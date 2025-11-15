import sqlite3
from pathlib import Path
from datetime import date

# store the database next to this script 
database_path = Path(__file__).with_name("employees.db")

sql_schema = """
CREATE TABLE IF NOT EXISTS employees (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name  TEXT NOT NULL,
    last_name   TEXT NOT NULL,
    email       TEXT UNIQUE,
    phone       TEXT,
    department  TEXT,
    title       TEXT,
    hire_date   TEXT -- YYYY-MM-DD; store as text for simplicity's sake
);
"""


def prompt_required(label: str) -> str:
    """Send a prompt until the user types something not empty."""
    while True:
        value = input(label).strip()
        if value:
            return value
        print("  (This field is required; try again.)")

def get_int(label: str) -> int:
    """Prompt until the user gives an integer."""
    while True:
        raw = input(label).strip()
        try:
            return int(raw)
        except ValueError:
            print("  (Please enter a number.)")

def print_rows(rows: list[sqlite3.Row]) -> None:
    """Print a list of employee rows."""
    if not rows:
        print("\n(no employees found)\n")
        return
    print()
    print(f"{'ID':<4} {'First':<12} {'Last':<14} {'Email':<28} {'Dept':<14} {'Title':<18} {'Hired':<10}")
    print("-" * 110)
    for r in rows:
        # go crazy with the formatting
        print(f"{r['id']:<4} {r['first_name']:<12} {r['last_name']:<14} "
              f"{(r['email'] or ''):<28} {(r['department'] or ''):<14} "
              f"{(r['title'] or ''):<18} {(r['hire_date'] or ''):<10}")
    print()

# function comments kinda speak for themselves here
def get_connection() -> sqlite3.Connection:
    """Open a connection and set row_factory so we can use column names."""
    conn = sqlite3.connect(database_path)
    # row factory makes fetched rows act like dictionaries
    conn.row_factory = sqlite3.Row  
    conn.execute("PRAGMA foreign_keys = ON;")  
    return conn

def init_db(conn: sqlite3.Connection) -> None:
    """Create the table if it doesn't exist."""
    conn.executescript(sql_schema)
    conn.commit()


# menu utils
def add_employee(conn: sqlite3.Connection) -> None:
    print("\nAdd a new employee\n-------------------")
    first = prompt_required("First name: ")
    last  = prompt_required("Last name: ")
    email = input("Email (optional): ").strip() or None
    phone = input("Phone (optional): ").strip() or None
    dept  = input("Department (optional): ").strip() or None
    title = input("Title (optional): ").strip() or None

    # f]if user leaves hire date blank just use today's date in ISO (YYYY-MM-DD).
    hire = input("Hire date (YYYY-MM-DD) [default: today]: ").strip()
    if not hire:
        hire = date.today().isoformat()

    try:
        conn.execute(
            """
            INSERT INTO employees (first_name, last_name, email, phone, department, title, hire_date)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (first, last, email, phone, dept, title, hire),
        )
        conn.commit()
        print("\n✅ Employee added.\n")
    except sqlite3.IntegrityError as e: # pass through e as the exception and display 
        # handle an error, likely a unique email issue
        print(f"\n⚠️  Couldn't add employee (maybe the email is already used?): {e}\n")


def list_employees(conn: sqlite3.Connection) -> None:
    print("\nAll employees\n-------------")
    rows = conn.execute(
        """
        SELECT * FROM employees
        ORDER BY last_name COLLATE NOCASE, first_name COLLATE NOCASE
        """
    ).fetchall()
    print_rows(rows)


def search_employees(conn: sqlite3.Connection) -> None:
    print("\nSearch employees\n----------------")
    term = input("Search by name/email/department/title or an exact ID: ").strip()
    if not term:
        print("\n(nothing to search)\n")
        return

    # if the user typed a number, treat it as an ID lookup
    if term.isdigit():
        row = conn.execute("SELECT * FROM employees WHERE id = ?", (int(term),)).fetchone()
        print_rows([row] if row else [])
        return

    # or scan a few text fields using LIKE.
    like = f"%{term}%"
    rows = conn.execute(
        """
        SELECT * FROM employees
        WHERE first_name LIKE ? OR last_name LIKE ?
           OR email LIKE ? OR department LIKE ? OR title LIKE ?
        ORDER BY last_name COLLATE NOCASE, first_name COLLATE NOCASE
        """,
        (like, like, like, like, like),
    ).fetchall()
    print_rows(rows)


def update_employee(conn: sqlite3.Connection) -> None:
    print("\nUpdate an employee\n------------------")
    emp_id = get_int("Enter the employee ID to update: ")

    row = conn.execute("SELECT * FROM employees WHERE id = ?", (emp_id,)).fetchone()
    if not row:
        print("\n(no employee with that ID)\n")
        return

    print("\nPress Enter to keep the current value. Current values in [brackets].\n")
    first = input(f"First name [{row['first_name']}]: ").strip() or row['first_name']
    last  = input(f"Last name  [{row['last_name']}]: ").strip() or row['last_name']
    email = input(f"Email      [{row['email'] or ''}]: ").strip() or (row['email'] or None)
    phone = input(f"Phone      [{row['phone'] or ''}]: ").strip() or (row['phone'] or None)
    dept  = input(f"Department [{row['department'] or ''}]: ").strip() or (row['department'] or None)
    title = input(f"Title      [{row['title'] or ''}]: ").strip() or (row['title'] or None)
    hire  = input(f"Hire date  [{row['hire_date'] or ''}]: ").strip() or (row['hire_date'] or None)

    try:
        conn.execute(
            """
            UPDATE employees
               SET first_name = ?, last_name = ?, email = ?, phone = ?,
                   department = ?, title = ?, hire_date = ?
             WHERE id = ?
            """,
            (first, last, email, phone, dept, title, hire, emp_id),
        )
        conn.commit()
        print("\n✅ Employee updated.\n")
    except sqlite3.IntegrityError as e:
        print(f"\n⚠️  Couldn't update employee: {e}\n")

# delete an employee from the database
def delete_employee(conn: sqlite3.Connection) -> None:
    print("\nDelete an employee\n------------------")
    emp_id = get_int("Enter the employee ID to delete: ")

    row = conn.execute("SELECT id, first_name, last_name FROM employees WHERE id = ?", (emp_id,)).fetchone()
    if not row:
        print("\n(no employee with that ID)\n")
        return

    confirm = input(f"Type 'delete' to confirm deleting {row['first_name']} {row['last_name']} (ID {row['id']}): ").strip().lower()
    if confirm != "delete":
        print("\n(canceled)\n")
        return

    conn.execute("DELETE FROM employees WHERE id = ?", (emp_id,))
    conn.commit()
    print("\n🗑️  Employee deleted.\n")


# main menu 
def main() -> None:
    print("\nEmployee Directory (SQLite)\n===========================\n")

    conn = get_connection()
    try:
        init_db(conn)
        while True:
            print("Main menu\n---------")
            print("  1) List employees")
            print("  2) Search employees")
            print("  3) Add employee")
            print("  4) Update employee")
            print("  5) Delete employee")
            print("  6) Quit\n")

            choice = input("Choose 1-6: ").strip()
            if choice == "1":
                list_employees(conn)
            elif choice == "2":
                search_employees(conn)
            elif choice == "3":
                add_employee(conn)
            elif choice == "4":
                update_employee(conn)
            elif choice == "5":
                delete_employee(conn)
            elif choice == "6" or choice.lower() in {"q", "quit", "exit"}:
                print("\nGoodbye!\n")
                break
            else:
                print("\n(unrecognized option; try again)\n")
    finally:
        conn.close()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n(Interrupted) Bye!\n")
