import base64
import hashlib
import hmac
import secrets
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


DATABASE_PATH = Path(__file__).with_name("case_tracker.db")
PASSWORD_ITERATIONS = 210_000


def get_connection():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def hash_secret(secret):
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        secret.encode("utf-8"),
        salt,
        PASSWORD_ITERATIONS,
    )
    return "pbkdf2_sha256${}${}${}".format(
        PASSWORD_ITERATIONS,
        base64.b64encode(salt).decode("ascii"),
        base64.b64encode(digest).decode("ascii"),
    )


def verify_secret(secret, stored_value):
    try:
        algorithm, iterations, salt_text, digest_text = stored_value.split("$")

        if algorithm != "pbkdf2_sha256":
            return False

        salt = base64.b64decode(salt_text)
        expected_digest = base64.b64decode(digest_text)

        actual_digest = hashlib.pbkdf2_hmac(
            "sha256",
            secret.encode("utf-8"),
            salt,
            int(iterations),
        )

        return hmac.compare_digest(
            actual_digest,
            expected_digest,
        )

    except (ValueError, TypeError):
        return False


def initialize_database():
    with get_connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS organizations (
                organization_id INTEGER PRIMARY KEY AUTOINCREMENT,
                organization_name TEXT NOT NULL UNIQUE COLLATE NOCASE,
                active INTEGER NOT NULL DEFAULT 1
                    CHECK (active IN (0, 1)),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS organization_codes (
                code_id INTEGER PRIMARY KEY AUTOINCREMENT,
                organization_id INTEGER NOT NULL,
                code_hash TEXT NOT NULL,
                default_role TEXT NOT NULL DEFAULT 'Investigator'
                    CHECK (default_role = 'Investigator'),
                active INTEGER NOT NULL DEFAULT 1
                    CHECK (active IN (0, 1)),
                max_uses INTEGER NOT NULL DEFAULT 100
                    CHECK (max_uses > 0),
                use_count INTEGER NOT NULL DEFAULT 0
                    CHECK (use_count >= 0),
                expires_at TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (organization_id)
                    REFERENCES organizations(organization_id)
            );

            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                organization_id INTEGER NOT NULL,
                username TEXT NOT NULL UNIQUE COLLATE NOCASE,
                password_hash TEXT NOT NULL,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                date_of_birth TEXT NOT NULL,
                state TEXT NOT NULL,
                country TEXT NOT NULL,
                zip_code TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE COLLATE NOCASE,
                role TEXT NOT NULL
                    CHECK (role IN ('Investigator', 'Supervisor')),
                active INTEGER NOT NULL DEFAULT 1
                    CHECK (active IN (0, 1)),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (organization_id)
                    REFERENCES organizations(organization_id)
            );

            CREATE TABLE IF NOT EXISTS invitations (
                invitation_id INTEGER PRIMARY KEY AUTOINCREMENT,
                organization_id INTEGER NOT NULL,
                email TEXT NOT NULL COLLATE NOCASE,
                role TEXT NOT NULL
                    CHECK (role IN ('Investigator', 'Supervisor')),
                invitation_hash TEXT NOT NULL,
                invited_by INTEGER NOT NULL,
                expires_at TEXT NOT NULL,
                used_at TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (organization_id)
                    REFERENCES organizations(organization_id),
                FOREIGN KEY (invited_by)
                    REFERENCES users(user_id)
            );

            CREATE TABLE IF NOT EXISTS access_requests (
                request_id INTEGER PRIMARY KEY AUTOINCREMENT,
                organization_id INTEGER NOT NULL,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                email TEXT NOT NULL COLLATE NOCASE,
                reason TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Pending'
                    CHECK (
                        status IN ('Pending', 'Approved', 'Denied')
                    ),
                reviewed_by INTEGER,
                reviewed_at TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (organization_id)
                    REFERENCES organizations(organization_id),
                FOREIGN KEY (reviewed_by)
                    REFERENCES users(user_id)
            );

            CREATE TABLE IF NOT EXISTS cases (
                case_id INTEGER PRIMARY KEY AUTOINCREMENT,
                organization_id INTEGER NOT NULL,
                case_number TEXT NOT NULL COLLATE NOCASE,
                title TEXT NOT NULL
                    CHECK (
                        length(trim(title)) BETWEEN 1 AND 100
                    ),
                description TEXT,
                status TEXT NOT NULL DEFAULT 'Open'
                    CHECK (
                        status IN (
                            'Open',
                            'Investigating',
                            'Ready for Review',
                            'Under Review',
                            'Returned',
                            'Verified',
                            'Complete'
                        )
                    ),
                created_by INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (organization_id)
                    REFERENCES organizations(organization_id),
                FOREIGN KEY (created_by)
                    REFERENCES users(user_id),
                UNIQUE (organization_id, case_number)
            );

            CREATE TABLE IF NOT EXISTS case_assignments (
                assignment_id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id INTEGER NOT NULL,
                investigator_id INTEGER NOT NULL,
                assigned_by INTEGER NOT NULL,
                assignment_status TEXT NOT NULL DEFAULT 'Active'
                    CHECK (
                        assignment_status IN ('Active', 'Removed')
                    ),
                assigned_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (case_id)
                    REFERENCES cases(case_id),
                FOREIGN KEY (investigator_id)
                    REFERENCES users(user_id),
                FOREIGN KEY (assigned_by)
                    REFERENCES users(user_id),
                UNIQUE (case_id, investigator_id)
            );

            CREATE TABLE IF NOT EXISTS evidence_items (
                evidence_id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id INTEGER NOT NULL,
                evidence_number TEXT NOT NULL COLLATE NOCASE,
                item_type TEXT NOT NULL,
                description TEXT NOT NULL,
                serial_number TEXT,
                status TEXT NOT NULL DEFAULT 'Collected'
                    CHECK (
                        status IN (
                            'Collected',
                            'Stored',
                            'Under Examination',
                            'Transferred',
                            'Released'
                        )
                    ),
                storage_location TEXT NOT NULL,
                added_by INTEGER NOT NULL,
                added_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (case_id)
                    REFERENCES cases(case_id),
                FOREIGN KEY (added_by)
                    REFERENCES users(user_id),
                UNIQUE (case_id, evidence_number)
            );

            CREATE TABLE IF NOT EXISTS custody_records (
                custody_id INTEGER PRIMARY KEY AUTOINCREMENT,
                evidence_id INTEGER NOT NULL,
                action TEXT NOT NULL
                    CHECK (
                        action IN (
                            'Collected',
                            'Transferred',
                            'Examined',
                            'Stored',
                            'Released'
                        )
                    ),
                performed_by INTEGER NOT NULL,
                previous_location TEXT,
                new_location TEXT NOT NULL,
                notes TEXT,
                verified INTEGER NOT NULL DEFAULT 0
                    CHECK (verified IN (0, 1)),
                verified_by INTEGER,
                action_timestamp TEXT NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (evidence_id)
                    REFERENCES evidence_items(evidence_id),
                FOREIGN KEY (performed_by)
                    REFERENCES users(user_id),
                FOREIGN KEY (verified_by)
                    REFERENCES users(user_id)
            );

            CREATE TABLE IF NOT EXISTS case_notes (
                note_id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                note_text TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT,
                FOREIGN KEY (case_id)
                    REFERENCES cases(case_id),
                FOREIGN KEY (user_id)
                    REFERENCES users(user_id)
            );

            CREATE TABLE IF NOT EXISTS case_reviews (
                review_id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id INTEGER NOT NULL,
                supervisor_id INTEGER NOT NULL,
                decision TEXT NOT NULL
                    CHECK (
                        decision IN (
                            'Verified',
                            'Returned for Corrections',
                            'Marked Complete'
                        )
                    ),
                comments TEXT,
                reviewed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (case_id)
                    REFERENCES cases(case_id),
                FOREIGN KEY (supervisor_id)
                    REFERENCES users(user_id)
            );

            CREATE TABLE IF NOT EXISTS access_logs (
                log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                organization_id INTEGER NOT NULL,
                user_id INTEGER,
                action TEXT NOT NULL,
                table_name TEXT NOT NULL,
                record_id INTEGER,
                details TEXT,
                action_timestamp TEXT NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (organization_id)
                    REFERENCES organizations(organization_id),
                FOREIGN KEY (user_id)
                    REFERENCES users(user_id)
            );
            """
        )


def system_needs_setup():
    with get_connection() as connection:
        row = connection.execute(
            "SELECT COUNT(*) AS total FROM users"
        ).fetchone()

        return row["total"] == 0


def create_initial_supervisor(
    organization_name,
    company_code,
    profile,
):
    with get_connection() as connection:
        existing = connection.execute(
            "SELECT COUNT(*) AS total FROM users"
        ).fetchone()["total"]

        if existing != 0:
            raise ValueError(
                "Initial setup has already been completed."
            )

        try:
            organization_cursor = connection.execute(
                """
                INSERT INTO organizations (organization_name)
                VALUES (?)
                """,
                (organization_name.strip(),),
            )

            organization_id = organization_cursor.lastrowid

            connection.execute(
                """
                INSERT INTO organization_codes (
                    organization_id,
                    code_hash,
                    default_role
                )
                VALUES (?, ?, 'Investigator')
                """,
                (
                    organization_id,
                    hash_secret(company_code),
                ),
            )

            user_cursor = connection.execute(
                """
                INSERT INTO users (
                    organization_id,
                    username,
                    password_hash,
                    first_name,
                    last_name,
                    date_of_birth,
                    state,
                    country,
                    zip_code,
                    email,
                    role
                )
                VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    'Supervisor'
                )
                """,
                (
                    organization_id,
                    profile["username"].strip(),
                    hash_secret(profile["password"]),
                    profile["first_name"].strip(),
                    profile["last_name"].strip(),
                    profile["date_of_birth"].strip(),
                    profile["state"].strip(),
                    profile["country"].strip(),
                    profile["zip_code"].strip(),
                    profile["email"].strip(),
                ),
            )

            connection.execute(
                """
                INSERT INTO access_logs (
                    organization_id,
                    user_id,
                    action,
                    table_name,
                    record_id,
                    details
                )
                VALUES (
                    ?, ?,
                    'CREATE',
                    'users',
                    ?,
                    ?
                )
                """,
                (
                    organization_id,
                    user_cursor.lastrowid,
                    user_cursor.lastrowid,
                    "Initial Supervisor account created",
                ),
            )

        except sqlite3.IntegrityError as error:
            raise ValueError(
                "That organization, username, or email already exists."
            ) from error


def _find_valid_company_code(
    connection,
    company_code,
):
    rows = connection.execute(
        """
        SELECT
            code_id,
            organization_id,
            code_hash,
            max_uses,
            use_count,
            expires_at
        FROM organization_codes
        WHERE active = 1
          AND use_count < max_uses
        """
    ).fetchall()

    now = datetime.now(timezone.utc)

    for row in rows:
        if row["expires_at"]:
            expiration = datetime.fromisoformat(
                row["expires_at"]
            )

            if expiration.tzinfo is None:
                expiration = expiration.replace(
                    tzinfo=timezone.utc
                )

            if expiration <= now:
                continue

        if verify_secret(
            company_code,
            row["code_hash"],
        ):
            return row

    return None


def create_investigator_account(
    company_code,
    profile,
):
    with get_connection() as connection:
        code = _find_valid_company_code(
            connection,
            company_code,
        )

        if code is None:
            raise ValueError(
                "The company access code is invalid or inactive."
            )

        try:
            cursor = connection.execute(
                """
                INSERT INTO users (
                    organization_id,
                    username,
                    password_hash,
                    first_name,
                    last_name,
                    date_of_birth,
                    state,
                    country,
                    zip_code,
                    email,
                    role
                )
                VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    'Investigator'
                )
                """,
                (
                    code["organization_id"],
                    profile["username"].strip(),
                    hash_secret(profile["password"]),
                    profile["first_name"].strip(),
                    profile["last_name"].strip(),
                    profile["date_of_birth"].strip(),
                    profile["state"].strip(),
                    profile["country"].strip(),
                    profile["zip_code"].strip(),
                    profile["email"].strip(),
                ),
            )

            connection.execute(
                """
                UPDATE organization_codes
                SET use_count = use_count + 1
                WHERE code_id = ?
                """,
                (code["code_id"],),
            )

            connection.execute(
                """
                INSERT INTO access_logs (
                    organization_id,
                    user_id,
                    action,
                    table_name,
                    record_id,
                    details
                )
                VALUES (
                    ?, ?,
                    'CREATE',
                    'users',
                    ?,
                    ?
                )
                """,
                (
                    code["organization_id"],
                    cursor.lastrowid,
                    cursor.lastrowid,
                    "Investigator joined with company access code",
                ),
            )

        except sqlite3.IntegrityError as error:
            raise ValueError(
                "That username or email is already registered."
            ) from error


def authenticate_user(
    username,
    password,
):
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT
                users.*,
                organizations.organization_name
            FROM users
            JOIN organizations
              ON organizations.organization_id =
                 users.organization_id
            WHERE users.username = ? COLLATE NOCASE
              AND users.active = 1
              AND organizations.active = 1
            """,
            (username.strip(),),
        ).fetchone()

        if (
            row is None
            or not verify_secret(
                password,
                row["password_hash"],
            )
        ):
            return None

        connection.execute(
            """
            INSERT INTO access_logs (
                organization_id,
                user_id,
                action,
                table_name,
                record_id,
                details
            )
            VALUES (
                ?, ?,
                'LOGIN',
                'users',
                ?,
                'Successful sign in'
            )
            """,
            (
                row["organization_id"],
                row["user_id"],
                row["user_id"],
            ),
        )

        return dict(row)


def submit_access_request(
    organization_name,
    first_name,
    last_name,
    email,
    reason,
):
    with get_connection() as connection:
        organization = connection.execute(
            """
            SELECT organization_id
            FROM organizations
            WHERE organization_name = ? COLLATE NOCASE
              AND active = 1
            """,
            (organization_name.strip(),),
        ).fetchone()

        if organization is None:
            raise ValueError(
                "That organization could not be found."
            )

        duplicate = connection.execute(
            """
            SELECT request_id
            FROM access_requests
            WHERE organization_id = ?
              AND email = ? COLLATE NOCASE
              AND status = 'Pending'
            """,
            (
                organization["organization_id"],
                email.strip(),
            ),
        ).fetchone()

        if duplicate:
            raise ValueError(
                "A pending request already exists "
                "for that email address."
            )

        connection.execute(
            """
            INSERT INTO access_requests (
                organization_id,
                first_name,
                last_name,
                email,
                reason
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                organization["organization_id"],
                first_name.strip(),
                last_name.strip(),
                email.strip(),
                reason.strip(),
            ),
        )


def get_pending_request_count(organization_id):
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT COUNT(*) AS total
            FROM access_requests
            WHERE organization_id = ?
              AND status = 'Pending'
            """,
            (organization_id,),
        ).fetchone()

        return row["total"]


def get_case_numbers(organization_id):
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT case_number
            FROM cases
            WHERE organization_id = ?
            ORDER BY case_number COLLATE NOCASE
            """,
            (organization_id,),
        ).fetchall()

        return [
            row["case_number"]
            for row in rows
        ]

def get_cases_for_user(
    organization_id,
    user_id,
    role,
):
    with get_connection() as connection:
        if role == "Supervisor":
            rows = connection.execute(
                """
                SELECT
                    case_id,
                    case_number,
                    title,
                    status,
                    created_at
                FROM cases
                WHERE organization_id = ?
                ORDER BY
                    created_at DESC,
                    case_number COLLATE NOCASE
                """,
                (organization_id,),
            ).fetchall()

        else:
            rows = connection.execute(
                """
                SELECT
                    cases.case_id,
                    cases.case_number,
                    cases.title,
                    cases.status,
                    cases.created_at
                FROM cases
                JOIN case_assignments
                  ON case_assignments.case_id =
                     cases.case_id
                WHERE cases.organization_id = ?
                  AND case_assignments.investigator_id = ?
                  AND case_assignments.assignment_status =
                      'Active'
                ORDER BY
                    cases.created_at DESC,
                    cases.case_number COLLATE NOCASE
                """,
                (
                    organization_id,
                    user_id,
                ),
            ).fetchall()

        return [
            dict(row)
            for row in rows
        ]

def get_case_for_user(
    case_id,
    organization_id,
    user_id,
    role,
):
    with get_connection() as connection:
        if role == "Supervisor":
            row = connection.execute(
                """
                SELECT
                    cases.case_id,
                    cases.case_number,
                    cases.title,
                    cases.description,
                    cases.status,
                    cases.created_at,
                    users.first_name || ' ' ||
                    users.last_name AS investigator_name
                FROM cases
                JOIN users
                  ON users.user_id = cases.created_by
                WHERE cases.case_id = ?
                  AND cases.organization_id = ?
                """,
                (
                    case_id,
                    organization_id,
                ),
            ).fetchone()

        else:
            row = connection.execute(
                """
                SELECT
                    cases.case_id,
                    cases.case_number,
                    cases.title,
                    cases.description,
                    cases.status,
                    cases.created_at,
                    users.first_name || ' ' ||
                    users.last_name AS investigator_name
                FROM cases
                JOIN users
                  ON users.user_id = cases.created_by
                JOIN case_assignments
                  ON case_assignments.case_id =
                     cases.case_id
                WHERE cases.case_id = ?
                  AND cases.organization_id = ?
                  AND case_assignments.investigator_id = ?
                  AND case_assignments.assignment_status =
                      'Active'
                """,
                (
                    case_id,
                    organization_id,
                    user_id,
                ),
            ).fetchone()

        if row is None:
            return None

        return dict(row)


def get_evidence_for_case(
    case_id,
    organization_id,
    user_id,
    role,
):
    accessible_case = get_case_for_user(
        case_id,
        organization_id,
        user_id,
        role,
    )

    if accessible_case is None:
        return []

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                evidence_id,
                evidence_number,
                item_type,
                description,
                serial_number,
                status,
                storage_location,
                added_at
            FROM evidence_items
            WHERE case_id = ?
            ORDER BY
                added_at DESC,
                evidence_number COLLATE NOCASE
            """,
            (case_id,),
        ).fetchall()

        return [
            dict(row)
            for row in rows
        ]


def create_evidence_item(
    case_id,
    organization_id,
    added_by,
    evidence_number,
    item_type,
    description,
    serial_number,
    storage_location,
):
    clean_evidence_number = evidence_number.strip()
    clean_item_type = item_type.strip()
    clean_description = description.strip()
    clean_serial_number = serial_number.strip()
    clean_storage_location = storage_location.strip()

    if not clean_evidence_number:
        raise ValueError(
            "Evidence number is required."
        )

    if not clean_item_type:
        raise ValueError(
            "Evidence type is required."
        )

    if not clean_description:
        raise ValueError(
            "Evidence description is required."
        )

    if not clean_storage_location:
        raise ValueError(
            "Storage location is required."
        )

    with get_connection() as connection:
        permission = connection.execute(
            """
            SELECT cases.case_id
            FROM cases
            JOIN case_assignments
              ON case_assignments.case_id =
                 cases.case_id
            JOIN users
              ON users.user_id =
                 case_assignments.investigator_id
            WHERE cases.case_id = ?
              AND cases.organization_id = ?
              AND case_assignments.investigator_id = ?
              AND case_assignments.assignment_status =
                  'Active'
              AND users.role = 'Investigator'
              AND users.active = 1
            """,
            (
                case_id,
                organization_id,
                added_by,
            ),
        ).fetchone()

        if permission is None:
            raise ValueError(
                "You do not have permission to add "
                "evidence to this case."
            )

        duplicate = connection.execute(
            """
            SELECT evidence_id
            FROM evidence_items
            WHERE case_id = ?
              AND evidence_number = ? COLLATE NOCASE
            """,
            (
                case_id,
                clean_evidence_number,
            ),
        ).fetchone()

        if duplicate is not None:
            raise ValueError(
                "That evidence number already exists "
                "in this case."
            )

        try:
            cursor = connection.execute(
                """
                INSERT INTO evidence_items (
                    case_id,
                    evidence_number,
                    item_type,
                    description,
                    serial_number,
                    status,
                    storage_location,
                    added_by
                )
                VALUES (
                    ?, ?, ?, ?, ?,
                    'Collected',
                    ?, ?
                )
                """,
                (
                    case_id,
                    clean_evidence_number,
                    clean_item_type,
                    clean_description,
                    clean_serial_number or None,
                    clean_storage_location,
                    added_by,
                ),
            )

            evidence_id = cursor.lastrowid

            connection.execute(
                """
                INSERT INTO custody_records (
                    evidence_id,
                    action,
                    performed_by,
                    previous_location,
                    new_location,
                    notes
                )
                VALUES (
                    ?,
                    'Collected',
                    ?,
                    NULL,
                    ?,
                    'Initial evidence collection'
                )
                """,
                (
                    evidence_id,
                    added_by,
                    clean_storage_location,
                ),
            )

            connection.execute(
                """
                INSERT INTO access_logs (
                    organization_id,
                    user_id,
                    action,
                    table_name,
                    record_id,
                    details
                )
                VALUES (
                    ?, ?,
                    'CREATE',
                    'evidence_items',
                    ?,
                    ?
                )
                """,
                (
                    organization_id,
                    added_by,
                    evidence_id,
                    (
                        "Evidence "
                        f"{clean_evidence_number} added "
                        f"to case ID {case_id}"
                    ),
                ),
            )

            return {
                "evidence_id": evidence_id,
                "case_id": case_id,
                "evidence_number": clean_evidence_number,
                "item_type": clean_item_type,
                "description": clean_description,
                "serial_number": clean_serial_number,
                "status": "Collected",
                "storage_location": clean_storage_location,
            }

        except sqlite3.IntegrityError as error:
            raise ValueError(
                "The evidence item could not be saved."
            ) from error

def create_case(
    organization_id,
    created_by,
    case_number,
    title,
    description="",
):
    clean_case_number = case_number.strip()
    clean_title = title.strip()
    clean_description = description.strip()

    try:
        with get_connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO cases (
                    organization_id,
                    case_number,
                    title,
                    description,
                    status,
                    created_by
                )
                VALUES (
                    ?, ?, ?, ?,
                    'Open',
                    ?
                )
                """,
                (
                    organization_id,
                    clean_case_number,
                    clean_title,
                    clean_description or None,
                    created_by,
                ),
            )

            case_id = cursor.lastrowid

            connection.execute(
                """
                INSERT INTO case_assignments (
                    case_id,
                    investigator_id,
                    assigned_by
                )
                VALUES (?, ?, ?)
                """,
                (
                    case_id,
                    created_by,
                    created_by,
                ),
            )

            connection.execute(
                """
                INSERT INTO access_logs (
                    organization_id,
                    user_id,
                    action,
                    table_name,
                    record_id,
                    details
                )
                VALUES (
                    ?, ?,
                    'CREATE',
                    'cases',
                    ?,
                    ?
                )
                """,
                (
                    organization_id,
                    created_by,
                    case_id,
                    f"Case {clean_case_number} created",
                ),
            )

            return {
                "case_id": case_id,
                "case_number": clean_case_number,
                "title": clean_title,
                "description": clean_description,
                "status": "Open",
            }

    except sqlite3.IntegrityError as error:
        raise ValueError(
            "That case number already exists "
            "for this organization."
        ) from error