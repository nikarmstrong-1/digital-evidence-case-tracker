def validate_required_case_fields(case_data):
    field_labels = {
        "case_number": "Case number is required.",
        "title": "Title is required.",
        "status": "Status is required.",
    }

    missing_fields = [
        message
        for field, message in field_labels.items()
        if not str(case_data.get(field, "")).strip()
    ]

    return {
        "valid": not missing_fields,
        "missing_fields": missing_fields,
    }


def validate_case_title(title):
    clean_title = str(title).strip()

    if not clean_title:
        return "required"

    if len(clean_title) > 100:
        return "too_long"

    return "valid"


def is_unique_case_number(
    case_number,
    existing_case_numbers,
):
    normalized = str(case_number).strip().casefold()

    existing = {
        str(number).strip().casefold()
        for number in existing_case_numbers
    }

    return (
        bool(normalized)
        and normalized not in existing
    )


def validate_create_case(
    case_data,
    existing_case_numbers,
):
    errors = []

    required_result = validate_required_case_fields(
        case_data
    )

    errors.extend(
        required_result["missing_fields"]
    )

    title_result = validate_case_title(
        case_data.get("title", "")
    )

    if title_result == "too_long":
        errors.append(
            "Title must be 100 characters or fewer."
        )

    case_number = str(
        case_data.get("case_number", "")
    ).strip()

    if (
        case_number
        and not is_unique_case_number(
            case_number,
            existing_case_numbers,
        )
    ):
        errors.append(
            "Case number already exists."
        )

    status = str(
        case_data.get("status", "")
    ).strip()

    if status != "Open":
        errors.append(
            "A new case must begin with the status Open."
        )

    return {
        "valid": not errors,
        "errors": errors,
    }


def format_case_created_confirmation(
    case_number,
    title,
):
    clean_case_number = str(
        case_number
    ).strip()

    clean_title = str(
        title
    ).strip()

    return {
        "message": "Case created",
        "summary": (
            f"{clean_case_number} - {clean_title}"
        ),
    }