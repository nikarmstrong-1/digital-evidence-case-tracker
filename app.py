import re
import tkinter as tk
from datetime import date, datetime
from tkinter import messagebox, ttk

from database import (
    authenticate_user,
    create_initial_supervisor,
    create_investigator_account,
    get_pending_request_count,
    initialize_database,
    submit_access_request,
    system_needs_setup,
)


BACKGROUND = "#eef2f7"
NAVY = "#163a5f"
ACCENT = "#2c6e9e"
TEXT = "#1f2933"
MUTED = "#5f6b76"
WHITE = "#ffffff"


class CaseTrackerApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Digital Evidence Case Tracker")
        self.geometry("980x720")
        self.minsize(850, 650)
        self.configure(background=BACKGROUND)
        self.current_user = None

        self.configure_styles()
        initialize_database()

        if system_needs_setup():
            self.show_initial_setup()
        else:
            self.show_login()

    def configure_styles(self):
        style = ttk.Style(self)
        style.theme_use("clam")

        style.configure("Card.TFrame", background=WHITE)
        style.configure(
            "Card.TLabel",
            background=WHITE,
            foreground=TEXT,
            font=("Segoe UI", 10),
        )
        style.configure(
            "CardTitle.TLabel",
            background=WHITE,
            foreground=NAVY,
            font=("Segoe UI", 18, "bold"),
        )
        style.configure(
            "Muted.TLabel",
            background=WHITE,
            foreground=MUTED,
            font=("Segoe UI", 10),
        )
        style.configure(
            "Primary.TButton",
            background=ACCENT,
            foreground=WHITE,
            padding=(16, 9),
            font=("Segoe UI", 10, "bold"),
        )
        style.map("Primary.TButton", background=[("active", NAVY)])
        style.configure(
            "Secondary.TButton",
            background="#dbe6ef",
            foreground=NAVY,
            padding=(14, 8),
            font=("Segoe UI", 10),
        )

    def clear_screen(self):
        for widget in self.winfo_children():
            widget.destroy()

    def add_header(self, subtitle):
        header = tk.Frame(self, background=NAVY, height=100)
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(
            header,
            text="Digital Evidence Case Tracker",
            background=NAVY,
            foreground=WHITE,
            font=("Segoe UI", 22, "bold"),
        ).pack(pady=(18, 2))

        tk.Label(
            header,
            text=subtitle,
            background=NAVY,
            foreground="#d9e6f2",
            font=("Segoe UI", 10),
        ).pack()

    def create_card(self):
        card = ttk.Frame(self, style="Card.TFrame", padding=28)
        card.pack(fill="both", expand=True, padx=70, pady=35)
        return card

    def add_field(self, parent, label, row, column, show=None, width=30):
        container = ttk.Frame(parent, style="Card.TFrame")
        container.grid(row=row, column=column, padx=10, pady=7, sticky="ew")

        ttk.Label(container, text=label, style="Card.TLabel").pack(anchor="w")
        entry = ttk.Entry(container, width=width, show=show)
        entry.pack(fill="x", pady=(3, 0))
        return entry

    def profile_is_valid(self, entries, include_account=True):
        values = {name: entry.get().strip() for name, entry in entries.items()}

        required = [
            "first_name",
            "last_name",
            "date_of_birth",
            "state",
            "country",
            "zip_code",
            "email",
        ]
        if include_account:
            required.extend(["username", "password", "confirm_password"])

        if any(not values.get(field) for field in required):
            messagebox.showerror("Missing Information", "Please complete every required field.")
            return None

        try:
            birth_date = datetime.strptime(values["date_of_birth"], "%Y-%m-%d").date()
            if birth_date >= date.today():
                raise ValueError
        except ValueError:
            messagebox.showerror(
                "Invalid Date",
                "Date of birth must use YYYY-MM-DD and must be earlier than today.",
            )
            return None

        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", values["email"]):
            messagebox.showerror("Invalid Email", "Enter a valid email address.")
            return None

        if len(values["zip_code"]) < 3 or len(values["zip_code"]) > 12:
            messagebox.showerror("Invalid ZIP Code", "Enter a valid ZIP or postal code.")
            return None

        if include_account:
            if len(values["username"]) < 4:
                messagebox.showerror("Invalid Username", "Username must contain at least 4 characters.")
                return None

            password = values["password"]
            if (
                len(password) < 8
                or not any(character.isupper() for character in password)
                or not any(character.islower() for character in password)
                or not any(character.isdigit() for character in password)
            ):
                messagebox.showerror(
                    "Weak Password",
                    "Password must contain at least 8 characters, including uppercase, lowercase, and a number.",
                )
                return None

            if password != values["confirm_password"]:
                messagebox.showerror("Password Error", "The passwords do not match.")
                return None

        return values

    def show_initial_setup(self):
        self.clear_screen()
        self.add_header("First-time organization and Supervisor setup")
        card = self.create_card()

        ttk.Label(card, text="Create the first Supervisor", style="CardTitle.TLabel").grid(
            row=0, column=0, columnspan=2, sticky="w", padx=10
        )
        ttk.Label(
            card,
            text="This first account controls your organization and becomes the Supervisor.",
            style="Muted.TLabel",
        ).grid(row=1, column=0, columnspan=2, sticky="w", padx=10, pady=(2, 12))

        entries = {}
        entries["organization_name"] = self.add_field(card, "Organization name", 2, 0)
        entries["company_code"] = self.add_field(card, "Investigator company access code", 2, 1)
        entries["first_name"] = self.add_field(card, "First name", 3, 0)
        entries["last_name"] = self.add_field(card, "Last name", 3, 1)
        entries["date_of_birth"] = self.add_field(card, "Date of birth (YYYY-MM-DD)", 4, 0)
        entries["email"] = self.add_field(card, "Email", 4, 1)
        entries["state"] = self.add_field(card, "State or province", 5, 0)
        entries["country"] = self.add_field(card, "Country", 5, 1)
        entries["zip_code"] = self.add_field(card, "ZIP or postal code", 6, 0)
        entries["username"] = self.add_field(card, "Username", 6, 1)
        entries["password"] = self.add_field(card, "Password", 7, 0, show="*")
        entries["confirm_password"] = self.add_field(card, "Confirm password", 7, 1, show="*")

        card.columnconfigure(0, weight=1)
        card.columnconfigure(1, weight=1)

        def complete_setup():
            values = self.profile_is_valid(entries)
            if values is None:
                return

            if not values["organization_name"]:
                messagebox.showerror("Missing Organization", "Enter the organization name.")
                return
            if len(values["company_code"]) < 8:
                messagebox.showerror(
                    "Weak Company Code",
                    "The company access code must contain at least 8 characters.",
                )
                return

            try:
                create_initial_supervisor(
                    values["organization_name"],
                    values["company_code"],
                    values,
                )
                messagebox.showinfo(
                    "Setup Complete",
                    "Your organization and Supervisor account were created.",
                )
                self.show_login()
            except ValueError as error:
                messagebox.showerror("Setup Error", str(error))

        ttk.Button(
            card,
            text="Complete Setup",
            style="Primary.TButton",
            command=complete_setup,
        ).grid(row=8, column=0, columnspan=2, pady=(20, 0))

    def show_login(self):
        self.clear_screen()
        self.add_header("Secure access for approved organization members")
        card = self.create_card()

        card.columnconfigure(0, weight=1)
        ttk.Label(card, text="Sign In", style="CardTitle.TLabel").pack(pady=(10, 4))
        ttk.Label(
            card,
            text="Use your approved Investigator or Supervisor account.",
            style="Muted.TLabel",
        ).pack(pady=(0, 20))

        form = ttk.Frame(card, style="Card.TFrame")
        form.pack()
        username_entry = self.add_field(form, "Username", 0, 0, width=36)
        password_entry = self.add_field(form, "Password", 1, 0, show="*", width=36)
        username_entry.focus()

        def sign_in():
            user = authenticate_user(username_entry.get(), password_entry.get())
            if user is None:
                messagebox.showerror("Sign In Failed", "Invalid username or password.")
                password_entry.delete(0, tk.END)
                return

            self.current_user = user
            self.show_dashboard()

        ttk.Button(
            form,
            text="Sign In",
            style="Primary.TButton",
            command=sign_in,
        ).grid(row=2, column=0, pady=(18, 8))

        password_entry.bind("<Return>", lambda _event: sign_in())

        actions = ttk.Frame(card, style="Card.TFrame")
        actions.pack(pady=(15, 0))
        ttk.Button(
            actions,
            text="Create Account",
            style="Secondary.TButton",
            command=self.show_create_account,
        ).grid(row=0, column=0, padx=6)
        ttk.Button(
            actions,
            text="Request Access",
            style="Secondary.TButton",
            command=self.show_request_access,
        ).grid(row=0, column=1, padx=6)

    def show_create_account(self):
        self.clear_screen()
        self.add_header("Create an approved Investigator account")
        card = self.create_card()

        ttk.Label(card, text="Create Investigator Account", style="CardTitle.TLabel").grid(
            row=0, column=0, columnspan=2, sticky="w", padx=10
        )
        ttk.Label(
            card,
            text="A valid company access code is required. Supervisor accounts cannot be self-created.",
            style="Muted.TLabel",
        ).grid(row=1, column=0, columnspan=2, sticky="w", padx=10, pady=(2, 12))

        entries = {}
        entries["company_code"] = self.add_field(card, "Company access code", 2, 0)
        entries["email"] = self.add_field(card, "Email", 2, 1)
        entries["first_name"] = self.add_field(card, "First name", 3, 0)
        entries["last_name"] = self.add_field(card, "Last name", 3, 1)
        entries["date_of_birth"] = self.add_field(card, "Date of birth (YYYY-MM-DD)", 4, 0)
        entries["state"] = self.add_field(card, "State or province", 4, 1)
        entries["country"] = self.add_field(card, "Country", 5, 0)
        entries["zip_code"] = self.add_field(card, "ZIP or postal code", 5, 1)
        entries["username"] = self.add_field(card, "Username", 6, 0)
        entries["password"] = self.add_field(card, "Password", 6, 1, show="*")
        entries["confirm_password"] = self.add_field(card, "Confirm password", 7, 0, show="*")

        card.columnconfigure(0, weight=1)
        card.columnconfigure(1, weight=1)

        def create_account():
            values = self.profile_is_valid(entries)
            if values is None:
                return

            if not values["company_code"]:
                messagebox.showerror("Access Code Required", "Enter your company access code.")
                return

            try:
                create_investigator_account(values["company_code"], values)
                messagebox.showinfo(
                    "Account Created",
                    "Your Investigator account was created. You can now sign in.",
                )
                self.show_login()
            except ValueError as error:
                messagebox.showerror("Account Error", str(error))

        buttons = ttk.Frame(card, style="Card.TFrame")
        buttons.grid(row=8, column=0, columnspan=2, pady=(20, 0))
        ttk.Button(
            buttons,
            text="Create Account",
            style="Primary.TButton",
            command=create_account,
        ).grid(row=0, column=0, padx=6)
        ttk.Button(
            buttons,
            text="Back",
            style="Secondary.TButton",
            command=self.show_login,
        ).grid(row=0, column=1, padx=6)

    def show_request_access(self):
        self.clear_screen()
        self.add_header("Request access to an existing organization")
        card = self.create_card()

        ttk.Label(card, text="Request Access", style="CardTitle.TLabel").grid(
            row=0, column=0, columnspan=2, sticky="w", padx=10
        )
        ttk.Label(
            card,
            text="The request will be stored for a Supervisor to review later.",
            style="Muted.TLabel",
        ).grid(row=1, column=0, columnspan=2, sticky="w", padx=10, pady=(2, 12))

        organization_entry = self.add_field(card, "Organization name", 2, 0)
        email_entry = self.add_field(card, "Email", 2, 1)
        first_name_entry = self.add_field(card, "First name", 3, 0)
        last_name_entry = self.add_field(card, "Last name", 3, 1)

        reason_frame = ttk.Frame(card, style="Card.TFrame")
        reason_frame.grid(row=4, column=0, columnspan=2, padx=10, pady=8, sticky="ew")
        ttk.Label(reason_frame, text="Reason for requesting access", style="Card.TLabel").pack(anchor="w")
        reason_text = tk.Text(reason_frame, height=6, wrap="word", font=("Segoe UI", 10))
        reason_text.pack(fill="x", pady=(3, 0))

        card.columnconfigure(0, weight=1)
        card.columnconfigure(1, weight=1)

        def send_request():
            organization = organization_entry.get().strip()
            first_name = first_name_entry.get().strip()
            last_name = last_name_entry.get().strip()
            email = email_entry.get().strip()
            reason = reason_text.get("1.0", "end").strip()

            if not all([organization, first_name, last_name, email, reason]):
                messagebox.showerror("Missing Information", "Complete every request field.")
                return

            if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
                messagebox.showerror("Invalid Email", "Enter a valid email address.")
                return

            try:
                submit_access_request(
                    organization,
                    first_name,
                    last_name,
                    email,
                    reason,
                )
                messagebox.showinfo(
                    "Request Submitted",
                    "Your access request was submitted for Supervisor review.",
                )
                self.show_login()
            except ValueError as error:
                messagebox.showerror("Request Error", str(error))

        buttons = ttk.Frame(card, style="Card.TFrame")
        buttons.grid(row=5, column=0, columnspan=2, pady=(18, 0))
        ttk.Button(
            buttons,
            text="Submit Request",
            style="Primary.TButton",
            command=send_request,
        ).grid(row=0, column=0, padx=6)
        ttk.Button(
            buttons,
            text="Back",
            style="Secondary.TButton",
            command=self.show_login,
        ).grid(row=0, column=1, padx=6)

    def show_dashboard(self):
        self.clear_screen()
        role = self.current_user["role"]
        self.add_header(f"{role} dashboard")
        card = self.create_card()

        full_name = f"{self.current_user['first_name']} {self.current_user['last_name']}"
        ttk.Label(
            card,
            text=f"Welcome, {full_name}",
            style="CardTitle.TLabel",
        ).pack(anchor="w")
        ttk.Label(
            card,
            text=f"{self.current_user['organization_name']}  •  {role}",
            style="Muted.TLabel",
        ).pack(anchor="w", pady=(2, 22))

        if role == "Supervisor":
            pending = get_pending_request_count(self.current_user["organization_id"])
            message = (
                "Supervisor access is active. You will eventually review all cases, "
                "verify custody records, return cases for corrections, and mark cases complete."
            )
            request_message = f"Pending access requests: {pending}"
        else:
            message = (
                "Investigator access is active. You will eventually create cases, add evidence, "
                "record custody activity, and submit cases for review."
            )
            request_message = ""

        ttk.Label(
            card,
            text=message,
            style="Card.TLabel",
            wraplength=700,
            justify="left",
        ).pack(anchor="w", pady=(0, 16))

        if request_message:
            ttk.Label(
                card,
                text=request_message,
                style="CardTitle.TLabel",
            ).pack(anchor="w", pady=(0, 18))

        ttk.Label(
            card,
            text="Case-management screens will be added in a later work session.",
            style="Muted.TLabel",
        ).pack(anchor="w")

        ttk.Button(
            card,
            text="Sign Out",
            style="Secondary.TButton",
            command=self.sign_out,
        ).pack(anchor="w", pady=(30, 0))

    def sign_out(self):
        self.current_user = None
        self.show_login()


if __name__ == "__main__":
    application = CaseTrackerApp()
    application.mainloop()