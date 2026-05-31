"""
gemini_helper.py
----------------
Talks to Google's Gemini AI for FEEDBACK and the CHATBOT.
Gemini is NOT used for math - we do all calculations ourselves.
Gemini only reads our numbers and gives human-friendly advice.

KEY DESIGN GOAL: never crash the app.
If there's no key, no internet, or the API errors out, every function
returns a polite fallback string instead of raising an exception.
"""

import urllib.request
import urllib.error
import json
import config


def _is_key_set():
    """True only if the user actually pasted a real-looking key."""
    key = config.GEMINI_API_KEY
    return key and key != "PASTE_YOUR_KEY_HERE" and len(key) > 10


def _ask_gemini(prompt):
    """
    Low-level call. Sends a prompt, returns Gemini's text reply.
    Uses only the standard library (urllib) so there's nothing extra
    to install. If anything goes wrong, we return a friendly message.
    """
    if not _is_key_set():
        return "(AI feedback unavailable - no API key set in config.py)"

    url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
           f"{config.GEMINI_MODEL}:generateContent?key={config.GEMINI_API_KEY}")


    body = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}]
    }).encode("utf-8")

    req = urllib.request.Request(
        url, data=body, headers={"Content-Type": "application/json"}
    )

    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        return data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except urllib.error.URLError:
        return "(AI feedback unavailable - check your internet connection.)"
    except (KeyError, IndexError):
        return "(AI gave an unexpected response. Try again.)"
    except Exception as e:
        return f"(AI error: {e})"


def get_budget_feedback(monthly_income, total_spent, surplus, score):
    """Feature 16: AI feedback on the user's overall financial month."""
    prompt = (
        "You are a friendly family finance coach. In 3-4 short sentences, "
        "give encouraging, practical feedback. Do NOT do any math, just react "
        "to these numbers:\n"
        f"- Monthly income: {monthly_income}\n"
        f"- Total spent: {total_spent}\n"
        f"- Monthly surplus (saved): {surplus}\n"
        f"- Savings score out of 100: {score}\n"
    )
    return _ask_gemini(prompt)


def get_emergency_feedback(months_survivable, shortfall):
    """Feature 12: AI feedback on emergency preparedness."""
    prompt = (
        "You are a calm financial advisor. In 2-3 sentences, comment on this "
        "family's emergency preparedness. Be reassuring but honest:\n"
        f"- Months they could survive with no income: {months_survivable}\n"
        f"- Shortfall vs recommended fund: {shortfall}\n"
    )
    return _ask_gemini(prompt)


def chat(user_message, context_summary=""):
    """Feature 10: the chatbot. context_summary lets us feed it the user's
    current numbers so answers are personalised."""
    prompt = (
        "You are a helpful family finance assistant inside a budgeting app. "
        "Keep answers short and practical. Here is the user's current "
        f"financial snapshot:\n{context_summary}\n\n"
        f"User asks: {user_message}"
    )
    return _ask_gemini(prompt)


def increase_income_advice(profile):
    """
    'Grow & Save' - Increase Income survey.
    `profile` is a dict of question -> answer covering job, company, education,
    certifications, skills, city, places willing to relocate, etc. The AI gives
    specific, actionable ways to earn more.
    """
    details = "\n".join(f"- {q}: {a}" for q, a in profile.items() if a)
    prompt = (
        "You are an experienced career and income coach. A person has filled in "
        "a detailed survey about their work life. Give them a specific, practical "
        "plan to increase their income. Organise your answer under clear headings "
        "such as: Certifications & courses to take, Higher education worth it (or not), "
        "Skills to build (including communication/speaking), Companies or roles to "
        "target, Relocation opportunities, and Side income or investment ideas. "
        "Refer to the actual companies, city and qualifications they mention. Where "
        "you suggest a certification or company, say briefly WHY it fits them. Use "
        "short bullet points. Be encouraging, realistic, and concrete - avoid vague "
        "advice. Do not invent exact salary numbers; speak in general terms about "
        "earning potential.\n\n"
        f"Their survey answers:\n{details}"
    )
    return _ask_gemini(prompt)


def reduce_spending_advice(profile, spending_by_category):
    """
    'Grow & Save' - Reduce Spending survey.
    `profile` = question -> answer (where they shop, housing, activities, etc.);
    `spending_by_category` = their actual recorded spending. The AI analyses
    where money goes and gives concrete ways to spend less.
    """
    details = "\n".join(f"- {q}: {a}" for q, a in profile.items() if a)
    if spending_by_category:
        spend_lines = "\n".join(f"- {c}: {a:,.0f}" for c, a in spending_by_category.items())
    else:
        spend_lines = "- (no spending recorded in the app yet)"
    prompt = (
        "You are a practical money-saving coach. A person has filled in a survey "
        "about how and where they spend. Analyse it and give a specific plan to "
        "reduce their spending without hurting their quality of life. Organise "
        "under clear headings such as: Food & groceries, Housing, Transport, "
        "Subscriptions & activities, and Apps & coupons that help. Reference the "
        "actual stores, apps, city and habits they mention. For each suggestion, "
        "give a rough sense of how much it could save per month. Point at their "
        "biggest spending areas first. Use short bullet points. Be concrete, kind, "
        "and non-judgmental.\n\n"
        f"Their survey answers:\n{details}\n\n"
        f"Their recorded spending this month:\n{spend_lines}"
    )
    return _ask_gemini(prompt)


_KEYWORD_CATEGORIES = {
    "food": ["kfc", "pizza", "mcdonald", "restaurant", "cafe", "coffee", "starbucks",
             "grocery", "supermarket", "food", "dominos", "burger", "subway", "dining"],
    "rent": ["rent", "landlord", "lease", "apartment", "housing"],
    "transport": ["uber", "lyft", "fuel", "petrol", "gas station", "shell", "taxi",
                  "transport", "metro", "bus", "train", "parking"],
    "utilities": ["electric", "water bill", "gas bill", "internet", "wifi", "phone",
                  "utility", "telecom"],
    "shopping": ["amazon", "walmart", "target", "mall", "store", "clothing", "shop"],
    "entertainment": ["netflix", "spotify", "cinema", "movie", "game", "disney"],
    "health": ["pharmacy", "hospital", "clinic", "doctor", "medical", "gym"],
    "tuition": ["tuition", "school", "university", "college", "course", "education"],
}


def _fallback_category(description):
    """Guess a category from keywords when the AI can't be reached."""
    low = description.lower()
    for category, words in _KEYWORD_CATEGORIES.items():
        if any(w in low for w in words):
            return category
    return "other"


def categorize_transactions(descriptions):
    """
    Take a list of transaction descriptions (e.g. ['KFC', 'PIZZA HUT', 'RENT PAYMENT'])
    and return a matching list of categories (e.g. ['food', 'food', 'rent']).

    We ask Gemini to classify them all at once and return JSON. If anything
    goes wrong (no key, no internet, bad reply), we fall back to keyword
    matching so the Bank import still works. The AI only LABELS - it never
    touches the money amounts; our own code handles those.
    """
    if not descriptions:
        return []

    if not _is_key_set():
        return [_fallback_category(d) for d in descriptions]

    numbered = "\n".join(f"{i}. {d}" for i, d in enumerate(descriptions))
    prompt = (
        "You are a transaction categorizer for a budgeting app. "
        "For each numbered transaction description below, assign ONE short "
        "lowercase spending category. Use simple categories like: food, rent, "
        "transport, utilities, shopping, entertainment, health, tuition, other. "
        "Reply with ONLY a JSON array of strings, one category per transaction, "
        "in the same order. No explanation, no markdown.\n\n"
        f"{numbered}"
    )
    reply = _ask_gemini(prompt)


    try:
        cleaned = reply.strip().replace("```json", "").replace("```", "").strip()
        result = json.loads(cleaned)
        if isinstance(result, list) and len(result) == len(descriptions):
            return [str(c).lower().strip() for c in result]
    except Exception:
        pass
    return [_fallback_category(d) for d in descriptions]


if __name__ == "__main__":
    print("Key set?", _is_key_set())
    print(get_budget_feedback(4000, 2500, 1500, 85))
