"""
finance_logic.py
----------------
PURE MATH. No database, no GUI - just functions that take numbers in
and give numbers out. This is the easiest file to defend to judges
because every function is testable on its own and has no side effects.

Contains: loan repayment schedule, goal monthly plan,
emergency fund survival, and the savings score.
"""


def purchase_plan(cost, monthly_payment=None, months=None):
    """
    Smart Buying plan for an item costing `cost`.
    The user fills exactly ONE of:
      - monthly_payment  -> we work out how many months it takes
      - months           -> we work out the monthly payment

    Rules:
      - If neither is given -> error.
      - If BOTH are given and they don't agree (monthly*months != cost,
        within a small tolerance) -> error explaining the mismatch.
      - If both agree, that's fine.

    Returns a dict with monthly_amount, months, and a schedule table.
    """
    if cost <= 0:
        return {"error": "Enter a cost greater than zero."}

    has_pay = monthly_payment is not None and monthly_payment > 0
    has_months = months is not None and months > 0

    if not has_pay and not has_months:
        return {"error": "Enter either a monthly payment OR a number of months."}

    if has_pay and has_months:

        implied_cost = monthly_payment * months
        if abs(implied_cost - cost) > 0.5:
            need_months = cost / monthly_payment
            return {"error": (
                f"These don't match. Paying {monthly_payment:,.0f}/month for "
                f"{months} months covers {implied_cost:,.0f}, not {cost:,.0f}. "
                f"At {monthly_payment:,.0f}/month it actually takes "
                f"{need_months:.1f} months. Clear one field and let us fill it.")}
        final_months = int(round(months))
        final_payment = monthly_payment
    elif has_pay:
        final_payment = monthly_payment
        final_months = int(round(cost / monthly_payment + 0.4999))
    else:
        final_months = int(round(months))
        final_payment = cost / final_months


    schedule = []
    paid = 0.0
    for m in range(1, final_months + 1):
        paid += final_payment
        schedule.append({
            "month": m,
            "payment": round(final_payment, 2),
            "paid_so_far": round(min(paid, cost), 2),
            "remaining": round(max(cost - paid, 0), 2),
        })
    return {
        "monthly_amount": round(final_payment, 2),
        "months": final_months,
        "schedule": schedule,
    }


def loan_schedule(principal, annual_rate_percent, monthly_payment):
    """
    Build a month-by-month loan repayment table.

    The math (standard amortisation):
      - Each month interest is added:  interest = balance * monthly_rate
      - The payment first covers that interest, the rest reduces the balance.
      - monthly_rate = annual_rate / 100 / 12

    Returns a list of dicts, one per month, plus a 'safety' guard so a
    too-small payment can't loop forever.
    """
    monthly_rate = annual_rate_percent / 100 / 12
    balance = principal
    schedule = []
    month = 0


    if monthly_payment <= balance * monthly_rate:
        return {"error": "Monthly payment too low to ever repay this loan.",
                "schedule": []}

    while balance > 0 and month < 600:
        month += 1
        interest = balance * monthly_rate
        principal_paid = monthly_payment - interest
        balance -= principal_paid
        if balance < 0:

            monthly_payment += balance
            balance = 0
        schedule.append({
            "month": month,
            "payment": round(monthly_payment, 2),
            "interest": round(interest, 2),
            "principal": round(principal_paid, 2),
            "balance": round(balance, 2),
        })

    total_paid = sum(row["payment"] for row in schedule)
    return {
        "schedule": schedule,
        "months_to_repay": month,
        "total_paid": round(total_paid, 2),
        "total_interest": round(total_paid - principal, 2),
    }


def goal_plan(cost, months):
    """
    For a goal (an item costing `cost` you want in `months` months):
    how much to set aside each month, and the running saved total.

    Simple: monthly_amount = cost / months.
    We return a table so the UI can show progress month by month.
    """
    if months <= 0:
        return {"error": "Months must be at least 1.", "schedule": []}

    monthly_amount = cost / months
    schedule = []
    saved = 0.0
    for m in range(1, months + 1):
        saved += monthly_amount
        schedule.append({
            "month": m,
            "save_this_month": round(monthly_amount, 2),
            "saved_so_far": round(saved, 2),
            "remaining": round(cost - saved, 2),
        })
    return {"monthly_amount": round(monthly_amount, 2), "schedule": schedule}


def emergency_fund(monthly_expense, total_savings, recommended_months=6):
    """
    Emergency fund analysis (feature 12).

    - recommended = how much you SHOULD have (default 6 months of expenses).
    - months_survivable = how long your current savings would last if income
      stopped and you kept spending at the same rate.
    """
    recommended = monthly_expense * recommended_months
    if monthly_expense <= 0:
        months_survivable = 0
    else:
        months_survivable = total_savings / monthly_expense

    return {
        "recommended_fund": round(recommended, 2),
        "current_savings": round(total_savings, 2),
        "shortfall": round(max(0, recommended - total_savings), 2),
        "months_survivable": round(months_survivable, 1),
    }


def savings_score(planned_save, actual_surplus):
    """
    A 0-100 score (feature 14) comparing how much you actually saved
    (actual_surplus) against how much you PLANNED to save (planned_save).

    - If you planned to save 0, we can't grade against a goal, so we give
      a neutral 50 unless you have a positive surplus (then 100).
    - Otherwise score = (actual / planned) * 100, capped at 100.
    """
    if planned_save <= 0:
        return 100 if actual_surplus > 0 else 50

    score = (actual_surplus / planned_save) * 100
    score = max(0, min(100, score))
    return round(score, 1)


if __name__ == "__main__":
    print("LOAN:")
    result = loan_schedule(10000, 12, 500)
    print("  months to repay:", result["months_to_repay"])
    print("  total interest:", result["total_interest"])

    print("GOAL:")
    g = goal_plan(1200, 6)
    print("  save per month:", g["monthly_amount"])

    print("EMERGENCY:")
    e = emergency_fund(2000, 12000)
    print("  recommended:", e["recommended_fund"], "survive months:", e["months_survivable"])

    print("SCORE:")
    print("  ", savings_score(500, 450))
