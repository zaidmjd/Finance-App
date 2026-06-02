import re
try:
    import pdfplumber
    HAVE_PDF = True
except ImportError:
    HAVE_PDF = False

def extract_text(path):
    if not HAVE_PDF:
        return ''
    try:
        text = ''
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                text += (page.extract_text() or '') + '\n'
        return text
    except Exception:
        return ''

def guess_totals(text):
    money_in = 0.0
    money_out = 0.0
    for line in text.splitlines():
        low = line.lower()
        amounts = re.findall('[\\d,]+\\.\\d{2}', line)
        if not amounts:
            continue
        value = float(amounts[-1].replace(',', ''))
        if any((w in low for w in ['deposit', 'credit', 'salary', 'transfer in'])):
            money_in += value
        elif any((w in low for w in ['withdraw', 'debit', 'purchase', 'payment', 'transfer out'])):
            money_out += value
    return (round(money_in, 2), round(money_out, 2))

def extract_transactions(text):
    transactions = []
    out_words = ['withdraw', 'debit', 'purchase', 'payment', 'pos', 'card', 'transfer out', 'paid', 'buy']
    in_words = ['deposit', 'credit', 'salary', 'transfer in', 'refund']

    def has_word(words, text):
        return any((re.search('\\b' + re.escape(w) + '\\b', text) for w in words))
    for line in text.splitlines():
        low = line.lower()
        amounts = re.findall('[\\d,]+\\.\\d{2}', line)
        if not amounts:
            continue
        if has_word(in_words, low) and (not has_word(out_words, low)):
            continue
        value = float(amounts[-1].replace(',', ''))
        desc = re.sub('[\\d,]+\\.\\d{2}', '', line)
        desc = re.sub('\\s{2,}', ' ', desc).strip(' -|\t')
        if not desc:
            desc = 'Unknown transaction'
        transactions.append({'description': desc, 'amount': value})
    return transactions

def import_statement(path):
    text = extract_text(path)
    money_in, money_out = guess_totals(text)
    return {'had_text': bool(text), 'money_in': money_in, 'money_out': money_out, 'transactions': extract_transactions(text)}
if __name__ == '__main__':
    print('pdfplumber available?', HAVE_PDF)
    print(guess_totals('Salary deposit 3,000.00\nGrocery purchase 240.50\nRent payment 1,200.00'))