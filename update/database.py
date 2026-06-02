import sqlite3
import os
from datetime import datetime

REGISTRY_DB = 'finance_months.db'

# the database file currently in use; set by open_month(). Until a month is
# opened we use a default file so the app never breaks.
_active_db = 'finance.db'


def get_connection():
    conn = sqlite3.connect(_active_db)
    conn.row_factory = sqlite3.Row
    return conn


def _registry_conn():
    conn = sqlite3.connect(REGISTRY_DB)
    conn.row_factory = sqlite3.Row
    return conn


def init_registry():
    conn = _registry_conn()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS months (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            db_file TEXT NOT NULL,
            created_at TEXT
        )
    ''')
    conn.commit()
    conn.close()


def get_all_months():
    conn = _registry_conn()
    rows = conn.execute('SELECT * FROM months ORDER BY id').fetchall()
    conn.close()
    return rows


def add_month(name):
    """Create a new month with its own fresh database file."""
    conn = _registry_conn()
    cur = conn.cursor()
    cur.execute('INSERT INTO months (name, db_file, created_at) VALUES (?, ?, ?)',
                (name, '', datetime.now().isoformat()))
    month_id = cur.lastrowid
    db_file = f'finance_month_{month_id}.db'
    cur.execute('UPDATE months SET db_file = ? WHERE id = ?', (db_file, month_id))
    conn.commit()
    conn.close()
    # build the fresh tables in the new file
    open_month(month_id)
    init_db()
    return month_id


def delete_month(month_id):
    """Remove a month from the registry and delete its database file."""
    conn = _registry_conn()
    row = conn.execute('SELECT db_file FROM months WHERE id = ?', (month_id,)).fetchone()
    conn.execute('DELETE FROM months WHERE id = ?', (month_id,))
    conn.commit()
    conn.close()
    if row and row['db_file'] and os.path.exists(row['db_file']):
        try:
            os.remove(row['db_file'])
        except OSError:
            pass


def open_month(month_id):
    """Point all future queries at this month's database file."""
    global _active_db
    conn = _registry_conn()
    row = conn.execute('SELECT db_file FROM months WHERE id = ?', (month_id,)).fetchone()
    conn.close()
    if row and row['db_file']:
        _active_db = row['db_file']
        init_db()
    return _active_db


def init_db():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('\n        CREATE TABLE IF NOT EXISTS income (\n            id INTEGER PRIMARY KEY CHECK (id = 1),\n            salary REAL DEFAULT 0,\n            bonus REAL DEFAULT 0\n        )\n    ')
    cur.execute('INSERT OR IGNORE INTO income (id, salary, bonus) VALUES (1, 0, 0)')
    cur.execute('\n        CREATE TABLE IF NOT EXISTS budget (\n            id INTEGER PRIMARY KEY AUTOINCREMENT,\n            category TEXT NOT NULL UNIQUE,\n            planned_spend REAL DEFAULT 0,\n            planned_save REAL DEFAULT 0\n        )\n    ')
    cur.execute("\n        CREATE TABLE IF NOT EXISTS transactions (\n            id INTEGER PRIMARY KEY AUTOINCREMENT,\n            category TEXT NOT NULL,\n            amount REAL NOT NULL,\n            source TEXT DEFAULT 'manual',\n            note TEXT,\n            date TEXT\n        )\n    ")
    cur.execute('\n        CREATE TABLE IF NOT EXISTS savings (\n            id INTEGER PRIMARY KEY CHECK (id = 1),\n            balance REAL DEFAULT 0\n        )\n    ')
    cur.execute('INSERT OR IGNORE INTO savings (id, balance) VALUES (1, 0)')
    cur.execute('\n        CREATE TABLE IF NOT EXISTS bank_statements (\n            id INTEGER PRIMARY KEY AUTOINCREMENT,\n            filename TEXT,\n            period TEXT,\n            money_in REAL DEFAULT 0,\n            money_out REAL DEFAULT 0,\n            imported_at TEXT\n        )\n    ')
    cur.execute('\n        CREATE TABLE IF NOT EXISTS goals (\n            id INTEGER PRIMARY KEY AUTOINCREMENT,\n            item TEXT NOT NULL,\n            cost REAL NOT NULL,\n            months INTEGER NOT NULL,\n            created_at TEXT\n        )\n    ')
    cur.execute('\n        CREATE TABLE IF NOT EXISTS loans (\n            id INTEGER PRIMARY KEY AUTOINCREMENT,\n            name TEXT NOT NULL,\n            principal REAL NOT NULL,\n            annual_rate REAL NOT NULL,\n            monthly_payment REAL NOT NULL,\n            created_at TEXT\n        )\n    ')
    cur.execute('\n        CREATE TABLE IF NOT EXISTS investments (\n            id INTEGER PRIMARY KEY AUTOINCREMENT,\n            name TEXT NOT NULL,\n            type TEXT,\n            amount_invested REAL DEFAULT 0,\n            monthly_change REAL DEFAULT 0,\n            created_at TEXT\n        )\n    ')
    conn.commit()
    conn.close()

def set_income(salary, bonus):
    conn = get_connection()
    conn.execute('UPDATE income SET salary = ?, bonus = ? WHERE id = 1', (salary, bonus))
    conn.commit()
    conn.close()

def get_income():
    conn = get_connection()
    row = conn.execute('SELECT salary, bonus FROM income WHERE id = 1').fetchone()
    conn.close()
    return (row['salary'], row['bonus'])

def get_monthly_income():
    salary, bonus = get_income()
    total = salary + bonus + get_total_investment_change()
    return round(total, 2)

def add_or_update_budget(category, planned_spend, planned_save):
    conn = get_connection()
    conn.execute('\n        INSERT INTO budget (category, planned_spend, planned_save)\n        VALUES (?, ?, ?)\n        ON CONFLICT(category) DO UPDATE SET\n            planned_spend = excluded.planned_spend,\n            planned_save  = excluded.planned_save\n    ', (category, planned_spend, planned_save))
    conn.commit()
    conn.close()

def get_all_budget():
    conn = get_connection()
    rows = conn.execute('SELECT * FROM budget ORDER BY category').fetchall()
    conn.close()
    return rows

def delete_budget(category):
    conn = get_connection()
    conn.execute('DELETE FROM budget WHERE category = ?', (category,))
    conn.commit()
    conn.close()

def get_total_planned_save():
    conn = get_connection()
    row = conn.execute('SELECT SUM(planned_save) AS s FROM budget').fetchone()
    conn.close()
    return row['s'] or 0.0

def add_transaction(category, amount, source='manual', note=''):
    conn = get_connection()
    conn.execute('INSERT INTO transactions (category, amount, source, note, date) VALUES (?, ?, ?, ?, ?)', (category, amount, source, note, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def get_all_transactions():
    conn = get_connection()
    rows = conn.execute('SELECT * FROM transactions ORDER BY id DESC').fetchall()
    conn.close()
    return rows

def delete_transaction(transaction_id):
    conn = get_connection()
    conn.execute('DELETE FROM transactions WHERE id = ?', (transaction_id,))
    conn.commit()
    conn.close()

def get_spending_by_category():
    conn = get_connection()
    rows = conn.execute('\n        SELECT category, SUM(amount) AS total\n        FROM transactions GROUP BY category\n    ').fetchall()
    conn.close()
    return {r['category']: r['total'] for r in rows}

def get_total_spending():
    conn = get_connection()
    row = conn.execute('SELECT SUM(amount) AS total FROM transactions').fetchone()
    conn.close()
    return row['total'] or 0.0

def get_savings_base():
    conn = get_connection()
    row = conn.execute('SELECT balance FROM savings WHERE id = 1').fetchone()
    conn.close()
    return row['balance']

def set_savings(amount):
    conn = get_connection()
    conn.execute('UPDATE savings SET balance = ? WHERE id = 1', (amount,))
    conn.commit()
    conn.close()

def get_savings():
    base = get_savings_base()
    live = base + get_monthly_income() - get_total_spending()
    return round(live, 2)

def adjust_savings(delta):
    conn = get_connection()
    conn.execute('UPDATE savings SET balance = balance + ? WHERE id = 1', (delta,))
    conn.commit()
    conn.close()

def get_monthly_surplus():
    return round(get_monthly_income() - get_total_spending(), 2)

def add_bank_statement(filename, period, money_in, money_out):
    conn = get_connection()
    conn.execute('\n        INSERT INTO bank_statements (filename, period, money_in, money_out, imported_at)\n        VALUES (?, ?, ?, ?, ?)\n    ', (filename, period, money_in, money_out, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def get_all_bank_statements():
    conn = get_connection()
    rows = conn.execute('SELECT * FROM bank_statements ORDER BY id DESC').fetchall()
    conn.close()
    return rows

def delete_bank_statement(stmt_id):
    conn = get_connection()
    conn.execute('DELETE FROM bank_statements WHERE id = ?', (stmt_id,))
    conn.commit()
    conn.close()

def add_goal(item, cost, months):
    conn = get_connection()
    conn.execute('INSERT INTO goals (item, cost, months, created_at) VALUES (?, ?, ?, ?)', (item, cost, months, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def get_all_goals():
    conn = get_connection()
    rows = conn.execute('SELECT * FROM goals ORDER BY id DESC').fetchall()
    conn.close()
    return rows

def delete_goal(goal_id):
    conn = get_connection()
    conn.execute('DELETE FROM goals WHERE id = ?', (goal_id,))
    conn.commit()
    conn.close()

def add_loan(name, principal, annual_rate, monthly_payment):
    conn = get_connection()
    conn.execute('\n        INSERT INTO loans (name, principal, annual_rate, monthly_payment, created_at)\n        VALUES (?, ?, ?, ?, ?)\n    ', (name, principal, annual_rate, monthly_payment, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def get_all_loans():
    conn = get_connection()
    rows = conn.execute('SELECT * FROM loans ORDER BY id DESC').fetchall()
    conn.close()
    return rows

def delete_loan(loan_id):
    conn = get_connection()
    conn.execute('DELETE FROM loans WHERE id = ?', (loan_id,))
    conn.commit()
    conn.close()

def add_investment(name, inv_type, amount_invested, monthly_change):
    conn = get_connection()
    conn.execute('\n        INSERT INTO investments (name, type, amount_invested, monthly_change, created_at)\n        VALUES (?, ?, ?, ?, ?)\n    ', (name, inv_type, amount_invested, monthly_change, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def get_all_investments():
    conn = get_connection()
    rows = conn.execute('SELECT * FROM investments ORDER BY id DESC').fetchall()
    conn.close()
    return rows

def delete_investment(inv_id):
    conn = get_connection()
    conn.execute('DELETE FROM investments WHERE id = ?', (inv_id,))
    conn.commit()
    conn.close()

def get_total_invested():
    conn = get_connection()
    row = conn.execute('SELECT SUM(amount_invested) AS s FROM investments').fetchone()
    conn.close()
    return row['s'] or 0.0

def get_total_investment_change():
    conn = get_connection()
    row = conn.execute('SELECT SUM(monthly_change) AS s FROM investments').fetchone()
    conn.close()
    return row['s'] or 0.0


def get_full_context():
    """Build a complete plain-text summary of everything the user has entered,
    so the AI assistant knows all their numbers - income, budget, spending by
    category, every investment with its monthly profit/loss, savings, loans,
    and goals. The AI reads this; it does not do any of the math itself."""
    lines = []

    salary, bonus = get_income()
    lines.append(f"Monthly salary: {salary:,.0f}")
    lines.append(f"Monthly bonus: {bonus:,.0f}")
    lines.append(f"Total monthly income (incl. investment change): {get_monthly_income():,.0f}")
    lines.append(f"Total spent this month: {get_total_spending():,.0f}")
    lines.append(f"Monthly surplus (income - spending): {get_monthly_surplus():,.0f}")
    lines.append(f"Current savings (live): {get_savings():,.0f}")

    budget = get_all_budget()
    if budget:
        lines.append("Budget categories (max planned spend):")
        for b in budget:
            lines.append(f"  - {b['category']}: {b['planned_spend']:,.0f}")

    spending = get_spending_by_category()
    if spending:
        lines.append("Actual spending by category:")
        for cat, amt in spending.items():
            lines.append(f"  - {cat}: {amt:,.0f}")

    investments = get_all_investments()
    if investments:
        lines.append("Investments (this month's profit/loss):")
        for inv in investments:
            ch = inv['monthly_change']
            sign = "profit" if ch >= 0 else "loss"
            name = inv['name']
            typ = f" ({inv['type']})" if inv['type'] else ""
            lines.append(f"  - {name}{typ}: {ch:+,.0f} {sign} this month")
        lines.append(f"Total investment profit/loss this month: {get_total_investment_change():+,.0f}")
        lines.append(f"Total amount invested: {get_total_invested():,.0f}")
    else:
        lines.append("Investments: none entered yet")

    loans = get_all_loans()
    if loans:
        lines.append("Loans:")
        for ln in loans:
            lines.append(f"  - {ln['name']}: {ln['principal']:,.0f} at {ln['annual_rate']:.1f}%, paying {ln['monthly_payment']:,.0f}/month")

    goals = get_all_goals()
    if goals:
        lines.append("Goals:")
        for g in goals:
            lines.append(f"  - {g['item']}: {g['cost']:,.0f} over {g['months']} months")

    return "\n".join(lines)


if __name__ == '__main__':
    init_db()
    print('All tables created.')
    print(get_full_context())