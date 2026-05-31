"""
pdf_import.py
-------------
Handles importing a bank statement PDF (feature 4).

Reality check we tell judges honestly: every bank formats statements
differently, so fully automatic parsing is unreliable. Our approach:
  1. Try to pull raw text out of the PDF.
  2. Scan that text for likely "total in" / "total out" numbers.
  3. Whatever we find, we PRE-FILL the boxes - the user confirms or
     corrects before saving. Human-in-the-loop = trustworthy.

We use pdfplumber if available; if not, we degrade gracefully to
manual entry so the feature never hard-fails.
"""

import re

try:
    import pdfplumber
    HAVE_PDF = True
except ImportError:
    HAVE_PDF = False


def extract_text(path):
    """Return all text from the PDF, or empty string if we can't."""
    if not HAVE_PDF:
        return ""
    try:
        text = ""
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                text += (page.extract_text() or "") + "\n"
        return text
    except Exception:
        return ""


def guess_totals(text):
    """
    Best-effort: find money amounts near words like 'deposit/credit/in'
    and 'withdrawal/debit/out'. Returns (money_in, money_out) guesses.
    If nothing is found, returns (0, 0) and the user types them in.
    """
    money_in = 0.0
    money_out = 0.0


    for line in text.splitlines():
        low = line.lower()
        amounts = re.findall(r"[\d,]+\.\d{2}", line)
        if not amounts:
            continue
        value = float(amounts[-1].replace(",", ""))
        if any(w in low for w in ["deposit", "credit", "salary", "transfer in"]):
            money_in += value
        elif any(w in low for w in ["withdraw", "debit", "purchase", "payment", "transfer out"]):
            money_out += value

    return round(money_in, 2), round(money_out, 2)


def extract_transactions(text):
    """
    Pull individual SPENDING transactions out of the statement text.
    Returns a list of dicts: [{"description": "KFC", "amount": 24.50}, ...]

    For each line that looks like an outgoing payment (debit/purchase/etc.)
    and contains a money amount, we take the amount and use the surrounding
    words as the description. The description is later sent to Gemini for
    categorizing. We skip incoming money (deposits/credits).
    """
    transactions = []
    out_words = ["withdraw", "debit", "purchase", "payment", "pos", "card",
                 "transfer out", "paid", "buy"]
    in_words = ["deposit", "credit", "salary", "transfer in", "refund"]

    def has_word(words, text):

        return any(re.search(r"\b" + re.escape(w) + r"\b", text) for w in words)

    for line in text.splitlines():
        low = line.lower()
        amounts = re.findall(r"[\d,]+\.\d{2}", line)
        if not amounts:
            continue

        if has_word(in_words, low) and not has_word(out_words, low):
            continue

        value = float(amounts[-1].replace(",", ""))

        desc = re.sub(r"[\d,]+\.\d{2}", "", line)
        desc = re.sub(r"\s{2,}", " ", desc).strip(" -|\t")
        if not desc:
            desc = "Unknown transaction"
        transactions.append({"description": desc, "amount": value})

    return transactions


def import_statement(path):
    """High-level: given a file path, return guessed totals AND the list of
    individual transactions for categorizing."""
    text = extract_text(path)
    money_in, money_out = guess_totals(text)
    return {
        "had_text": bool(text),
        "money_in": money_in,
        "money_out": money_out,
        "transactions": extract_transactions(text),
    }


if __name__ == "__main__":
    print("pdfplumber available?", HAVE_PDF)
    print(guess_totals("Salary deposit 3,000.00\nGrocery purchase 240.50\nRent payment 1,200.00"))
