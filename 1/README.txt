FAMILY FINANCE MANAGER - setup
==============================

1. Install Python 3.10+ (you have it).

2. Install the two extra libraries:
   pip install customtkinter matplotlib pdfplumber

3. (Optional but for full marks) Get a FREE Gemini API key:
   - Go to https://aistudio.google.com/apikey
   - Create a key, copy it
   - Open config.py, paste it between the quotes on the GEMINI_API_KEY line
   The app works WITHOUT a key - AI tabs just show "unavailable".

4. Run the app:
   python main.py

FILES
-----
main.py          - the GUI, all 11 tabs (RUN THIS)
database.py      - all data storage (SQLite)
finance_logic.py - all the math (loans, goals, emergency, score)
gemini_helper.py - AI feedback + chatbot
pdf_import.py    - bank statement PDF reading
config.py        - your API key goes here

FEATURE MAP (what to point judges to)
-------------------------------------
1 income+frequency+bonus ... Income tab + database.get_monthly_income
2 planned spend/save ........ Budget tab
3 actual spending ........... Spending tab
4 bank statement + browse ... Bank tab + pdf_import.py
5 manual cash entry ......... Spending tab (cash/bank dropdown)
6 goals monthly plan ........ Goals tab + finance_logic.goal_plan
7 savings up/down ........... Savings tab
8 loan calculator ........... Loans tab + finance_logic.loan_schedule
9 investment portfolio ...... Investments tab
10 AI chatbot ............... Assistant tab
12 emergency fund ........... Emergency tab + finance_logic.emergency_fund
14 report + graph + score ... Report tab
16 AI feedback .............. Report & Emergency tabs
