import urllib.request
import urllib.error
import json
import config

def _clean(text):
    if not text or text.startswith('('):
        return text
    out_lines = []
    for line in text.split('\n'):
        s = line.rstrip()
        stripped = s.lstrip()
        if stripped.startswith('* ') or stripped.startswith('- '):
            indent = s[:len(s) - len(stripped)]
            s = indent + '- ' + stripped[2:]
        s = s.replace('**', '').replace('*', '')
        s = s.lstrip('#').rstrip()
        out_lines.append(s)
    cleaned, blank = ([], 0)
    for ln in out_lines:
        if ln.strip() == '':
            blank += 1
            if blank <= 1:
                cleaned.append('')
        else:
            blank = 0
            cleaned.append(ln)
    return '\n'.join(cleaned).strip()

def _is_key_set():
    key = config.GEMINI_API_KEY
    return key and key != 'PASTE_YOUR_KEY_HERE' and (len(key) > 10)
_MODELS_TO_TRY = ['gemini-2.5-flash', 'gemini-2.5-flash-lite', 'gemini-flash-latest', 'gemini-2.0-flash']
_working_model = None

def _call_model(model, prompt):
    url = f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={config.GEMINI_API_KEY}'
    body = json.dumps({'contents': [{'parts': [{'text': prompt}]}]}).encode('utf-8')
    req = urllib.request.Request(url, data=body, headers={'Content-Type': 'application/json'}, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            data = json.loads(resp.read().decode('utf-8'))
        text = data['candidates'][0]['content']['parts'][0]['text'].strip()
        return (text, None)
    except urllib.error.HTTPError as e:
        detail = ''
        try:
            detail = json.loads(e.read().decode('utf-8')).get('error', {}).get('message', '')
        except Exception:
            pass
        return (None, f'HTTP {e.code}: {detail or e.reason}')
    except urllib.error.URLError as e:
        return (None, f'no-connection: {e.reason}')
    except (KeyError, IndexError):
        return (None, 'unexpected-response')
    except Exception as e:
        return (None, f'error: {e}')

def _ask_gemini(prompt):
    global _working_model
    if not _is_key_set():
        return '(AI feedback unavailable - no API key set in config.py)'
    order = []
    for m in [_working_model, config.GEMINI_MODEL] + _MODELS_TO_TRY:
        if m and m not in order:
            order.append(m)
    last_error = ''
    for model in order:
        text, err = _call_model(model, prompt)
        if text is not None:
            _working_model = model
            return _clean(text)
        last_error = err
        if err and err.startswith('no-connection'):
            return '(AI feedback unavailable - check your internet connection.)'
        if err and err.startswith('HTTP 400') and ('API key not valid' in err):
            return '(AI unavailable - your API key was rejected. Check config.py.)'
        if err and err.startswith('HTTP 403'):
            return '(AI unavailable - key lacks permission or quota. Check your Google account.)'
    return f'(AI unavailable - {last_error})'

def get_budget_feedback(monthly_income, total_spent, surplus, score):
    prompt = f'You are a friendly family finance coach. In 3-4 short sentences, give encouraging, practical feedback. Do NOT do any math, just react to these numbers:\n- Monthly income: {monthly_income}\n- Total spent: {total_spent}\n- Monthly surplus (saved): {surplus}\n- Savings score out of 100: {score}\n'
    return _ask_gemini(prompt)

def get_emergency_feedback(months_survivable, shortfall):
    prompt = f"You are a calm financial advisor. In 2-3 sentences, comment on this family's emergency preparedness. Be reassuring but honest:\n- Months they could survive with no income: {months_survivable}\n- Shortfall vs recommended fund: {shortfall}\n"
    return _ask_gemini(prompt)

def chat(user_message, context_summary=''):
    prompt = f"You are a sharp, friendly personal finance adviser chatting inside a budgeting app. Give the best, most genuinely useful answer to the user's question - clear and to the point, usually 2-5 sentences (a little longer only if they truly need steps). Write in plain text only - NO asterisks, NO markdown, NO bold. If you list steps, use short dashed lines. Use the user's real numbers below when relevant.\nTheir financial snapshot:\n{context_summary}\n\nUser asks: {user_message}"
    return _ask_gemini(prompt)

def increase_income_advice(profile):
    details = '\n'.join((f'- {q}: {a}' for q, a in profile.items() if a))
    prompt = f'You are a top career and income coach giving advice to one person. Based on their survey answers, give them your best, most useful plan to earn more. Write in plain text only - NO asterisks, NO markdown, NO bold. Use a few short sections with a plain heading line followed by 2-3 short dashed points. Keep the whole reply focused and readable - around 200-260 words. Be specific to their job, city and qualifications; name real certifications, skills, or types of companies and say briefly why each fits them. Sound like a sharp, encouraging mentor. Do not invent exact salary numbers.\n\nTheir survey answers:\n{details}'
    return _ask_gemini(prompt)

def reduce_spending_advice(profile, spending_by_category):
    details = '\n'.join((f'- {q}: {a}' for q, a in profile.items() if a))
    if spending_by_category:
        spend_lines = '\n'.join((f'- {c}: {a:,.0f}' for c, a in spending_by_category.items()))
    else:
        spend_lines = '- (no spending recorded in the app yet)'
    prompt = f'You are a top money-saving coach giving advice to one person. Using their survey answers and recorded spending, give your best plan to spend less without hurting their life. Write in plain text only - NO asterisks, NO markdown, NO bold. Use a few short sections, each a plain heading line followed by 2-3 short dashed points. Keep the whole reply focused - around 200-260 words. Start with their biggest spending areas. Name real cheaper stores, apps or habits and give a rough monthly saving for each. Sound like a sharp, kind adviser.\n\nTheir survey answers:\n{details}\n\nTheir recorded spending this month:\n{spend_lines}'
    return _ask_gemini(prompt)
_KEYWORD_CATEGORIES = {'food': ['kfc', 'pizza', 'mcdonald', 'restaurant', 'cafe', 'coffee', 'starbucks', 'grocery', 'supermarket', 'food', 'dominos', 'burger', 'subway', 'dining'], 'rent': ['rent', 'landlord', 'lease', 'apartment', 'housing'], 'transport': ['uber', 'lyft', 'fuel', 'petrol', 'gas station', 'shell', 'taxi', 'transport', 'metro', 'bus', 'train', 'parking'], 'utilities': ['electric', 'water bill', 'gas bill', 'internet', 'wifi', 'phone', 'utility', 'telecom'], 'shopping': ['amazon', 'walmart', 'target', 'mall', 'store', 'clothing', 'shop'], 'entertainment': ['netflix', 'spotify', 'cinema', 'movie', 'game', 'disney'], 'health': ['pharmacy', 'hospital', 'clinic', 'doctor', 'medical', 'gym'], 'tuition': ['tuition', 'school', 'university', 'college', 'course', 'education']}

def _fallback_category(description):
    low = description.lower()
    for category, words in _KEYWORD_CATEGORIES.items():
        if any((w in low for w in words)):
            return category
    return 'other'

def categorize_transactions(descriptions):
    if not descriptions:
        return []
    if not _is_key_set():
        return [_fallback_category(d) for d in descriptions]
    numbered = '\n'.join((f'{i}. {d}' for i, d in enumerate(descriptions)))
    prompt = f'You are a transaction categorizer for a budgeting app. For each numbered transaction description below, assign ONE short lowercase spending category. Use simple categories like: food, rent, transport, utilities, shopping, entertainment, health, tuition, other. Reply with ONLY a JSON array of strings, one category per transaction, in the same order. No explanation, no markdown.\n\n{numbered}'
    reply = _ask_gemini(prompt)
    try:
        cleaned = reply.strip().replace('```json', '').replace('```', '').strip()
        result = json.loads(cleaned)
        if isinstance(result, list) and len(result) == len(descriptions):
            return [str(c).lower().strip() for c in result]
    except Exception:
        pass
    return [_fallback_category(d) for d in descriptions]
if __name__ == '__main__':
    print('Key set?    ', _is_key_set())
    print('Key length: ', len(config.GEMINI_API_KEY))
    print('Testing each model...')
    for m in _MODELS_TO_TRY:
        text, err = _call_model(m, 'Say hello in 3 words.')
        if text:
            print(f'  {m:24} WORKS -> {text}')
        else:
            print(f'  {m:24} failed -> {err}')
    print()
    print('Final answer via _ask_gemini:')
    print(' ', _ask_gemini('Give one short money saving tip.'))