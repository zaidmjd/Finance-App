import customtkinter as ctk
from tkinter import messagebox, filedialog
import database as db
import finance_logic as fl
import gemini_helper as ai
import pdf_import
import matplotlib
matplotlib.use('TkAgg')
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
COLORS = {'bg': '#EFE7DA', 'sidebar': '#E3D5C0', 'card': '#F7F1E8', 'card_border': '#D8C7AE', 'accent': '#A6764C', 'accent_hi': '#BF8C5E', 'text': '#3D2F22', 'text_soft': '#8A7860', 'good': '#5E7F52', 'bad': '#B05B43', 'nav_idle': '#E3D5C0', 'nav_text': '#5A4632'}
FONT = 'Segoe UI'
FONT_SERIF = 'Georgia'
INPUT_HEIGHT = 52
INPUT_FONT = 16
LABEL_FONT = 16
BTN_HEIGHT = 52
BTN_FONT = 16
INPUT_RADIUS = 12
NAV_ITEMS = [('Home', 'home'), ('Income', 'income'), ('Budget', 'budget'), ('Spending', 'spending'), ('Bank', 'bank'), ('Smart Buying', 'smart'), ('Grow & Save', 'grow'), ('Investments', 'investments'), ('Emergency', 'emergency'), ('Report', 'report'), ('Assistant', 'assistant')]

class FinanceApp(ctk.CTk):

    def __init__(self):
        super().__init__()
        self.title('Family Finance Manager')
        self.geometry('1280x820')
        self.minsize(1120, 700)
        self.configure(fg_color=COLORS['bg'])
        ctk.set_appearance_mode('light')

        db.init_registry()

        self.pages = {}
        self.nav_buttons = {}
        self.app_built = False

        # two top-level screens: the month selector, and the main app
        self.selector_screen = ctk.CTkFrame(self, fg_color=COLORS['bg'])
        self.app_screen = ctk.CTkFrame(self, fg_color=COLORS['bg'])

        self._build_selector()
        self.show_selector()

    # =================== MONTH SELECTOR SCREEN ===================
    def _build_selector(self):
        wrap = ctk.CTkFrame(self.selector_screen, fg_color=COLORS['bg'])
        wrap.pack(fill='both', expand=True, padx=60, pady=40)

        ctk.CTkLabel(wrap, text='FINEASE', font=(FONT_SERIF, 44, 'bold'),
                     text_color=COLORS['accent']).pack(anchor='center', pady=(10, 4))
        ctk.CTkLabel(wrap, text='Choose a month to open, or add a new one.',
                     font=(FONT, 16), text_color=COLORS['text_soft']).pack(anchor='center', pady=(0, 24))

        addcard = self._card(wrap); addcard.pack(fill='x', pady=(0, 20))
        addrow = ctk.CTkFrame(addcard, fg_color='transparent'); addrow.pack(padx=20, pady=18, anchor='w')
        self.new_month_entry = self._entry(addrow, 'e.g. January 2026', 320)
        self.new_month_entry.pack(side='left', padx=(0, 10))
        self.new_month_entry.bind('<Return>', lambda e: self.create_month())
        self._btn(addrow, 'Add Month', self.create_month, width=160).pack(side='left')

        self.months_list = self._scroll(wrap, 'Your months')
        self.months_list.pack(fill='both', expand=True)

    def show_selector(self):
        self.app_screen.pack_forget()
        self.selector_screen.pack(fill='both', expand=True)
        self.refresh_months()

    def refresh_months(self):
        for w in self.months_list.winfo_children():
            w.destroy()
        months = db.get_all_months()
        if not months:
            ctk.CTkLabel(self.months_list, text="No months yet. Add your first month above to get started.",
                         font=(FONT, 15), text_color=COLORS['text_soft']).pack(anchor='w', padx=6, pady=10)
            return
        for m in months:
            row = self._row(self.months_list)
            ctk.CTkLabel(row, text=m['name'], font=(FONT, 18, 'bold'),
                         text_color=COLORS['text']).pack(side='left', padx=20, pady=14)
            self._btn(row, 'Delete', lambda i=m['id'], n=m['name']: self.remove_month(i, n),
                      COLORS['bad'], width=100).pack(side='right', padx=(8, 16))
            self._btn(row, 'Open', lambda i=m['id']: self.open_month(i), width=110).pack(side='right', padx=4)

    def create_month(self):
        name = self.new_month_entry.get().strip()
        if not name:
            return messagebox.showerror('Missing', 'Type a name for the month first.')
        db.add_month(name)
        self.new_month_entry.delete(0, 'end')
        self.refresh_months()

    def remove_month(self, month_id, name):
        if not messagebox.askyesno('Delete month',
                                   f'Delete "{name}" and all its data? This cannot be undone.'):
            return
        db.delete_month(month_id)
        self.refresh_months()

    def open_month(self, month_id):
        db.open_month(month_id)
        # remember the name for display on the home page
        self.active_month_name = ""
        for m in db.get_all_months():
            if m['id'] == month_id:
                self.active_month_name = m['name']
                break
        # build the full app the first time a month is opened, then reuse it
        if not self.app_built:
            self._build_app()
            self.app_built = True
        self.selector_screen.pack_forget()
        self.app_screen.pack(fill='both', expand=True)
        self.show_page('home')

    def _build_app(self):
        self._build_sidebar()
        self._build_content_area()
        self.build_home_page()
        self.build_income_page()
        self.build_budget_page()
        self.build_spending_page()
        self.build_bank_page()
        self.build_smart_page()
        self.build_grow_page()
        self.build_investments_page()
        self.build_emergency_page()
        self.build_report_page()
        self.build_assistant_page()

    def _build_sidebar(self):
        bar = ctk.CTkFrame(self.app_screen, width=210, corner_radius=0, fg_color=COLORS['sidebar'])
        bar.pack(side='left', fill='y')
        bar.pack_propagate(False)
        ctk.CTkLabel(bar, text='FinEase', font=(FONT_SERIF, 26, 'bold'), text_color=COLORS['accent']).pack(pady=(28, 8), padx=24, anchor='w')
        ctk.CTkButton(bar, text='\u2190 Switch Month', anchor='w', font=(FONT, 13),
                      fg_color=COLORS['nav_idle'], text_color=COLORS['accent'],
                      hover_color=COLORS['accent_hi'], corner_radius=10, height=34,
                      command=self.show_selector).pack(fill='x', padx=14, pady=(0, 16))
        for label, key in NAV_ITEMS:
            b = ctk.CTkButton(bar, text=label, anchor='w', font=(FONT, 15), fg_color=COLORS['nav_idle'], text_color=COLORS['nav_text'], hover_color=COLORS['accent_hi'], corner_radius=10, height=42, command=lambda k=key: self.show_page(k))
            b.pack(fill='x', padx=14, pady=3)
            self.nav_buttons[key] = b

    def _build_content_area(self):
        self.content = ctk.CTkFrame(self.app_screen, corner_radius=0, fg_color=COLORS['bg'])
        self.content.pack(side='left', fill='both', expand=True)

    def show_page(self, key):
        for p in self.pages.values():
            p.pack_forget()
        self.pages[key].pack(fill='both', expand=True, padx=40, pady=30)
        for k, b in self.nav_buttons.items():
            if k == key:
                b.configure(fg_color=COLORS['accent'], text_color='white')
            else:
                b.configure(fg_color=COLORS['nav_idle'], text_color=COLORS['nav_text'])
        refreshers = {'home': self.refresh_home, 'income': self.refresh_income, 'budget': self.refresh_budget, 'spending': self.refresh_spending, 'bank': self.refresh_bank, 'investments': self.refresh_investments}
        if key in refreshers:
            refreshers[key]()

    def _new_page(self, key):
        frame = ctk.CTkFrame(self.content, fg_color=COLORS['bg'])
        self.pages[key] = frame
        return frame

    def _title(self, parent, title, subtitle=''):
        ctk.CTkLabel(parent, text=title, font=(FONT, 30, 'bold'), text_color=COLORS['text']).pack(anchor='w')
        if subtitle:
            ctk.CTkLabel(parent, text=subtitle, font=(FONT, 15), text_color=COLORS['text_soft']).pack(anchor='w', pady=(2, 18))
        else:
            ctk.CTkLabel(parent, text='').pack(pady=4)

    def _card(self, parent):
        return ctk.CTkFrame(parent, fg_color=COLORS['card'], border_color=COLORS['card_border'], border_width=1, corner_radius=18)

    def _entry(self, parent, placeholder, width=240):
        return ctk.CTkEntry(parent, placeholder_text=placeholder, width=width, height=INPUT_HEIGHT, corner_radius=INPUT_RADIUS, font=(FONT, INPUT_FONT), fg_color=COLORS['card'], border_color=COLORS['card_border'], text_color=COLORS['text'])

    def _dropdown(self, parent, values, width=220):
        return ctk.CTkOptionMenu(parent, values=values, width=width, height=INPUT_HEIGHT, corner_radius=INPUT_RADIUS, font=(FONT, INPUT_FONT), fg_color=COLORS['accent'], button_color=COLORS['accent_hi'], button_hover_color=COLORS['accent_hi'], text_color='white')

    def _btn(self, parent, text, command, color=None, width=170):
        return ctk.CTkButton(parent, text=text, command=command, width=width, height=BTN_HEIGHT, corner_radius=INPUT_RADIUS, font=(FONT, BTN_FONT, 'bold'), fg_color=color or COLORS['accent'], hover_color=COLORS['accent_hi'], text_color='white')

    def _stat_card(self, parent, label, value, note, value_color=None):
        card = self._card(parent)
        ctk.CTkLabel(card, text=label, font=(FONT, 13), text_color=COLORS['text_soft']).pack(anchor='w', padx=20, pady=(18, 0))
        ctk.CTkLabel(card, text=value, font=(FONT, 26, 'bold'), text_color=value_color or COLORS['text']).pack(anchor='w', padx=20, pady=(2, 0))
        ctk.CTkLabel(card, text=note, font=(FONT, 12), text_color=COLORS['text_soft']).pack(anchor='w', padx=20, pady=(4, 18))
        return card

    def _scroll(self, parent, label=''):
        return ctk.CTkScrollableFrame(parent, fg_color=COLORS['bg'], label_text=label, label_text_color=COLORS['text_soft'], label_fg_color=COLORS['bg'])

    def _row(self, parent):
        r = ctk.CTkFrame(parent, fg_color=COLORS['card'], border_color=COLORS['card_border'], border_width=1, corner_radius=12)
        r.pack(fill='x', pady=5, padx=2)
        return r

    def build_home_page(self):
        page = self._new_page('home')
        ctk.CTkLabel(page, text='FINEASE', font=(FONT_SERIF, 40, 'bold'), text_color=COLORS['accent']).pack(anchor='center', pady=(6, 18))
        self.home_heading = ctk.CTkLabel(page, text='Welcome back.', font=(FONT, 28, 'bold'), text_color=COLORS['text'])
        self.home_heading.pack(anchor='w')
        self.home_subheading = ctk.CTkLabel(page, text="Here's a snapshot of your family's money this month.", font=(FONT, 15), text_color=COLORS['text_soft'])
        self.home_subheading.pack(anchor='w', pady=(2, 24))
        self.home_cards = ctk.CTkFrame(page, fg_color=COLORS['bg'])
        self.home_cards.pack(fill='x')
        for i in range(4):
            self.home_cards.grid_columnconfigure(i, weight=1, uniform='cards')
        sav = self._card(page)
        sav.pack(fill='x', pady=(22, 0))
        inner = ctk.CTkFrame(sav, fg_color='transparent')
        inner.pack(fill='x', padx=24, pady=20)
        left = ctk.CTkFrame(inner, fg_color='transparent')
        left.pack(side='left')
        ctk.CTkLabel(left, text='Total Savings', font=(FONT, 13), text_color=COLORS['text_soft']).pack(anchor='w')
        self.home_savings = ctk.CTkLabel(left, text='', font=(FONT, 30, 'bold'), text_color=COLORS['text'])
        self.home_savings.pack(anchor='w')
        ctk.CTkLabel(left, text='Updates live with income earned, money spent, and investment gains/losses.', font=(FONT, 12), text_color=COLORS['text_soft']).pack(anchor='w', pady=(2, 0))
        self._btn(inner, 'Update Savings', self.update_savings_dialog, width=170).pack(side='right')

    def refresh_home(self):
        name = getattr(self, 'active_month_name', '')
        if name:
            self.home_heading.configure(text=name)
            self.home_subheading.configure(text="Here's a snapshot of this month's money.")
        for w in self.home_cards.winfo_children():
            w.destroy()
        income = db.get_monthly_income()
        spent = db.get_total_spending()
        surplus = db.get_monthly_surplus()
        cards = [('Monthly Income', f'{income:,.0f}', 'Salary + bonus.', COLORS['text']), ('Total Spent', f'{spent:,.0f}', 'All categories.', COLORS['text']), ('This Month', f'{surplus:+,.0f}', 'Surplus' if surplus >= 0 else 'Shortfall', COLORS['good'] if surplus >= 0 else COLORS['bad']), ('Investments P/L', f'{db.get_total_investment_change():+,.0f}', 'This month.', COLORS['good'] if db.get_total_investment_change() >= 0 else COLORS['bad'])]
        for i, (label, value, note, col) in enumerate(cards):
            c = self._stat_card(self.home_cards, label, value, note, col)
            c.grid(row=0, column=i, padx=8, sticky='nsew')
        self.home_savings.configure(text=f'{db.get_savings():,.2f}')

    def update_savings_dialog(self):
        dlg = ctk.CTkInputDialog(text='Enter your current total savings:', title='Update Savings')
        val = dlg.get_input()
        if val is None:
            return
        try:
            amt = float(val)
        except ValueError:
            return messagebox.showerror('Invalid', 'Please enter a number.')
        db.set_savings(amt)
        self.refresh_home()

    def build_income_page(self):
        page = self._new_page('income')
        self._title(page, 'Income', 'Enter your monthly salary and monthly bonus.')
        card = self._card(page)
        card.pack(fill='x', pady=(0, 16))
        form = ctk.CTkFrame(card, fg_color='transparent')
        form.pack(padx=24, pady=24, anchor='w')
        ctk.CTkLabel(form, text='Monthly salary', font=(FONT, LABEL_FONT), text_color=COLORS['text']).grid(row=0, column=0, padx=8, pady=10, sticky='w')
        self.income_salary = self._entry(form, 'e.g. 5000', 320)
        self.income_salary.grid(row=0, column=1, padx=8, pady=10)
        ctk.CTkLabel(form, text='Monthly bonus', font=(FONT, LABEL_FONT), text_color=COLORS['text']).grid(row=1, column=0, padx=8, pady=10, sticky='w')
        self.income_bonus = self._entry(form, 'e.g. 800', 320)
        self.income_bonus.grid(row=1, column=1, padx=8, pady=10)
        self._btn(form, 'Save Income', self.save_income, width=180).grid(row=2, column=1, padx=8, pady=(14, 4), sticky='w')
        self.income_total = ctk.CTkLabel(page, text='', font=(FONT, 20, 'bold'), text_color=COLORS['good'])
        self.income_total.pack(anchor='w', pady=8)

    def save_income(self):
        try:
            salary = float(self.income_salary.get() or 0)
            bonus = float(self.income_bonus.get() or 0)
        except ValueError:
            return messagebox.showerror('Invalid', 'Salary and bonus must be numbers.')
        db.set_income(salary, bonus)
        self.refresh_income()
        messagebox.showinfo('Saved', 'Your income has been updated.')

    def refresh_income(self):
        salary, bonus = db.get_income()
        self.income_salary.delete(0, 'end')
        self.income_salary.insert(0, f'{salary:.0f}')
        self.income_bonus.delete(0, 'end')
        self.income_bonus.insert(0, f'{bonus:.0f}')
        self.income_total.configure(text=f'Estimated monthly income:  {db.get_monthly_income():,.2f}')

    def build_budget_page(self):
        page = self._new_page('budget')
        self._title(page, 'Budget', "Add categories and the most you'd like to spend on each.")
        card = self._card(page)
        card.pack(fill='x', pady=(0, 16))
        form = ctk.CTkFrame(card, fg_color='transparent')
        form.pack(padx=18, pady=18, anchor='w')
        self.b_cat = self._entry(form, 'Category (e.g. Food)')
        self.b_cat.grid(row=0, column=0, padx=6, pady=6)
        self.b_spend = self._entry(form, 'Max to spend', 220)
        self.b_spend.grid(row=0, column=1, padx=6, pady=6)
        self._btn(form, 'Add Category', self.save_budget, width=160).grid(row=0, column=2, padx=6, pady=6)
        self.budget_list = self._scroll(page, 'Your budget categories')
        self.budget_list.pack(fill='both', expand=True)

    def save_budget(self):
        cat = self.b_cat.get().strip().lower()
        try:
            sp = float(self.b_spend.get() or 0)
        except ValueError:
            return messagebox.showerror('Invalid', 'Amount must be a number.')
        if not cat:
            return messagebox.showerror('Missing', 'Enter a category name.')
        db.add_or_update_budget(cat, sp, 0)
        self.b_cat.delete(0, 'end')
        self.b_spend.delete(0, 'end')
        self.refresh_budget()
        self.refresh_spending()

    def refresh_budget(self):
        for w in self.budget_list.winfo_children():
            w.destroy()
        for r in db.get_all_budget():
            row = self._row(self.budget_list)
            ctk.CTkLabel(row, text=f'{r['category'].title()}    max spend: {r['planned_spend']:,.0f}', font=(FONT, 14), text_color=COLORS['text']).pack(side='left', padx=16, pady=10)
            self._btn(row, 'Delete', lambda c=r['category']: (db.delete_budget(c), self.refresh_budget(), self.refresh_spending()), COLORS['bad'], width=84).pack(side='right', padx=12, pady=8)

    def build_spending_page(self):
        page = self._new_page('spending')
        self._title(page, 'Spending', 'Actual spending vs your budget. Add cash spends or import from Bank.')
        card = self._card(page)
        card.pack(fill='x', pady=(0, 16))
        form = ctk.CTkFrame(card, fg_color='transparent')
        form.pack(padx=18, pady=18, anchor='w')
        self.s_cat = self._dropdown(form, ['(add categories)'], 200)
        self.s_cat.grid(row=0, column=0, padx=6, pady=6)
        self.s_amt = self._entry(form, 'Amount spent', 180)
        self.s_amt.grid(row=0, column=1, padx=6, pady=6)
        self.s_note = self._entry(form, 'Note (optional)', 170)
        self.s_note.grid(row=0, column=2, padx=6, pady=6)
        self._btn(form, 'Add Spending', self.save_spending, width=150).grid(row=0, column=3, padx=6, pady=6)
        self.spending_list = self._scroll(page, 'Spending by category')
        self.spending_list.pack(fill='both', expand=True)

    def save_spending(self):
        cat = self.s_cat.get()
        if cat == '(add categories)':
            return messagebox.showerror('No category', 'Add a budget category first.')
        try:
            amt = float(self.s_amt.get())
        except ValueError:
            return messagebox.showerror('Invalid', 'Amount must be a number.')
        db.add_transaction(cat, amt, 'cash', self.s_note.get().strip())
        self.s_amt.delete(0, 'end')
        self.s_note.delete(0, 'end')
        self.refresh_spending()

    def refresh_spending(self):
        cats = [r['category'] for r in db.get_all_budget()]
        if cats:
            self.s_cat.configure(values=cats)
            if self.s_cat.get() not in cats:
                self.s_cat.set(cats[0])
        else:
            self.s_cat.configure(values=['(add categories)'])
            self.s_cat.set('(add categories)')
        for w in self.spending_list.winfo_children():
            w.destroy()
        spent = db.get_spending_by_category()
        budget = {r['category']: r['planned_spend'] for r in db.get_all_budget()}
        ctk.CTkLabel(self.spending_list, text='By category', font=(FONT, 15, 'bold'), text_color=COLORS['text_soft']).pack(anchor='w', padx=4, pady=(2, 4))
        for cat in sorted(set(list(spent) + list(budget))):
            actual = spent.get(cat, 0)
            planned = budget.get(cat, 0)
            over = planned > 0 and actual > planned
            within = planned > 0 and actual <= planned
            row = self._row(self.spending_list)
            if over:
                status = 'OVER budget'
                color = COLORS['bad']
            elif within:
                status = 'within budget'
                color = COLORS['good']
            else:
                status = 'no budget set'
                color = COLORS['text_soft']
            ctk.CTkLabel(row, text=f'{cat.title()}:   spent {actual:,.0f} / budget {planned:,.0f}', font=(FONT, 14, 'bold'), text_color=color).pack(side='left', padx=16, pady=10)
            ctk.CTkLabel(row, text=status, font=(FONT, 13), text_color=color).pack(side='right', padx=16)
        ctk.CTkLabel(self.spending_list, text=f'Total spent:  {db.get_total_spending():,.2f}', font=(FONT, 16, 'bold'), text_color=COLORS['text']).pack(anchor='w', pady=(8, 4), padx=4)
        entries = db.get_all_transactions()
        if entries:
            ctk.CTkLabel(self.spending_list, text='Individual entries', font=(FONT, 15, 'bold'), text_color=COLORS['text_soft']).pack(anchor='w', padx=4, pady=(10, 4))
        for t in entries:
            row = self._row(self.spending_list)
            label = f'{t['category'].title()}:  {t['amount']:,.2f}'
            if t['note']:
                label += f'   ({t['note']})'
            src = 'bank' if t['source'] == 'bank' else 'cash'
            ctk.CTkLabel(row, text=label, font=(FONT, 14), text_color=COLORS['text']).pack(side='left', padx=16, pady=8)
            self._btn(row, 'Delete', lambda i=t['id']: self.delete_spending(i), COLORS['bad'], width=84).pack(side='right', padx=12, pady=6)
            ctk.CTkLabel(row, text=src, font=(FONT, 12), text_color=COLORS['text_soft']).pack(side='right', padx=4)

    def delete_spending(self, transaction_id):
        db.delete_transaction(transaction_id)
        self.refresh_spending()
        self.refresh_bank()

    def build_bank_page(self):
        page = self._new_page('bank')
        self._title(page, 'Bank Statement', 'Browse a PDF. We read each transaction and sort it into Spending automatically.')
        card = self._card(page)
        card.pack(fill='x', pady=(0, 16))
        inner = ctk.CTkFrame(card, fg_color='transparent')
        inner.pack(padx=24, pady=24, anchor='w')
        self._btn(inner, 'Browse PDF...', self.browse_pdf, width=180).pack(anchor='w')
        self.bank_status = ctk.CTkLabel(inner, text='No file selected yet.', font=(FONT, 14), text_color=COLORS['text_soft'])
        self.bank_status.pack(anchor='w', pady=(14, 0))
        self.bank_list = self._scroll(page, 'Transactions imported from your last statement')
        self.bank_list.pack(fill='both', expand=True)

    def browse_pdf(self):
        path = filedialog.askopenfilename(title='Choose a bank statement PDF', filetypes=[('PDF files', '*.pdf'), ('All files', '*.*')])
        if not path:
            return
        filename = path.replace('\\', '/').split('/')[-1]
        result = pdf_import.import_statement(path)
        txns = result['transactions']
        if not txns:
            self.bank_status.configure(text=f'Loaded {filename}, but found no spending transactions to import.')
            return
        self.bank_status.configure(text=f'Loaded {filename}. Categorizing {len(txns)} transactions...')
        self.update()
        descriptions = [t['description'] for t in txns]
        categories = ai.categorize_transactions(descriptions)
        existing = {r['category'] for r in db.get_all_budget()}
        for t, cat in zip(txns, categories):
            cat = cat or 'other'
            if cat not in existing:
                db.add_or_update_budget(cat, 0, 0)
                existing.add(cat)
            db.add_transaction(cat, t['amount'], 'bank', t['description'])
        self.bank_status.configure(text=f'Imported {len(txns)} transactions from {filename} into Spending.')
        self.refresh_bank()
        self.refresh_spending()

    def refresh_bank(self):
        for w in self.bank_list.winfo_children():
            w.destroy()
        bank_txns = [t for t in db.get_all_transactions() if t['source'] == 'bank']
        if not bank_txns:
            ctk.CTkLabel(self.bank_list, text='Nothing imported yet. Browse a PDF above.', font=(FONT, 14), text_color=COLORS['text_soft']).pack(anchor='w', padx=4, pady=8)
            return
        for t in bank_txns[:50]:
            row = self._row(self.bank_list)
            ctk.CTkLabel(row, text=f'{t['note']}', font=(FONT, 14), text_color=COLORS['text']).pack(side='left', padx=16, pady=10)
            self._btn(row, 'Delete', lambda i=t['id']: self.delete_bank_txn(i), COLORS['bad'], width=84).pack(side='right', padx=12, pady=6)
            ctk.CTkLabel(row, text=f'{t['amount']:,.2f}  ->  {t['category'].title()}', font=(FONT, 13, 'bold'), text_color=COLORS['accent']).pack(side='right', padx=10)

    def delete_bank_txn(self, transaction_id):
        db.delete_transaction(transaction_id)
        self.refresh_bank()
        self.refresh_spending()

    def build_smart_page(self):
        page = self._new_page('smart')
        self._title(page, 'Smart Buying', 'Fill the cost, then EITHER a monthly payment OR a timeframe.')
        card = self._card(page)
        card.pack(fill='x', pady=(0, 10))
        form = ctk.CTkFrame(card, fg_color='transparent')
        form.pack(padx=18, pady=14, anchor='w')

        def small_entry(ph):
            return ctk.CTkEntry(form, placeholder_text=ph, width=190, height=38, corner_radius=10, font=(FONT, 14), fg_color=COLORS['card'], border_color=COLORS['card_border'], text_color=COLORS['text'])
        self.buy_item = small_entry('e.g. Laptop')
        self.buy_cost = small_entry('e.g. 1200')
        self.buy_pay = small_entry('blank if using months')
        self.buy_months = small_entry('blank if using monthly')
        fields = [('Item', self.buy_item, 0, 0), ('Cost', self.buy_cost, 0, 2), ('Monthly payment', self.buy_pay, 1, 0), ('Months', self.buy_months, 1, 2)]
        for lab, ent, r, c in fields:
            ctk.CTkLabel(form, text=lab, font=(FONT, 13), text_color=COLORS['text']).grid(row=r, column=c, padx=(8, 4), pady=6, sticky='w')
            ent.grid(row=r, column=c + 1, padx=(0, 14), pady=6)
        self._btn(form, 'Make Plan', self.calc_purchase, width=150).grid(row=0, column=4, rowspan=2, padx=10, pady=6)
        ctk.CTkLabel(card, text="Enter only one of Monthly payment or Months. If both are given and disagree, we'll say so.", font=(FONT, 11), text_color=COLORS['text_soft']).pack(anchor='w', padx=20, pady=(0, 10))
        self.buy_summary = ctk.CTkLabel(page, text='', font=(FONT, 15, 'bold'), text_color=COLORS['text'], justify='left', wraplength=820)
        self.buy_summary.pack(anchor='w', pady=(0, 6))
        self.buy_table = self._scroll(page, 'Month-by-month plan')
        self.buy_table.pack(fill='both', expand=True)

    def calc_purchase(self):
        item = self.buy_item.get().strip() or 'this item'
        try:
            cost = float(self.buy_cost.get())
        except ValueError:
            return messagebox.showerror('Invalid', 'Enter a numeric cost.')
        pay = self.buy_pay.get().strip()
        months = self.buy_months.get().strip()
        try:
            pay_val = float(pay) if pay else None
            months_val = float(months) if months else None
        except ValueError:
            return messagebox.showerror('Invalid', 'Monthly payment and months must be numbers.')
        result = fl.purchase_plan(cost, pay_val, months_val)
        for w in self.buy_table.winfo_children():
            w.destroy()
        if 'error' in result:
            self.buy_summary.configure(text=result['error'], text_color=COLORS['bad'])
            return
        self.buy_summary.configure(text=f'To buy {item} ({cost:,.0f}):  pay {result['monthly_amount']:,.2f}/month for {result['months']} months.', text_color=COLORS['text'])
        head = self._row(self.buy_table)
        for txt in ['Month', 'Payment', 'Paid so far', 'Remaining']:
            ctk.CTkLabel(head, text=txt, font=(FONT, 13, 'bold'), width=150, text_color=COLORS['text']).pack(side='left', padx=4, pady=8)
        for m in result['schedule']:
            row = self._row(self.buy_table)
            vals = [str(m['month']), f'{m['payment']:,.0f}', f'{m['paid_so_far']:,.0f}', f'{m['remaining']:,.0f}']
            for v in vals:
                ctk.CTkLabel(row, text=v, font=(FONT, 13), width=150, text_color=COLORS['text']).pack(side='left', padx=4, pady=6)
    GROW_QUESTIONS = {'income': ['What company do you currently work at?', 'What is your job position or title?', 'What is your highest education / qualification?', 'Which certifications (if any) have you already done?', 'How many years of work experience do you have?', 'What are your strongest skills right now?', 'How would you rate your communication / speaking skills (and want to improve)?', 'What field or role would you love to grow into?', 'Which city do you currently live in?', 'Which cities or countries would you happily relocate to for a better job?', 'Roughly what do you earn now, and what would you like to earn?'], 'spending': ['How many people are in your family / household?', 'Which city or area do you live in?', 'How many bedrooms is your home, and do you rent or own?', 'Where do you usually buy your groceries and food from?', 'How often do you eat out or order food delivery?', 'What subscriptions or memberships do you pay for each month?', 'How do you usually travel (car, public transport, ride apps)?', 'What do you spend on for fun or extra activities?', 'Would you consider moving somewhere cheaper? If so, where?', 'What is your biggest money worry right now?', 'Which shopping or coupon apps do you already use, if any?']}

    def build_grow_page(self):
        page = self._new_page('grow')
        self._title(page, 'Grow & Save', 'Two coaches: one to grow your income, one to cut your spending.')
        self.grow_mode = None
        self.grow_index = 0
        self.grow_answers = {}
        self.grow_home = ctk.CTkFrame(page, fg_color='transparent')
        choices = ctk.CTkFrame(self.grow_home, fg_color='transparent')
        choices.pack(fill='x')
        for i in range(2):
            choices.grid_columnconfigure(i, weight=1, uniform='grow')
        c1 = self._card(choices)
        c1.grid(row=0, column=0, padx=10, sticky='nsew')
        ctk.CTkLabel(c1, text='Increase Income', font=(FONT, 20, 'bold'), text_color=COLORS['text']).pack(anchor='w', padx=22, pady=(22, 4))
        ctk.CTkLabel(c1, text="Answer a short survey about your work and we'll suggest\ncertifications, skills, companies, and places to grow your income.", font=(FONT, 13), text_color=COLORS['text_soft'], justify='left').pack(anchor='w', padx=22)
        self._btn(c1, 'Start', lambda: self.start_grow_survey('income'), width=140).pack(anchor='w', padx=22, pady=20)
        c2 = self._card(choices)
        c2.grid(row=0, column=1, padx=10, sticky='nsew')
        ctk.CTkLabel(c2, text='Reduce Spending', font=(FONT, 20, 'bold'), text_color=COLORS['text']).pack(anchor='w', padx=22, pady=(22, 4))
        ctk.CTkLabel(c2, text="Answer a short survey about how you live and spend, and\nwe'll find cheaper options, cuts, and apps that save you money.", font=(FONT, 13), text_color=COLORS['text_soft'], justify='left').pack(anchor='w', padx=22)
        self._btn(c2, 'Start', lambda: self.start_grow_survey('spending'), width=140).pack(anchor='w', padx=22, pady=20)
        self.grow_survey = ctk.CTkFrame(page, fg_color='transparent')
        qcard = self._card(self.grow_survey)
        qcard.pack(fill='x', pady=(0, 14))
        self.grow_progress = ctk.CTkLabel(qcard, text='', font=(FONT, 15), text_color=COLORS['text_soft'])
        self.grow_progress.pack(anchor='w', padx=28, pady=(24, 8))
        self.grow_question = ctk.CTkLabel(qcard, text='', font=(FONT, 23, 'bold'), text_color=COLORS['text'], justify='left', wraplength=820)
        self.grow_question.pack(anchor='w', padx=28, pady=(0, 18))
        self.grow_answer = ctk.CTkEntry(qcard, placeholder_text='Type your answer here...', width=820, height=60, corner_radius=INPUT_RADIUS, font=(FONT, 17), fg_color=COLORS['card'], border_color=COLORS['card_border'], text_color=COLORS['text'])
        self.grow_answer.pack(anchor='w', padx=28, pady=(0, 28))
        self.grow_answer.bind('<Return>', lambda e: self.grow_next())
        nav = ctk.CTkFrame(self.grow_survey, fg_color='transparent')
        nav.pack(fill='x')
        self._btn(nav, 'Back', self.grow_prev, COLORS['text_soft'], width=110).pack(side='left')
        self.grow_next_btn = self._btn(nav, 'Next', self.grow_next, width=140)
        self.grow_next_btn.pack(side='left', padx=10)
        self._btn(nav, 'Quit survey', self.grow_quit, COLORS['bad'], width=120).pack(side='right')
        self.grow_result_box = ctk.CTkFrame(page, fg_color='transparent')
        self.grow_result = ctk.CTkScrollableFrame(self.grow_result_box, fg_color=COLORS['bg'], label_text='Your personalised plan', label_text_color=COLORS['text_soft'], label_fg_color=COLORS['bg'])
        self.grow_result.pack(fill='both', expand=True)
        self.grow_result_label = ctk.CTkLabel(self.grow_result, text='', font=(FONT, 14), text_color=COLORS['text'], justify='left', wraplength=820)
        self.grow_result_label.pack(anchor='w', padx=6, pady=6)
        self._btn(self.grow_result_box, 'Done', self.grow_quit, width=120).pack(anchor='w', pady=10)
        self._show_grow_screen('home')

    def _show_grow_screen(self, which):
        for f in (self.grow_home, self.grow_survey, self.grow_result_box):
            f.pack_forget()
        if which == 'home':
            self.grow_home.pack(fill='x', pady=(4, 0))
        elif which == 'survey':
            self.grow_survey.pack(fill='both', expand=True, pady=(4, 0))
        else:
            self.grow_result_box.pack(fill='both', expand=True, pady=(4, 0))

    def start_grow_survey(self, mode):
        self.grow_mode = mode
        self.grow_index = 0
        self.grow_answers = {}
        self.grow_result_label.configure(text='')
        self._show_grow_screen('survey')
        self._render_grow_question()

    def _render_grow_question(self):
        questions = self.GROW_QUESTIONS[self.grow_mode]
        total = len(questions)
        q = questions[self.grow_index]
        self.grow_progress.configure(text=f'Question {self.grow_index + 1} of {total}')
        self.grow_question.configure(text=q)
        self.grow_answer.delete(0, 'end')
        if q in self.grow_answers:
            self.grow_answer.insert(0, self.grow_answers[q])
        self.grow_answer.focus()
        last = self.grow_index == total - 1
        self.grow_next_btn.configure(text='Get Advice' if last else 'Next')

    def grow_next(self):
        questions = self.GROW_QUESTIONS[self.grow_mode]
        q = questions[self.grow_index]
        self.grow_answers[q] = self.grow_answer.get().strip()
        if self.grow_index < len(questions) - 1:
            self.grow_index += 1
            self._render_grow_question()
        else:
            self.finish_grow_survey()

    def grow_prev(self):
        questions = self.GROW_QUESTIONS[self.grow_mode]
        q = questions[self.grow_index]
        self.grow_answers[q] = self.grow_answer.get().strip()
        if self.grow_index > 0:
            self.grow_index -= 1
            self._render_grow_question()
        else:
            self._show_grow_screen('home')

    def grow_quit(self):
        self._show_grow_screen('home')

    def finish_grow_survey(self):
        self._show_grow_screen('result')
        self.grow_result_label.configure(text='Analysing your answers with the AI coach...')
        self.update()
        if self.grow_mode == 'income':
            advice = ai.increase_income_advice(self.grow_answers)
        else:
            advice = ai.reduce_spending_advice(self.grow_answers, db.get_spending_by_category())
        self.grow_result_label.configure(text=advice)
        self.update()
        try:
            self.grow_result._parent_canvas.yview_moveto(0.0)
        except Exception:
            pass

    def build_investments_page(self):
        page = self._new_page('investments')
        self._title(page, 'Investments', 'Name an investment and its profit or loss this month.')
        card = self._card(page)
        card.pack(fill='x', pady=(0, 16))
        form = ctk.CTkFrame(card, fg_color='transparent')
        form.pack(padx=18, pady=18, anchor='w')
        self.i_name = self._entry(form, 'Investment name', 280)
        self.i_name.grid(row=0, column=0, padx=6, pady=6)
        self.i_change = self._entry(form, 'Profit (+) or loss (-)', 260)
        self.i_change.grid(row=0, column=1, padx=6, pady=6)
        self._btn(form, 'Add', self.save_investment, width=120).grid(row=0, column=2, padx=6, pady=6)
        self.inv_total = ctk.CTkLabel(page, text='', font=(FONT, 16, 'bold'), text_color=COLORS['text'])
        self.inv_total.pack(anchor='w', pady=(0, 8))
        self.inv_list = self._scroll(page, 'Your investments')
        self.inv_list.pack(fill='both', expand=True)

    def save_investment(self):
        name = self.i_name.get().strip()
        try:
            ch = float(self.i_change.get() or 0)
        except ValueError:
            return messagebox.showerror('Invalid', 'Profit/loss must be a number.')
        if not name:
            return messagebox.showerror('Missing', 'Enter an investment name.')
        db.add_investment(name, '', 0, ch)
        self.i_name.delete(0, 'end')
        self.i_change.delete(0, 'end')
        self.refresh_investments()

    def refresh_investments(self):
        for w in self.inv_list.winfo_children():
            w.destroy()
        for r in db.get_all_investments():
            ch = r['monthly_change']
            row = self._row(self.inv_list)
            ctk.CTkLabel(row, text=f'{r['name']}', font=(FONT, 14), text_color=COLORS['text']).pack(side='left', padx=16, pady=10)
            ctk.CTkLabel(row, text=f'{ch:+,.0f} this month', font=(FONT, 14, 'bold'), text_color=COLORS['good'] if ch >= 0 else COLORS['bad']).pack(side='right', padx=60)
            self._btn(row, 'Delete', lambda i=r['id']: (db.delete_investment(i), self.refresh_investments()), COLORS['bad'], width=84).pack(side='right', padx=12, pady=8)
        change = db.get_total_investment_change()
        self.inv_total.configure(text=f'Total profit/loss this month:  {change:+,.0f}', text_color=COLORS['good'] if change >= 0 else COLORS['bad'])

    def build_emergency_page(self):
        page = self._new_page('emergency')
        self._title(page, 'Emergency Fund', 'How long could you last if income stopped?')
        self._btn(page, 'Calculate', self.calc_emergency, width=160).pack(anchor='w', pady=(0, 14))
        card = self._card(page)
        card.pack(fill='x', pady=(0, 12))
        self.emerg_display = ctk.CTkLabel(card, text='Press Calculate to run the numbers.', font=(FONT, 15), text_color=COLORS['text'], justify='left')
        self.emerg_display.pack(anchor='w', padx=24, pady=22)
        aicard = self._card(page)
        aicard.pack(fill='x')
        self.emerg_ai = ctk.CTkLabel(aicard, text='AI advice will appear here.', wraplength=760, font=(FONT, 14), text_color=COLORS['accent'], justify='left')
        self.emerg_ai.pack(anchor='w', padx=24, pady=18)

    def calc_emergency(self):
        monthly_expense = db.get_total_spending()
        total_savings = db.get_savings() + db.get_total_invested()
        e = fl.emergency_fund(monthly_expense, total_savings)
        self.emerg_display.configure(text=f'Monthly expenses:  {monthly_expense:,.0f}\nTotal savings:  {total_savings:,.0f}\nRecommended fund (6 months):  {e['recommended_fund']:,.0f}\nShortfall:  {e['shortfall']:,.0f}\nYou could survive about {e['months_survivable']} months with no income.')
        self.emerg_ai.configure(text='Asking AI for advice...')
        self.update()
        self.emerg_ai.configure(text=ai.get_emergency_feedback(e['months_survivable'], e['shortfall']))

    def build_report_page(self):
        page = self._new_page('report')
        self._title(page, 'Monthly Report', 'Your score and a picture of the month.')
        self._btn(page, 'Generate report', self.generate_report, width=180).pack(anchor='w', pady=(0, 12))
        self.report_score = ctk.CTkLabel(page, text='', font=(FONT, 24, 'bold'), text_color=COLORS['text'])
        self.report_score.pack(anchor='w')
        self.report_ai = ctk.CTkLabel(page, text='', wraplength=820, font=(FONT, 14), text_color=COLORS['accent'], justify='left')
        self.report_ai.pack(anchor='w', pady=(4, 10))
        self.chart_frame = self._card(page)
        self.chart_frame.pack(fill='both', expand=True)

    def generate_report(self):
        for w in self.chart_frame.winfo_children():
            w.destroy()
        income = db.get_monthly_income()
        spent = db.get_total_spending()
        surplus = db.get_monthly_surplus()
        planned_save = db.get_total_planned_save()
        score = fl.savings_score(planned_save, surplus)
        self.report_score.configure(text=f'Savings score:  {score}/100')
        self.report_ai.configure(text='Asking AI for feedback...')
        self.update()
        self.report_ai.configure(text=ai.get_budget_feedback(income, spent, surplus, score))
        fig = Figure(figsize=(8.5, 3.6), dpi=100)
        fig.patch.set_facecolor(COLORS['card'])
        ax1 = fig.add_subplot(121)
        spending = db.get_spending_by_category()
        if spending:
            ax1.pie(list(spending.values()), labels=[c.title() for c in spending], autopct='%1.0f%%')
            ax1.set_title('Spending by category')
        else:
            ax1.text(0.5, 0.5, 'No spending yet', ha='center')
            ax1.axis('off')
        ax2 = fig.add_subplot(122)
        ax2.bar(['Income', 'Spent', 'Surplus'], [income, spent, surplus], color=[COLORS['good'], COLORS['bad'], COLORS['accent']])
        ax2.set_title('This month')
        for ax in (ax1, ax2):
            ax.set_facecolor(COLORS['card'])
        fig.tight_layout()
        canvas = FigureCanvasTkAgg(fig, master=self.chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill='both', expand=True, padx=12, pady=12)

    def build_assistant_page(self):
        page = self._new_page('assistant')
        self._title(page, 'AI Assistant', 'Ask anything about your finances.')
        self.chat_display = ctk.CTkTextbox(page, fg_color=COLORS['card'], text_color=COLORS['text'], border_color=COLORS['card_border'], border_width=1, corner_radius=14, wrap='word', font=(FONT, 14))
        self.chat_display.pack(fill='both', expand=True, pady=(0, 12))
        self.chat_display.insert('end', 'Assistant: Hi! Ask me anything about your finances.\n\n')
        self.chat_display.configure(state='disabled')
        row = ctk.CTkFrame(page, fg_color='transparent')
        row.pack(fill='x')
        self.chat_entry = self._entry(row, 'Type your question...', 600)
        self.chat_entry.pack(side='left', fill='x', expand=True, padx=(0, 8))
        self.chat_entry.bind('<Return>', lambda e: self.send_chat())
        self._btn(row, 'Send', self.send_chat).pack(side='right')

    def send_chat(self):
        msg = self.chat_entry.get().strip()
        if not msg:
            return
        self.chat_entry.delete(0, 'end')
        self.chat_display.configure(state='normal')
        self.chat_display.insert('end', f'You: {msg}\n')
        context = db.get_full_context()
        self.chat_display.insert('end', 'Assistant: ...\n')
        self.chat_display.configure(state='disabled')
        self.update()
        reply = ai.chat(msg, context)
        self.chat_display.configure(state='normal')
        self.chat_display.insert('end', f'Assistant: {reply}\n\n')
        self.chat_display.configure(state='disabled')
        self.chat_display.see('end')
if __name__ == '__main__':
    app = FinanceApp()
    app.mainloop()