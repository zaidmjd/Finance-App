"""
database.py
-----------
The ONLY file that talks to SQLite. Every other file asks this file
to read or write. This is the "data access layer".

Phase 1 had: income, budget, transactions.
Now we add: savings, bank_statements, goals, loans, investments.
"""

import sqlite3
from datetime import datetime

DB_NAME = "finance.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create every table if it doesn't exist. Safe to run repeatedly."""
    conn = get_connection()
    cur = conn.cursor()


    cur.execute("""
        CREATE TABLE IF NOT EXISTS income (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            salary REAL DEFAULT 0,
            bonus REAL DEFAULT 0
        )
    """)
    cur.execute("INSERT OR IGNORE INTO income (id, salary, bonus) VALUES (1, 0, 0)")

    cur.execute("""
        CREATE TABLE IF NOT EXISTS budget (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL UNIQUE,
            planned_spend REAL DEFAULT 0,
            planned_save REAL DEFAULT 0
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            amount REAL NOT NULL,
            source TEXT DEFAULT 'manual',
            note TEXT,
            date TEXT
        )
    """)


    cur.execute("""
        CREATE TABLE IF NOT EXISTS savings (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            balance REAL DEFAULT 0
        )
    """)

    cur.execute("INSERT OR IGNORE INTO savings (id, balance) VALUES (1, 0)")


    cur.execute("""
        CREATE TABLE IF NOT EXISTS bank_statements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT,
            period TEXT,
            money_in REAL DEFAULT 0,
            money_out REAL DEFAULT 0,
            imported_at TEXT
        )
    """)


    cur.execute("""
        CREATE TABLE IF NOT EXISTS goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item TEXT NOT NULL,
            cost REAL NOT NULL,
            months INTEGER NOT NULL,
            created_at TEXT
        )
    """)


    cur.execute("""
        CREATE TABLE IF NOT EXISTS loans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            principal REAL NOT NULL,
            annual_rate REAL NOT NULL,
            monthly_payment REAL NOT NULL,
            created_at TEXT
        )
    """)


    cur.execute("""
        CREATE TABLE IF NOT EXISTS investments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            type TEXT,
            amount_invested REAL DEFAULT 0,
            monthly_change REAL DEFAULT 0,
            created_at TEXT
        )
    """)

    conn.commit()
    conn.close()


def set_income(salary, bonus):
    """Store the user's monthly salary and monthly bonus (single row)."""
    conn = get_connection()
    conn.execute("UPDATE income SET salary = ?, bonus = ? WHERE id = 1",
                 (salary, bonus))
    conn.commit()
    conn.close()


def get_income():
    """Return (salary, bonus) the user entered."""
    conn = get_connection()
    row = conn.execute("SELECT salary, bonus FROM income WHERE id = 1").fetchone()
    conn.close()
    return row["salary"], row["bonus"]


def get_monthly_income():
    """Monthly income = salary + bonus + this month's investment gain/loss."""
    salary, bonus = get_income()
    total = salary + bonus + get_total_investment_change()
    return round(total, 2)


def add_or_update_budget(category, planned_spend, planned_save):
    conn = get_connection()
    conn.execute("""
        INSERT INTO budget (category, planned_spend, planned_save)
        VALUES (?, ?, ?)
        ON CONFLICT(category) DO UPDATE SET
            planned_spend = excluded.planned_spend,
            planned_save  = excluded.planned_save
    """, (category, planned_spend, planned_save))
    conn.commit()
    conn.close()


def get_all_budget():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM budget ORDER BY category").fetchall()
    conn.close()
    return rows


def delete_budget(category):
    conn = get_connection()
    conn.execute("DELETE FROM budget WHERE category = ?", (category,))
    conn.commit()
    conn.close()


def get_total_planned_save():
    conn = get_connection()
    row = conn.execute("SELECT SUM(planned_save) AS s FROM budget").fetchone()
    conn.close()
    return row["s"] or 0.0


def add_transaction(category, amount, source="manual", note=""):
    conn = get_connection()
    conn.execute(
        "INSERT INTO transactions (category, amount, source, note, date) VALUES (?, ?, ?, ?, ?)",
        (category, amount, source, note, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()


def get_all_transactions():
    """Every transaction, newest first."""
    conn = get_connection()
    rows = conn.execute("SELECT * FROM transactions ORDER BY id DESC").fetchall()
    conn.close()
    return rows


def get_spending_by_category():
    conn = get_connection()
    rows = conn.execute("""
        SELECT category, SUM(amount) AS total
        FROM transactions GROUP BY category
    """).fetchall()
    conn.close()
    return {r["category"]: r["total"] for r in rows}


def get_total_spending():
    conn = get_connection()
    row = conn.execute("SELECT SUM(amount) AS total FROM transactions").fetchone()
    conn.close()
    return row["total"] or 0.0


def get_savings_base():
    """The raw balance the user last entered."""
    conn = get_connection()
    row = conn.execute("SELECT balance FROM savings WHERE id = 1").fetchone()
    conn.close()
    return row["balance"]


def set_savings(amount):
    """User sets their current savings. This becomes the new base from which
    future income/spending/investment changes are applied."""
    conn = get_connection()
    conn.execute("UPDATE savings SET balance = ? WHERE id = 1", (amount,))
    conn.commit()
    conn.close()


def get_savings():
    """The LIVE savings figure shown to the user:
       base + monthly income - total spending.
    (monthly income already includes investment profit/loss, so gains raise
     savings and losses lower it automatically.)"""
    base = get_savings_base()
    live = base + get_monthly_income() - get_total_spending()
    return round(live, 2)


def adjust_savings(delta):
    """Add (or subtract) directly to the stored base balance."""
    conn = get_connection()
    conn.execute("UPDATE savings SET balance = balance + ? WHERE id = 1", (delta,))
    conn.commit()
    conn.close()


def get_monthly_surplus():
    """Money left over each month = monthly income - total spending.
    Positive = saving, negative = overspending."""
    return round(get_monthly_income() - get_total_spending(), 2)


def add_bank_statement(filename, period, money_in, money_out):
    conn = get_connection()
    conn.execute("""
        INSERT INTO bank_statements (filename, period, money_in, money_out, imported_at)
        VALUES (?, ?, ?, ?, ?)
    """, (filename, period, money_in, money_out, datetime.now().isoformat()))
    conn.commit()
    conn.close()


def get_all_bank_statements():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM bank_statements ORDER BY id DESC").fetchall()
    conn.close()
    return rows


def delete_bank_statement(stmt_id):
    conn = get_connection()
    conn.execute("DELETE FROM bank_statements WHERE id = ?", (stmt_id,))
    conn.commit()
    conn.close()


def add_goal(item, cost, months):
    conn = get_connection()
    conn.execute(
        "INSERT INTO goals (item, cost, months, created_at) VALUES (?, ?, ?, ?)",
        (item, cost, months, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()


def get_all_goals():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM goals ORDER BY id DESC").fetchall()
    conn.close()
    return rows


def delete_goal(goal_id):
    conn = get_connection()
    conn.execute("DELETE FROM goals WHERE id = ?", (goal_id,))
    conn.commit()
    conn.close()


def add_loan(name, principal, annual_rate, monthly_payment):
    conn = get_connection()
    conn.execute("""
        INSERT INTO loans (name, principal, annual_rate, monthly_payment, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (name, principal, annual_rate, monthly_payment, datetime.now().isoformat()))
    conn.commit()
    conn.close()


def get_all_loans():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM loans ORDER BY id DESC").fetchall()
    conn.close()
    return rows


def delete_loan(loan_id):
    conn = get_connection()
    conn.execute("DELETE FROM loans WHERE id = ?", (loan_id,))
    conn.commit()
    conn.close()


def add_investment(name, inv_type, amount_invested, monthly_change):
    conn = get_connection()
    conn.execute("""
        INSERT INTO investments (name, type, amount_invested, monthly_change, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (name, inv_type, amount_invested, monthly_change, datetime.now().isoformat()))
    conn.commit()
    conn.close()


def get_all_investments():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM investments ORDER BY id DESC").fetchall()
    conn.close()
    return rows


def delete_investment(inv_id):
    conn = get_connection()
    conn.execute("DELETE FROM investments WHERE id = ?", (inv_id,))
    conn.commit()
    conn.close()


def get_total_invested():
    conn = get_connection()
    row = conn.execute("SELECT SUM(amount_invested) AS s FROM investments").fetchone()
    conn.close()
    return row["s"] or 0.0


def get_total_investment_change():
    """Total gain/loss from all investments THIS MONTH."""
    conn = get_connection()
    row = conn.execute("SELECT SUM(monthly_change) AS s FROM investments").fetchone()
    conn.close()
    return row["s"] or 0.0


if __name__ == "__main__":
    init_db()
    print("All tables created.")
    print("Monthly income:", get_monthly_income())
    print("Monthly surplus:", get_monthly_surplus())
    print("Savings:", get_savings())
