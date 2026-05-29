

import customtkinter as ctk
from tkinter import messagebox
import json
import os
import urllib.request
import urllib.error
from datetime import datetime

# ---------- App Configuration ----------
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

DATA_FILE = "paisapilot_data.json"

# ---------- Data Handling ----------
def load_data():
    default = {
        "profile_type": None,
        "income": 0,
        "income_updated": "",
        "business_history": [],
        "bonuses": [],
        "fixed_expenses": [],
        "variable_expenses": [],
        "budgets": {},
        "investments": [],
        "gemini_api_key": "",
        "chat_history": []
    }
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            saved = json.load(f)
        # Add any missing keys from old data files
        for key, value in default.items():
            if key not in saved:
                saved[key] = value
        return saved
    return default

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

# ---------- Stability Score ----------
def calculate_stability_score(data):
    score = 0
    income = data["income"]
    fixed_total = sum(item["amount"] for item in data["fixed_expenses"])
    variable_total = sum(item["amount"] for item in data["variable_expenses"])
    total_spent = fixed_total + variable_total
    bonus_total = sum(b["amount"] for b in data["bonuses"])
    effective_income = income + bonus_total

    if effective_income <= 0:
        return 0, "No income data"

    # 1. Income vs Expenses (40 pts)
    if total_spent <= effective_income * 0.5:
        score += 40
    elif total_spent <= effective_income * 0.7:
        score += 30
    elif total_spent <= effective_income * 0.9:
        score += 20
    elif total_spent <= effective_income:
        score += 10

    # 2. Budget Discipline (20 pts)
    if data["budgets"]:
        spent_by_cat = {}
        for item in data["variable_expenses"]:
            cat = item["category"]
            spent_by_cat[cat] = spent_by_cat.get(cat, 0) + item["amount"]
        within = 0
        total_cats = 0
        for cat, budget in data["budgets"].items():
            total_cats += 1
            if spent_by_cat.get(cat, 0) <= budget:
                within += 1
        if total_cats > 0:
            score += int((within / total_cats) * 20)

    # 3. Investments (20 pts)
    if data["investments"]:
        inv_count = len(data["investments"])
        if inv_count >= 3:
            score += 20
        elif inv_count == 2:
            score += 14
        elif inv_count == 1:
            score += 8

    # 4. Fixed expense ratio (20 pts)
    if effective_income > 0:
        ratio = fixed_total / effective_income
        if ratio <= 0.3:
            score += 20
        elif ratio <= 0.5:
            score += 14
        elif ratio <= 0.7:
            score += 8

    if score >= 80:
        verdict = "Excellent"
    elif score >= 60:
        verdict = "Good"
    elif score >= 40:
        verdict = "Fair"
    elif score >= 20:
        verdict = "Needs Attention"
    else:
        verdict = "Critical"

    return score, verdict

# ---------- Gemini API ----------
def call_gemini(api_key, message, context=""):
    if not api_key:
        return "Please add your Gemini API key first."

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
    full_prompt = f"You are a helpful family finance assistant in the PaisaPilot app. {context}\n\nUser question: {message}"

    payload = {"contents": [{"parts": [{"text": full_prompt}]}]}

    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return result["candidates"][0]["content"]["parts"][0]["text"]
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="ignore")
        return f"API Error ({e.code}): Check your API key.\n{err_body[:200]}"
    except Exception as e:
        return f"Error: {str(e)}"


# ---------- Main App Class ----------
class PaisaPilotApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("PaisaPilot - Family Finance Manager")
        self.geometry("1150x700")
        self.configure(fg_color="white")
        self.resizable(True, True)

        self.data = load_data()

        if not self.data["profile_type"]:
            self.show_profile_screen()
        else:
            self.build_main_ui()

    # ---------- Profile Screen ----------
    def show_profile_screen(self):
        for widget in self.winfo_children():
            widget.destroy()

        frame = ctk.CTkFrame(self, fg_color="white")
        frame.pack(expand=True, fill="both")

        ctk.CTkLabel(frame, text="Welcome to PaisaPilot",
                     font=("Arial", 32, "bold"), text_color="#1a1a1a").pack(pady=(120, 10))
        ctk.CTkLabel(frame, text="Select your profile type to get started",
                     font=("Arial", 16), text_color="#555555").pack(pady=(0, 50))

        btn_frame = ctk.CTkFrame(frame, fg_color="white")
        btn_frame.pack()

        ctk.CTkButton(btn_frame, text="Job Profile", width=200, height=60,
                      font=("Arial", 16, "bold"),
                      fg_color="#2563eb", hover_color="#1d4ed8",
                      command=lambda: self.set_profile("Job")).grid(row=0, column=0, padx=20)

        ctk.CTkButton(btn_frame, text="Business Profile", width=200, height=60,
                      font=("Arial", 16, "bold"),
                      fg_color="#059669", hover_color="#047857",
                      command=lambda: self.set_profile("Business")).grid(row=0, column=1, padx=20)

    def set_profile(self, profile_type):
        self.data["profile_type"] = profile_type
        save_data(self.data)
        self.build_main_ui()

    # ---------- Main UI ----------
    def build_main_ui(self):
        for widget in self.winfo_children():
            widget.destroy()

        top_bar = ctk.CTkFrame(self, fg_color="white", height=60, corner_radius=0)
        top_bar.pack(side="top", fill="x")
        top_bar.pack_propagate(False)

        ctk.CTkLabel(top_bar, text="PaisaPilot",
                     font=("Arial", 22, "bold"), text_color="#2563eb").pack(side="left", padx=20)
        ctk.CTkLabel(top_bar, text=f"Profile: {self.data['profile_type']}",
                     font=("Arial", 14), text_color="#666666").pack(side="right", padx=20)

        sep = ctk.CTkFrame(self, height=1, fg_color="#e5e5e5")
        sep.pack(fill="x")

        main = ctk.CTkFrame(self, fg_color="white")
        main.pack(expand=True, fill="both")

        # Sidebar
        self.sidebar = ctk.CTkFrame(main, fg_color="#f5f5f5", width=230, corner_radius=0)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        self.tabs = [
            "Dashboard",
            "Income",
            "Fixed Spending",
            "Variable Spending",
            "Budget",
            "Report",
            "Investment Portfolio",
            "AI Assistant"
        ]
        self.tab_buttons = {}

        ctk.CTkLabel(self.sidebar, text="Menu",
                     font=("Arial", 14, "bold"), text_color="#333333").pack(pady=(20, 10))

        for tab in self.tabs:
            btn = ctk.CTkButton(self.sidebar, text=tab, width=210, height=38,
                                font=("Arial", 13), anchor="w",
                                fg_color="transparent", text_color="#333333",
                                hover_color="#e5e5e5",
                                command=lambda t=tab: self.show_tab(t))
            btn.pack(pady=3, padx=10)
            self.tab_buttons[tab] = btn

        ctk.CTkButton(self.sidebar, text="Switch Profile", width=210, height=35,
                      font=("Arial", 12),
                      fg_color="#dc2626", hover_color="#b91c1c",
                      command=self.switch_profile).pack(side="bottom", pady=20, padx=10)

        self.content = ctk.CTkFrame(main, fg_color="white")
        self.content.pack(side="left", expand=True, fill="both", padx=20, pady=20)

        self.show_tab("Dashboard")

    def switch_profile(self):
        if messagebox.askyesno("Switch Profile", "Switch profile? Your data remains saved."):
            self.data["profile_type"] = None
            save_data(self.data)
            self.show_profile_screen()

    # ---------- Tab Routing ----------
    def show_tab(self, tab_name):
        for name, btn in self.tab_buttons.items():
            if name == tab_name:
                btn.configure(fg_color="#2563eb", text_color="white")
            else:
                btn.configure(fg_color="transparent", text_color="#333333")

        for widget in self.content.winfo_children():
            widget.destroy()

        if tab_name == "Dashboard":
            self.build_dashboard()
        elif tab_name == "Income":
            self.build_income_tab()
        elif tab_name == "Fixed Spending":
            self.build_fixed_tab()
        elif tab_name == "Variable Spending":
            self.build_variable_tab()
        elif tab_name == "Budget":
            self.build_budget_tab()
        elif tab_name == "Report":
            self.build_report_tab()
        elif tab_name == "Investment Portfolio":
            self.build_investment_tab()
        elif tab_name == "AI Assistant":
            self.build_ai_tab()

    # ---------- Dashboard ----------
    def build_dashboard(self):
        scroll = ctk.CTkScrollableFrame(self.content, fg_color="white")
        scroll.pack(fill="both", expand=True)

        ctk.CTkLabel(scroll, text="Dashboard",
                     font=("Arial", 26, "bold"), text_color="#1a1a1a").pack(anchor="w", pady=(0, 20))

        bonus_total = sum(b["amount"] for b in self.data["bonuses"])
        income = self.data["income"] + bonus_total
        fixed_total = sum(item["amount"] for item in self.data["fixed_expenses"])
        variable_total = sum(item["amount"] for item in self.data["variable_expenses"])
        total_spent = fixed_total + variable_total
        remaining = income - total_spent

        cards_frame = ctk.CTkFrame(scroll, fg_color="white")
        cards_frame.pack(fill="x", pady=10)

        self.make_card(cards_frame, "Income (incl. bonus)", f"Rs. {income:,.0f}", "#2563eb", 0)
        self.make_card(cards_frame, "Total Spent", f"Rs. {total_spent:,.0f}", "#dc2626", 1)
        self.make_card(cards_frame, "Remaining", f"Rs. {remaining:,.0f}",
                       "#059669" if remaining >= 0 else "#dc2626", 2)

        # Stability Score
        score, verdict = calculate_stability_score(self.data)

        score_frame = ctk.CTkFrame(scroll, fg_color="#f9f9f9", corner_radius=10)
        score_frame.pack(fill="x", pady=15, padx=5)

        ctk.CTkLabel(score_frame, text="Financial Stability Score",
                     font=("Arial", 16, "bold"), text_color="#1a1a1a").pack(anchor="w", padx=20, pady=(15, 5))

        score_inner = ctk.CTkFrame(score_frame, fg_color="#f9f9f9")
        score_inner.pack(fill="x", padx=20, pady=(0, 10))

        if score >= 80:
            score_color = "#059669"
        elif score >= 60:
            score_color = "#2563eb"
        elif score >= 40:
            score_color = "#d97706"
        else:
            score_color = "#dc2626"

        ctk.CTkLabel(score_inner, text=f"{score}/100",
                     font=("Arial", 36, "bold"), text_color=score_color).pack(side="left", padx=(0, 20))

        verdict_box = ctk.CTkFrame(score_inner, fg_color="#f9f9f9")
        verdict_box.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(verdict_box, text=verdict,
                     font=("Arial", 18, "bold"), text_color=score_color).pack(anchor="w")
        ctk.CTkLabel(verdict_box,
                     text="Based on income, expenses, budget discipline, and investments",
                     font=("Arial", 11), text_color="#666666").pack(anchor="w")

        progress = ctk.CTkProgressBar(score_frame, height=14, progress_color=score_color)
        progress.pack(fill="x", padx=20, pady=(0, 15))
        progress.set(score / 100)

        # Spending Breakdown
        breakdown_frame = ctk.CTkFrame(scroll, fg_color="#f9f9f9", corner_radius=10)
        breakdown_frame.pack(fill="x", pady=10, padx=5)

        ctk.CTkLabel(breakdown_frame, text="Spending Breakdown",
                     font=("Arial", 16, "bold"), text_color="#1a1a1a").pack(anchor="w", padx=20, pady=(15, 10))
        ctk.CTkLabel(breakdown_frame, text=f"Fixed Spending: Rs. {fixed_total:,.0f}",
                     font=("Arial", 13), text_color="#333333").pack(anchor="w", padx=20)
        ctk.CTkLabel(breakdown_frame, text=f"Variable Spending: Rs. {variable_total:,.0f}",
                     font=("Arial", 13), text_color="#333333").pack(anchor="w", padx=20)
        ctk.CTkLabel(breakdown_frame, text=f"Bonus Income: Rs. {bonus_total:,.0f}",
                     font=("Arial", 13), text_color="#059669").pack(anchor="w", padx=20, pady=(0, 15))

        # Recent Transactions
        recent_frame = ctk.CTkFrame(scroll, fg_color="#f9f9f9", corner_radius=10)
        recent_frame.pack(fill="both", expand=True, pady=10, padx=5)

        ctk.CTkLabel(recent_frame, text="Recent Transactions",
                     font=("Arial", 16, "bold"), text_color="#1a1a1a").pack(anchor="w", padx=20, pady=(15, 10))

        all_txns = []
        for item in self.data["fixed_expenses"]:
            all_txns.append({"type": "Fixed", **item})
        for item in self.data["variable_expenses"]:
            all_txns.append({"type": "Variable", **item})
        all_txns.sort(key=lambda x: x.get("date", ""), reverse=True)
        recent = all_txns[:6]

        if not recent:
            ctk.CTkLabel(recent_frame, text="No transactions yet.",
                         font=("Arial", 12), text_color="#888888").pack(padx=20, pady=20)
        else:
            for txn in recent:
                row = ctk.CTkFrame(recent_frame, fg_color="white", corner_radius=6)
                row.pack(fill="x", padx=15, pady=4)
                ctk.CTkLabel(row, text=f"{txn['name']}",
                             font=("Arial", 13, "bold"), text_color="#1a1a1a").pack(side="left", padx=15, pady=8)
                ctk.CTkLabel(row, text=f"[{txn['type']}] {txn.get('date', '')}",
                             font=("Arial", 11), text_color="#888888").pack(side="left", padx=10)
                ctk.CTkLabel(row, text=f"Rs. {txn['amount']:,.0f}",
                             font=("Arial", 13, "bold"), text_color="#dc2626").pack(side="right", padx=15)
            ctk.CTkLabel(recent_frame, text="", fg_color="#f9f9f9").pack(pady=5)

    def make_card(self, parent, title, value, color, col):
        card = ctk.CTkFrame(parent, fg_color="white", corner_radius=10,
                            border_width=1, border_color="#e5e5e5", width=300, height=110)
        card.grid(row=0, column=col, padx=10, pady=5, sticky="nsew")
        card.grid_propagate(False)
        parent.grid_columnconfigure(col, weight=1)

        ctk.CTkLabel(card, text=title,
                     font=("Arial", 13), text_color="#666666").pack(anchor="w", padx=20, pady=(20, 5))
        ctk.CTkLabel(card, text=value,
                     font=("Arial", 22, "bold"), text_color=color).pack(anchor="w", padx=20)

    # ---------- Income Tab ----------
    def build_income_tab(self):
        scroll = ctk.CTkScrollableFrame(self.content, fg_color="white")
        scroll.pack(fill="both", expand=True)

        ctk.CTkLabel(scroll, text="Income",
                     font=("Arial", 26, "bold"), text_color="#1a1a1a").pack(anchor="w", pady=(0, 20))

        profile = self.data["profile_type"]

        info_frame = ctk.CTkFrame(scroll, fg_color="#f9f9f9", corner_radius=10)
        info_frame.pack(fill="x", pady=10, padx=5)

        if profile == "Job":
            ctk.CTkLabel(info_frame, text="Monthly Salary",
                         font=("Arial", 16, "bold"), text_color="#1a1a1a").pack(anchor="w", padx=20, pady=(15, 5))
            ctk.CTkLabel(info_frame, text="Update only when your salary changes (hike, switch, etc.)",
                         font=("Arial", 12), text_color="#666666").pack(anchor="w", padx=20, pady=(0, 10))
            ctk.CTkLabel(info_frame, text=f"Current Salary: Rs. {self.data['income']:,.0f}",
                         font=("Arial", 14), text_color="#2563eb").pack(anchor="w", padx=20)
            ctk.CTkLabel(info_frame, text=f"Last Updated: {self.data['income_updated'] or 'Never'}",
                         font=("Arial", 11), text_color="#888888").pack(anchor="w", padx=20, pady=(0, 15))
        else:
            ctk.CTkLabel(info_frame, text="Monthly Business Profit",
                         font=("Arial", 16, "bold"), text_color="#1a1a1a").pack(anchor="w", padx=20, pady=(15, 5))
            ctk.CTkLabel(info_frame, text="Enter your profit for the current month",
                         font=("Arial", 12), text_color="#666666").pack(anchor="w", padx=20, pady=(0, 10))
            ctk.CTkLabel(info_frame, text=f"Current Month Profit: Rs. {self.data['income']:,.0f}",
                         font=("Arial", 14), text_color="#059669").pack(anchor="w", padx=20, pady=(0, 15))

        input_frame = ctk.CTkFrame(scroll, fg_color="white")
        input_frame.pack(fill="x", pady=15, padx=5)

        ctk.CTkLabel(input_frame, text="Enter Amount (Rs.):",
                     font=("Arial", 13), text_color="#333333").pack(anchor="w")
        amount_entry = ctk.CTkEntry(input_frame, width=300, height=38,
                                    font=("Arial", 13), placeholder_text="e.g. 50000")
        amount_entry.pack(anchor="w", pady=8)

        def save_income():
            try:
                amount = float(amount_entry.get())
                self.data["income"] = amount
                self.data["income_updated"] = datetime.now().strftime("%d %b %Y")
                if profile == "Business":
                    self.data["business_history"].append({
                        "month": datetime.now().strftime("%b %Y"),
                        "amount": amount
                    })
                save_data(self.data)
                messagebox.showinfo("Saved", "Income updated successfully!")
                self.show_tab("Income")
            except ValueError:
                messagebox.showerror("Error", "Please enter a valid number")

        ctk.CTkButton(input_frame, text="Save Income", width=150, height=38,
                      font=("Arial", 13, "bold"),
                      fg_color="#2563eb", hover_color="#1d4ed8",
                      command=save_income).pack(anchor="w", pady=5)

        # Bonus Section
        bonus_frame = ctk.CTkFrame(scroll, fg_color="#f9f9f9", corner_radius=10)
        bonus_frame.pack(fill="x", pady=15, padx=5)

        ctk.CTkLabel(bonus_frame, text="Add Bonus / Extra Income",
                     font=("Arial", 16, "bold"), text_color="#1a1a1a").pack(anchor="w", padx=20, pady=(15, 5))
        ctk.CTkLabel(bonus_frame, text="One-time bonuses, gifts, festival rewards, freelance income",
                     font=("Arial", 12), text_color="#666666").pack(anchor="w", padx=20, pady=(0, 10))

        bonus_total = sum(b["amount"] for b in self.data["bonuses"])
        ctk.CTkLabel(bonus_frame, text=f"Total Bonus Received: Rs. {bonus_total:,.0f}",
                     font=("Arial", 13, "bold"), text_color="#059669").pack(anchor="w", padx=20)

        bonus_inner = ctk.CTkFrame(bonus_frame, fg_color="#f9f9f9")
        bonus_inner.pack(fill="x", padx=20, pady=(10, 15))

        bonus_name = ctk.CTkEntry(bonus_inner, width=220, height=36,
                                  placeholder_text="Source (e.g. Diwali bonus)")
        bonus_name.grid(row=0, column=0, padx=5, pady=5)

        bonus_amt = ctk.CTkEntry(bonus_inner, width=140, height=36,
                                 placeholder_text="Amount")
        bonus_amt.grid(row=0, column=1, padx=5, pady=5)

        def add_bonus():
            name = bonus_name.get().strip()
            try:
                amt = float(bonus_amt.get())
            except ValueError:
                messagebox.showerror("Error", "Enter a valid amount")
                return
            if not name:
                messagebox.showerror("Error", "Enter a source name")
                return
            self.data["bonuses"].append({
                "name": name,
                "amount": amt,
                "date": datetime.now().strftime("%d %b %Y")
            })
            save_data(self.data)
            self.show_tab("Income")

        ctk.CTkButton(bonus_inner, text="Add Bonus", width=110, height=36,
                      font=("Arial", 13, "bold"),
                      fg_color="#059669", hover_color="#047857",
                      command=add_bonus).grid(row=0, column=2, padx=5)

        if self.data["bonuses"]:
            for i, b in enumerate(reversed(self.data["bonuses"])):
                actual_idx = len(self.data["bonuses"]) - 1 - i
                row = ctk.CTkFrame(bonus_frame, fg_color="white", corner_radius=6)
                row.pack(fill="x", padx=20, pady=3)
                ctk.CTkLabel(row, text=b["name"],
                             font=("Arial", 12, "bold"), text_color="#1a1a1a").pack(side="left", padx=15, pady=8)
                ctk.CTkLabel(row, text=b.get("date", ""),
                             font=("Arial", 11), text_color="#888888").pack(side="left", padx=10)
                ctk.CTkLabel(row, text=f"Rs. {b['amount']:,.0f}",
                             font=("Arial", 12, "bold"), text_color="#059669").pack(side="left", padx=15)
                ctk.CTkButton(row, text="X", width=30, height=26,
                              font=("Arial", 11),
                              fg_color="#dc2626", hover_color="#b91c1c",
                              command=lambda idx=actual_idx: self.delete_bonus(idx)).pack(side="right", padx=15)
            ctk.CTkLabel(bonus_frame, text="", fg_color="#f9f9f9").pack(pady=5)

        # Business history
        if profile == "Business" and self.data["business_history"]:
            hist_frame = ctk.CTkFrame(scroll, fg_color="#f9f9f9", corner_radius=10)
            hist_frame.pack(fill="both", expand=True, pady=10, padx=5)

            ctk.CTkLabel(hist_frame, text="Profit History",
                         font=("Arial", 16, "bold"), text_color="#1a1a1a").pack(anchor="w", padx=20, pady=(15, 10))

            avg = sum(h["amount"] for h in self.data["business_history"]) / len(self.data["business_history"])
            ctk.CTkLabel(hist_frame, text=f"Average Monthly Profit: Rs. {avg:,.0f}",
                         font=("Arial", 13), text_color="#059669").pack(anchor="w", padx=20, pady=(0, 10))

            for h in self.data["business_history"][-6:][::-1]:
                row = ctk.CTkFrame(hist_frame, fg_color="white", corner_radius=6)
                row.pack(fill="x", padx=15, pady=3)
                ctk.CTkLabel(row, text=h["month"],
                             font=("Arial", 12), text_color="#333333").pack(side="left", padx=15, pady=6)
                ctk.CTkLabel(row, text=f"Rs. {h['amount']:,.0f}",
                             font=("Arial", 12, "bold"), text_color="#059669").pack(side="right", padx=15)

            ctk.CTkLabel(hist_frame, text="", fg_color="#f9f9f9").pack(pady=5)

    def delete_bonus(self, idx):
        del self.data["bonuses"][idx]
        save_data(self.data)
        self.show_tab("Income")

    # ---------- Fixed Spending ----------
    def build_fixed_tab(self):
        ctk.CTkLabel(self.content, text="Fixed Spending",
                     font=("Arial", 26, "bold"), text_color="#1a1a1a").pack(anchor="w", pady=(0, 5))
        ctk.CTkLabel(self.content, text="Recurring monthly expenses like rent, EMIs, subscriptions",
                     font=("Arial", 12), text_color="#666666").pack(anchor="w", pady=(0, 15))

        total = sum(item["amount"] for item in self.data["fixed_expenses"])
        ctk.CTkLabel(self.content, text=f"Total Fixed Spending: Rs. {total:,.0f}",
                     font=("Arial", 16, "bold"), text_color="#dc2626").pack(anchor="w", pady=(0, 15))

        form = ctk.CTkFrame(self.content, fg_color="#f9f9f9", corner_radius=10)
        form.pack(fill="x", pady=5, padx=5)

        ctk.CTkLabel(form, text="Add New Fixed Expense",
                     font=("Arial", 14, "bold"), text_color="#1a1a1a").pack(anchor="w", padx=20, pady=(15, 10))

        inner = ctk.CTkFrame(form, fg_color="#f9f9f9")
        inner.pack(fill="x", padx=20, pady=(0, 15))

        name_entry = ctk.CTkEntry(inner, width=220, height=36, placeholder_text="Name (e.g. Netflix, Rent)")
        name_entry.grid(row=0, column=0, padx=5, pady=5)
        amount_entry = ctk.CTkEntry(inner, width=140, height=36, placeholder_text="Amount")
        amount_entry.grid(row=0, column=1, padx=5, pady=5)
        category_entry = ctk.CTkEntry(inner, width=160, height=36, placeholder_text="Category")
        category_entry.grid(row=0, column=2, padx=5, pady=5)

        def add_fixed():
            name = name_entry.get().strip()
            try:
                amt = float(amount_entry.get())
            except ValueError:
                messagebox.showerror("Error", "Enter a valid amount")
                return
            if not name:
                messagebox.showerror("Error", "Enter a name")
                return
            self.data["fixed_expenses"].append({
                "name": name, "amount": amt,
                "category": category_entry.get().strip() or "Other",
                "date": datetime.now().strftime("%d %b %Y")
            })
            save_data(self.data)
            self.show_tab("Fixed Spending")

        ctk.CTkButton(inner, text="Add", width=80, height=36,
                      font=("Arial", 13, "bold"),
                      fg_color="#2563eb", hover_color="#1d4ed8",
                      command=add_fixed).grid(row=0, column=3, padx=5)

        list_frame = ctk.CTkScrollableFrame(self.content, fg_color="white", height=300)
        list_frame.pack(fill="both", expand=True, pady=15, padx=5)

        if not self.data["fixed_expenses"]:
            ctk.CTkLabel(list_frame, text="No fixed expenses added yet.",
                         font=("Arial", 12), text_color="#888888").pack(pady=20)
        else:
            for i, item in enumerate(self.data["fixed_expenses"]):
                row = ctk.CTkFrame(list_frame, fg_color="#f9f9f9", corner_radius=8)
                row.pack(fill="x", pady=4, padx=5)
                info = ctk.CTkFrame(row, fg_color="#f9f9f9")
                info.pack(side="left", fill="x", expand=True, padx=15, pady=10)
                ctk.CTkLabel(info, text=item["name"],
                             font=("Arial", 13, "bold"), text_color="#1a1a1a").pack(anchor="w")
                ctk.CTkLabel(info, text=f"{item['category']} | Added: {item.get('date', '')}",
                             font=("Arial", 11), text_color="#888888").pack(anchor="w")
                ctk.CTkLabel(row, text=f"Rs. {item['amount']:,.0f}",
                             font=("Arial", 14, "bold"), text_color="#dc2626").pack(side="left", padx=15)
                ctk.CTkButton(row, text="Delete", width=70, height=30,
                              font=("Arial", 11),
                              fg_color="#dc2626", hover_color="#b91c1c",
                              command=lambda idx=i: self.delete_fixed(idx)).pack(side="right", padx=15)

    def delete_fixed(self, idx):
        del self.data["fixed_expenses"][idx]
        save_data(self.data)
        self.show_tab("Fixed Spending")

    # ---------- Variable Spending ----------
    def build_variable_tab(self):
        ctk.CTkLabel(self.content, text="Variable Spending",
                     font=("Arial", 26, "bold"), text_color="#1a1a1a").pack(anchor="w", pady=(0, 5))
        ctk.CTkLabel(self.content, text="Daily / weekly expenses like food, fuel, shopping",
                     font=("Arial", 12), text_color="#666666").pack(anchor="w", pady=(0, 15))

        total = sum(item["amount"] for item in self.data["variable_expenses"])
        ctk.CTkLabel(self.content, text=f"Total Variable Spending: Rs. {total:,.0f}",
                     font=("Arial", 16, "bold"), text_color="#dc2626").pack(anchor="w", pady=(0, 15))

        form = ctk.CTkFrame(self.content, fg_color="#f9f9f9", corner_radius=10)
        form.pack(fill="x", pady=5, padx=5)

        ctk.CTkLabel(form, text="Log New Expense",
                     font=("Arial", 14, "bold"), text_color="#1a1a1a").pack(anchor="w", padx=20, pady=(15, 10))

        inner = ctk.CTkFrame(form, fg_color="#f9f9f9")
        inner.pack(fill="x", padx=20, pady=(0, 15))

        name_entry = ctk.CTkEntry(inner, width=220, height=36, placeholder_text="Name (e.g. Groceries)")
        name_entry.grid(row=0, column=0, padx=5, pady=5)
        amount_entry = ctk.CTkEntry(inner, width=140, height=36, placeholder_text="Amount")
        amount_entry.grid(row=0, column=1, padx=5, pady=5)
        category_dropdown = ctk.CTkComboBox(inner, width=160, height=36,
                                            values=["Food", "Shopping", "Fuel", "Medical",
                                                    "Entertainment", "Activities", "Other"])
        category_dropdown.set("Food")
        category_dropdown.grid(row=0, column=2, padx=5, pady=5)

        def add_variable():
            name = name_entry.get().strip()
            try:
                amt = float(amount_entry.get())
            except ValueError:
                messagebox.showerror("Error", "Enter a valid amount")
                return
            if not name:
                messagebox.showerror("Error", "Enter a name")
                return
            self.data["variable_expenses"].append({
                "name": name, "amount": amt,
                "category": category_dropdown.get(),
                "date": datetime.now().strftime("%d %b %Y")
            })
            save_data(self.data)
            self.show_tab("Variable Spending")

        ctk.CTkButton(inner, text="Add", width=80, height=36,
                      font=("Arial", 13, "bold"),
                      fg_color="#2563eb", hover_color="#1d4ed8",
                      command=add_variable).grid(row=0, column=3, padx=5)

        list_frame = ctk.CTkScrollableFrame(self.content, fg_color="white", height=300)
        list_frame.pack(fill="both", expand=True, pady=15, padx=5)

        if not self.data["variable_expenses"]:
            ctk.CTkLabel(list_frame, text="No variable expenses logged yet.",
                         font=("Arial", 12), text_color="#888888").pack(pady=20)
        else:
            for i, item in enumerate(reversed(self.data["variable_expenses"])):
                actual_idx = len(self.data["variable_expenses"]) - 1 - i
                row = ctk.CTkFrame(list_frame, fg_color="#f9f9f9", corner_radius=8)
                row.pack(fill="x", pady=4, padx=5)
                info = ctk.CTkFrame(row, fg_color="#f9f9f9")
                info.pack(side="left", fill="x", expand=True, padx=15, pady=10)
                ctk.CTkLabel(info, text=item["name"],
                             font=("Arial", 13, "bold"), text_color="#1a1a1a").pack(anchor="w")
                ctk.CTkLabel(info, text=f"{item['category']} | {item.get('date', '')}",
                             font=("Arial", 11), text_color="#888888").pack(anchor="w")
                ctk.CTkLabel(row, text=f"Rs. {item['amount']:,.0f}",
                             font=("Arial", 14, "bold"), text_color="#dc2626").pack(side="left", padx=15)
                ctk.CTkButton(row, text="Delete", width=70, height=30,
                              font=("Arial", 11),
                              fg_color="#dc2626", hover_color="#b91c1c",
                              command=lambda idx=actual_idx: self.delete_variable(idx)).pack(side="right", padx=15)

    def delete_variable(self, idx):
        del self.data["variable_expenses"][idx]
        save_data(self.data)
        self.show_tab("Variable Spending")

    # ---------- Budget Tab ----------
    def build_budget_tab(self):
        scroll = ctk.CTkScrollableFrame(self.content, fg_color="white")
        scroll.pack(fill="both", expand=True)

        ctk.CTkLabel(scroll, text="Budget",
                     font=("Arial", 26, "bold"), text_color="#1a1a1a").pack(anchor="w", pady=(0, 5))
        ctk.CTkLabel(scroll, text="Set monthly spending limits for each category",
                     font=("Arial", 12), text_color="#666666").pack(anchor="w", pady=(0, 15))

        bonus_total = sum(b["amount"] for b in self.data["bonuses"])
        income = self.data["income"] + bonus_total
        fixed_total = sum(item["amount"] for item in self.data["fixed_expenses"])
        surplus = income - fixed_total

        summary = ctk.CTkFrame(scroll, fg_color="#f9f9f9", corner_radius=10)
        summary.pack(fill="x", pady=5, padx=5)

        ctk.CTkLabel(summary, text="Your Numbers",
                     font=("Arial", 15, "bold"), text_color="#1a1a1a").pack(anchor="w", padx=20, pady=(15, 8))
        ctk.CTkLabel(summary, text=f"Total Income (incl. bonus): Rs. {income:,.0f}",
                     font=("Arial", 13), text_color="#2563eb").pack(anchor="w", padx=20)
        ctk.CTkLabel(summary, text=f"Fixed Spending (auto deducted): Rs. {fixed_total:,.0f}",
                     font=("Arial", 13), text_color="#dc2626").pack(anchor="w", padx=20)
        ctk.CTkLabel(summary, text=f"Surplus Available: Rs. {surplus:,.0f}",
                     font=("Arial", 14, "bold"),
                     text_color="#059669" if surplus >= 0 else "#dc2626").pack(anchor="w", padx=20, pady=(5, 15))

        budget_frame = ctk.CTkFrame(scroll, fg_color="#f9f9f9", corner_radius=10)
        budget_frame.pack(fill="x", pady=10, padx=5)

        ctk.CTkLabel(budget_frame, text="Set Category Budgets",
                     font=("Arial", 15, "bold"), text_color="#1a1a1a").pack(anchor="w", padx=20, pady=(15, 10))

        categories = ["Food", "Shopping", "Fuel", "Medical", "Entertainment", "Activities", "Other"]
        entries = {}
        budget_inner = ctk.CTkFrame(budget_frame, fg_color="#f9f9f9")
        budget_inner.pack(fill="x", padx=20, pady=(0, 10))

        for i, cat in enumerate(categories):
            row = i // 2
            col = i % 2
            cell = ctk.CTkFrame(budget_inner, fg_color="#f9f9f9")
            cell.grid(row=row, column=col, padx=10, pady=5, sticky="w")
            ctk.CTkLabel(cell, text=f"{cat}:", width=100, font=("Arial", 12)).pack(side="left")
            e = ctk.CTkEntry(cell, width=130, height=32, placeholder_text="Max Rs.")
            current = self.data["budgets"].get(cat, "")
            if current:
                e.insert(0, str(current))
            e.pack(side="left", padx=5)
            entries[cat] = e

        def save_budgets():
            for cat, e in entries.items():
                val = e.get().strip()
                if val:
                    try:
                        self.data["budgets"][cat] = float(val)
                    except ValueError:
                        pass
            save_data(self.data)
            messagebox.showinfo("Saved", "Budgets saved! Check the Report tab for analysis.")
            self.show_tab("Budget")

        ctk.CTkButton(budget_frame, text="Save Budgets", width=150, height=36,
                      font=("Arial", 13, "bold"),
                      fg_color="#2563eb", hover_color="#1d4ed8",
                      command=save_budgets).pack(anchor="w", padx=20, pady=(5, 15))

        if self.data["budgets"]:
            total_budget = sum(self.data["budgets"].values())
            ctk.CTkLabel(scroll, text=f"Total Budgeted: Rs. {total_budget:,.0f}",
                         font=("Arial", 14, "bold"), text_color="#2563eb").pack(anchor="w", pady=10, padx=5)

    # ---------- Report Tab ----------
    def build_report_tab(self):
        scroll = ctk.CTkScrollableFrame(self.content, fg_color="white")
        scroll.pack(fill="both", expand=True)

        ctk.CTkLabel(scroll, text="Report",
                     font=("Arial", 26, "bold"), text_color="#1a1a1a").pack(anchor="w", pady=(0, 5))
        ctk.CTkLabel(scroll, text="Monthly spending analysis vs budget",
                     font=("Arial", 12), text_color="#666666").pack(anchor="w", pady=(0, 15))

        if not self.data["budgets"]:
            empty = ctk.CTkFrame(scroll, fg_color="#f9f9f9", corner_radius=10)
            empty.pack(fill="x", pady=20, padx=5)
            ctk.CTkLabel(empty, text="No budgets set yet",
                         font=("Arial", 16, "bold"), text_color="#dc2626").pack(padx=20, pady=(20, 5))
            ctk.CTkLabel(empty, text="Go to the Budget tab and set spending limits to see your report.",
                         font=("Arial", 12), text_color="#666666").pack(padx=20, pady=(0, 20))
            return

        spent_by_cat = {}
        for item in self.data["variable_expenses"]:
            cat = item["category"]
            spent_by_cat[cat] = spent_by_cat.get(cat, 0) + item["amount"]

        over_total = 0
        saved_total = 0
        for cat, budget in self.data["budgets"].items():
            spent = spent_by_cat.get(cat, 0)
            if spent > budget:
                over_total += (spent - budget)
            else:
                saved_total += (budget - spent)

        verdict_frame = ctk.CTkFrame(scroll, fg_color="#f9f9f9", corner_radius=10)
        verdict_frame.pack(fill="x", pady=5, padx=5)

        ctk.CTkLabel(verdict_frame, text="Overall Summary",
                     font=("Arial", 16, "bold"), text_color="#1a1a1a").pack(anchor="w", padx=20, pady=(15, 8))

        if over_total > 0:
            ctk.CTkLabel(verdict_frame, text=f"You overspent Rs. {over_total:,.0f} this month",
                         font=("Arial", 14, "bold"), text_color="#dc2626").pack(anchor="w", padx=20)
        if saved_total > 0:
            ctk.CTkLabel(verdict_frame, text=f"You saved Rs. {saved_total:,.0f} across categories within budget",
                         font=("Arial", 14, "bold"), text_color="#059669").pack(anchor="w", padx=20, pady=(0, 15))
        if over_total == 0 and saved_total == 0:
            ctk.CTkLabel(verdict_frame, text="Log variable expenses to see your report.",
                         font=("Arial", 12), text_color="#888888").pack(anchor="w", padx=20, pady=(0, 15))

        ctk.CTkLabel(scroll, text="Category Breakdown",
                     font=("Arial", 16, "bold"), text_color="#1a1a1a").pack(anchor="w", padx=5, pady=(20, 10))

        for cat, budget in self.data["budgets"].items():
            spent = spent_by_cat.get(cat, 0)
            pct = (spent / budget * 100) if budget > 0 else 0

            if pct >= 100:
                color = "#dc2626"
                status = "OVER BUDGET"
            elif pct >= 80:
                color = "#d97706"
                status = "CLOSE TO LIMIT"
            else:
                color = "#059669"
                status = "WITHIN BUDGET"

            row = ctk.CTkFrame(scroll, fg_color="#f9f9f9", corner_radius=8)
            row.pack(fill="x", pady=4, padx=5)

            top_row = ctk.CTkFrame(row, fg_color="#f9f9f9")
            top_row.pack(fill="x", padx=15, pady=(10, 5))
            ctk.CTkLabel(top_row, text=cat,
                         font=("Arial", 14, "bold"), text_color="#1a1a1a").pack(side="left")
            ctk.CTkLabel(top_row, text=status,
                         font=("Arial", 12, "bold"), text_color=color).pack(side="right")

            ctk.CTkLabel(row, text=f"Spent Rs. {spent:,.0f} of Rs. {budget:,.0f}  ({pct:.0f}%)",
                         font=("Arial", 12), text_color="#666666").pack(anchor="w", padx=15)

            progress = ctk.CTkProgressBar(row, height=8, progress_color=color)
            progress.pack(fill="x", padx=15, pady=(5, 12))
            progress.set(min(pct / 100, 1.0))

    # ---------- Investment Portfolio ----------
    def build_investment_tab(self):
        ctk.CTkLabel(self.content, text="Investment Portfolio",
                     font=("Arial", 26, "bold"), text_color="#1a1a1a").pack(anchor="w", pady=(0, 5))
        ctk.CTkLabel(self.content, text="Track your assets: property, vehicles, watches, stocks, gold, etc.",
                     font=("Arial", 12), text_color="#666666").pack(anchor="w", pady=(0, 15))

        total_value = sum(item["value"] for item in self.data["investments"])
        ctk.CTkLabel(self.content, text=f"Total Portfolio Value: Rs. {total_value:,.0f}",
                     font=("Arial", 18, "bold"), text_color="#059669").pack(anchor="w", pady=(0, 15))

        form = ctk.CTkFrame(self.content, fg_color="#f9f9f9", corner_radius=10)
        form.pack(fill="x", pady=5, padx=5)

        ctk.CTkLabel(form, text="Add Investment / Asset",
                     font=("Arial", 14, "bold"), text_color="#1a1a1a").pack(anchor="w", padx=20, pady=(15, 10))

        inner = ctk.CTkFrame(form, fg_color="#f9f9f9")
        inner.pack(fill="x", padx=20, pady=(0, 15))

        name_entry = ctk.CTkEntry(inner, width=220, height=36,
                                  placeholder_text="Name (e.g. House, Rolex)")
        name_entry.grid(row=0, column=0, padx=5, pady=5)

        value_entry = ctk.CTkEntry(inner, width=140, height=36,
                                   placeholder_text="Value (Rs.)")
        value_entry.grid(row=0, column=1, padx=5, pady=5)

        type_dropdown = ctk.CTkComboBox(inner, width=160, height=36,
                                        values=["Property", "Vehicle", "Watch", "Jewelry",
                                                "Stocks", "Mutual Fund", "Gold", "Crypto",
                                                "Fixed Deposit", "Other"])
        type_dropdown.set("Property")
        type_dropdown.grid(row=0, column=2, padx=5, pady=5)

        def add_investment():
            name = name_entry.get().strip()
            try:
                val = float(value_entry.get())
            except ValueError:
                messagebox.showerror("Error", "Enter a valid value")
                return
            if not name:
                messagebox.showerror("Error", "Enter a name")
                return
            self.data["investments"].append({
                "name": name, "value": val,
                "type": type_dropdown.get(),
                "date": datetime.now().strftime("%d %b %Y")
            })
            save_data(self.data)
            self.show_tab("Investment Portfolio")

        ctk.CTkButton(inner, text="Add", width=80, height=36,
                      font=("Arial", 13, "bold"),
                      fg_color="#059669", hover_color="#047857",
                      command=add_investment).grid(row=0, column=3, padx=5)

        list_frame = ctk.CTkScrollableFrame(self.content, fg_color="white", height=300)
        list_frame.pack(fill="both", expand=True, pady=15, padx=5)

        if not self.data["investments"]:
            ctk.CTkLabel(list_frame, text="No investments added yet.",
                         font=("Arial", 12), text_color="#888888").pack(pady=20)
        else:
            for i, item in enumerate(self.data["investments"]):
                row = ctk.CTkFrame(list_frame, fg_color="#f9f9f9", corner_radius=8)
                row.pack(fill="x", pady=4, padx=5)
                info = ctk.CTkFrame(row, fg_color="#f9f9f9")
                info.pack(side="left", fill="x", expand=True, padx=15, pady=10)
                ctk.CTkLabel(info, text=item["name"],
                             font=("Arial", 14, "bold"), text_color="#1a1a1a").pack(anchor="w")
                ctk.CTkLabel(info, text=f"{item['type']} | Added: {item.get('date', '')}",
                             font=("Arial", 11), text_color="#888888").pack(anchor="w")
                ctk.CTkLabel(row, text=f"Rs. {item['value']:,.0f}",
                             font=("Arial", 15, "bold"), text_color="#059669").pack(side="left", padx=15)
                ctk.CTkButton(row, text="Delete", width=70, height=30,
                              font=("Arial", 11),
                              fg_color="#dc2626", hover_color="#b91c1c",
                              command=lambda idx=i: self.delete_investment(idx)).pack(side="right", padx=15)

    def delete_investment(self, idx):
        del self.data["investments"][idx]
        save_data(self.data)
        self.show_tab("Investment Portfolio")

    # ---------- AI Assistant ----------
    def build_ai_tab(self):
        ctk.CTkLabel(self.content, text="AI Assistant",
                     font=("Arial", 26, "bold"), text_color="#1a1a1a").pack(anchor="w", pady=(0, 5))
        ctk.CTkLabel(self.content, text="Ask Gemini AI about your finances, budgeting tips, or investment advice",
                     font=("Arial", 12), text_color="#666666").pack(anchor="w", pady=(0, 15))

        api_frame = ctk.CTkFrame(self.content, fg_color="#f9f9f9", corner_radius=10)
        api_frame.pack(fill="x", pady=5, padx=5)

        ctk.CTkLabel(api_frame, text="Gemini API Key",
                     font=("Arial", 14, "bold"), text_color="#1a1a1a").pack(anchor="w", padx=20, pady=(15, 5))
        ctk.CTkLabel(api_frame, text="Get a free key from https://aistudio.google.com/apikey",
                     font=("Arial", 11), text_color="#666666").pack(anchor="w", padx=20)

        api_inner = ctk.CTkFrame(api_frame, fg_color="#f9f9f9")
        api_inner.pack(fill="x", padx=20, pady=(10, 15))

        api_entry = ctk.CTkEntry(api_inner, width=400, height=36,
                                 placeholder_text="Paste your Gemini API key here",
                                 show="*")
        api_entry.pack(side="left", padx=(0, 10))
        if self.data["gemini_api_key"]:
            api_entry.insert(0, self.data["gemini_api_key"])

        def save_api_key():
            key = api_entry.get().strip()
            self.data["gemini_api_key"] = key
            save_data(self.data)
            if key:
                messagebox.showinfo("Saved", "API key saved successfully!")
            else:
                messagebox.showinfo("Cleared", "API key removed.")

        ctk.CTkButton(api_inner, text="Save Key", width=110, height=36,
                      font=("Arial", 12, "bold"),
                      fg_color="#2563eb", hover_color="#1d4ed8",
                      command=save_api_key).pack(side="left")

        chat_frame = ctk.CTkScrollableFrame(self.content, fg_color="#fafafa", height=320)
        chat_frame.pack(fill="both", expand=True, pady=15, padx=5)
        self.chat_frame_ref = chat_frame

        if not self.data["chat_history"]:
            ctk.CTkLabel(chat_frame,
                         text="Hi! I am your finance assistant.\nAsk me anything about your money, budgeting, or investments.",
                         font=("Arial", 13), text_color="#666666").pack(pady=30)
        else:
            self.render_chat_history()

        input_frame = ctk.CTkFrame(self.content, fg_color="white")
        input_frame.pack(fill="x", pady=(5, 0), padx=5)

        msg_entry = ctk.CTkEntry(input_frame, height=40,
                                 font=("Arial", 13),
                                 placeholder_text="Type your question here...")
        msg_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        def send_message():
            msg = msg_entry.get().strip()
            if not msg:
                return
            if not self.data["gemini_api_key"]:
                messagebox.showerror("No API Key", "Please save your Gemini API key first.")
                return

            bonus_total = sum(b["amount"] for b in self.data["bonuses"])
            income = self.data["income"] + bonus_total
            fixed_total = sum(item["amount"] for item in self.data["fixed_expenses"])
            variable_total = sum(item["amount"] for item in self.data["variable_expenses"])
            inv_total = sum(item["value"] for item in self.data["investments"])
            score, verdict = calculate_stability_score(self.data)

            context = (f"User's financial summary: Profile={self.data['profile_type']}, "
                       f"Monthly Income (incl bonus)=Rs.{income:,.0f}, "
                       f"Fixed Expenses=Rs.{fixed_total:,.0f}, "
                       f"Variable Expenses=Rs.{variable_total:,.0f}, "
                       f"Investments=Rs.{inv_total:,.0f}, "
                       f"Stability Score={score}/100 ({verdict}). "
                       f"Keep replies short, friendly, and practical.")

            self.data["chat_history"].append({"role": "user", "text": msg})
            save_data(self.data)
            msg_entry.delete(0, "end")

            self.data["chat_history"].append({"role": "ai", "text": "Thinking..."})
            self.render_chat_history()
            self.update_idletasks()

            reply = call_gemini(self.data["gemini_api_key"], msg, context)

            self.data["chat_history"][-1] = {"role": "ai", "text": reply}
            save_data(self.data)
            self.render_chat_history()

        ctk.CTkButton(input_frame, text="Send", width=90, height=40,
                      font=("Arial", 13, "bold"),
                      fg_color="#2563eb", hover_color="#1d4ed8",
                      command=send_message).pack(side="left")

        ctk.CTkButton(input_frame, text="Clear", width=70, height=40,
                      font=("Arial", 12),
                      fg_color="#888888", hover_color="#666666",
                      command=self.clear_chat).pack(side="left", padx=(5, 0))

        msg_entry.bind("<Return>", lambda e: send_message())

    def render_chat_history(self):
        for widget in self.chat_frame_ref.winfo_children():
            widget.destroy()

        for msg in self.data["chat_history"]:
            if msg["role"] == "user":
                row = ctk.CTkFrame(self.chat_frame_ref, fg_color="#fafafa")
                row.pack(fill="x", pady=4)
                bubble = ctk.CTkFrame(row, fg_color="#2563eb", corner_radius=10)
                bubble.pack(side="right", padx=10)
                ctk.CTkLabel(bubble, text=msg["text"],
                             font=("Arial", 12), text_color="white",
                             wraplength=500, justify="left").pack(padx=14, pady=8)
            else:
                row = ctk.CTkFrame(self.chat_frame_ref, fg_color="#fafafa")
                row.pack(fill="x", pady=4)
                bubble = ctk.CTkFrame(row, fg_color="#e5e5e5", corner_radius=10)
                bubble.pack(side="left", padx=10)
                ctk.CTkLabel(bubble, text=msg["text"],
                             font=("Arial", 12), text_color="#1a1a1a",
                             wraplength=500, justify="left").pack(padx=14, pady=8)

    def clear_chat(self):
        if messagebox.askyesno("Clear Chat", "Clear chat history?"):
            self.data["chat_history"] = []
            save_data(self.data)
            self.show_tab("AI Assistant")


# ---------- Run ----------
if __name__ == "__main__":
    app = PaisaPilotApp()
    app.mainloop()
