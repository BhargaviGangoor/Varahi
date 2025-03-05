import sqlite3
from flask import Flask, render_template,request,redirect,url_for,session,flash
import math


app = Flask(__name__)
app.secret_key="your_secret_key_here"
user_budget=0

DATABASE="varahi.db"

expenses=[]

def get_db_connection():
    conn=sqlite3.connect(DATABASE)
    conn.row_factory=sqlite3.Row
    return conn

def init_db():
    conn=sqlite3.connect(DATABASE)
    cursor=conn.cursor()
    
    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS users (
                       id INTEGER PRIMARY KEY AUTOINCREMENT,
                       name TEXT NOT NULL,
                       email TEXT UNIQUE NOT NULL
                   )
                   ''')
    
    
    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS expenses (
                       id INTEGER PRIMARY KEY AUTOINCREMENT,
                       user_id INTEGER,
                       name TEXT NOT NULL,
                       amount REAL NOT NULL,
                       category TEXT NOT NULL,
                       budget_amount REAL NOT NULL,
                       date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                       FOREIGN KEY(user_id) REFERENCES users(id)
                   )
                   ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS budgets (
            user_id INTEGER PRIMARY KEY,
            budget_amount REAL NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')
    conn.commit()
    conn.close()
    
init_db()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/add_user',methods=['GET','POST'])
def add_user():
    if request.method =='POST':
        name=request.form['name']
        email=request.form['email']
        
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        existing_user = cursor.fetchone()
        if existing_user:
            conn.close()
            flash("Error: Email already exists! Please use a different email.", "error")
            return redirect(url_for('add_user'))

        # Insert new user
        cursor.execute('''INSERT INTO users (name, email) VALUES (?, ?)''', (name, email))
        conn.commit()
        user_id = cursor.lastrowid
        session['user_id'] = user_id 
        conn.close()
        
        flash("Registration successful! Welcome,"+name,"success")
        return redirect(url_for('users'))
    return render_template('add_user.html')

@app.route('/users')
def users():
    conn = get_db_connection()
    users = conn.execute('SELECT * FROM users').fetchall()
    conn.close()
    
    return render_template('profile.html', users=users)

@app.route('/budget')
def budget():
    user_id = session.get("user_id")
    if not user_id:
        flash("Please log in first to view your budget!", "error")
        return redirect(url_for("home"))

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT budget_amount FROM budgets WHERE user_id = ?", (user_id,))
    budget_data = cursor.fetchone()
    print(f"Fetched Budget Data: {budget_data}")
    conn.close()

    budget_value = budget_data[0] if budget_data else 0  # Default to 0 if no budget set

    print(f"Budget Value to be Rendered: {budget_value}") 
    return render_template('budget.html', budget_value=budget_value)

@app.route("/set_budget",methods=["POST"])
def set_budget():
    user_id=session.get("user_id")
    if not user_id:
        flash("Please log in first to set a budget!","error")
        return redirect(url_for("budget"))
    
    budget_value = request.form.get("budget")
    conn=get_db_connection()
    cursor=conn.cursor()
    cursor.execute("SELECT budget_amount FROM budgets WHERE user_id = ?", (user_id,))
    existing_budget = cursor.fetchone()

    if existing_budget:
            # Update existing budget
        cursor.execute("UPDATE budgets SET budget_amount = ? WHERE user_id = ?", (budget_value, user_id))
    else:
            # Insert new budget
        cursor.execute("INSERT INTO budgets (user_id, budget_amount) VALUES (?, ?)", (user_id, budget_value))

    conn.commit()
    conn.close()
    flash("Budget updated successfully!", "success")
    
    return redirect(url_for("budget"))
 
@app.route('/expense_tracker',methods=['GET','POST'])
def expense_tracker():
    user_id = session.get("user_id")
    if not user_id:
        flash("Please log in first!", "error")
        return redirect(url_for("home"))

    conn = get_db_connection()
    cursor = conn.cursor()
    if request.method=='POST' :
        name=request.form['expense-name']
        amount=request.form['expense-amount']
        category=request.form['expense-category']
        budget_amount=0
        
        cursor.execute("SELECT budget_amount FROM budgets WHERE user_id = ?", (user_id,))
        budget_data = cursor.fetchone() 
        budget_amount = budget_data[0] if budget_data else 0 

        cursor.execute('''
            INSERT INTO expenses (user_id, name, amount, category, budget_amount)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, name, amount, category, budget_amount))
        conn.commit()
        
   
    expenses = cursor.execute("SELECT * FROM expenses WHERE user_id = ?", (user_id,)).fetchall()
    cursor.execute("SELECT SUM(amount) FROM expenses WHERE user_id = ?", (user_id,))
    total_expense = cursor.fetchone()[0] or 0  # Default to 0 if no expenses
   
    cursor.execute("SELECT category, SUM(amount) as total FROM expenses WHERE user_id = ? GROUP BY category", (user_id,))
    category_data = cursor.fetchall()
    categories = [row['category'] for row in category_data]
    totals = [row['total'] for row in category_data]
    
    cursor.execute("SELECT budget_amount FROM budgets WHERE user_id = ?", (user_id,))
    budget_data = cursor.fetchone()
    budget_amount = budget_data[0] if budget_data else 0

    conn.close() 
    
    overspending_alert = None
    if budget_amount > 0 and total_expense > budget_amount:
        overspending_alert = f"⚠️ Warning: You've exceeded your budget! (₹{total_expense} spent, Budget: ₹{budget_amount})"
         
         
    return render_template("expense_tracker.html",expenses=expenses,total_expense=total_expense,overspending_alert=overspending_alert,categories=categories,totals=totals)

@app.route('/delete_expense/<int:expense_id>', methods=['POST'])
def delete_expense(expense_id):
    user_id = session.get("user_id")
    if not user_id:
        flash("Please log in first!", "error")
        return redirect(url_for("expense_tracker"))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM expenses WHERE id = ? AND user_id = ?", (expense_id, user_id))
    conn.commit()
    conn.close()

    return redirect(url_for("expense_tracker"))


@app.route('/delete_all_expenses',methods=['POST'])
def delete_all_expenses():
    user_id = session.get("user_id")
    if not user_id:
        flash("Please log in first!", "error")
        return redirect(url_for("expense_tracker"))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM expenses WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

    return redirect(url_for("expense_tracker"))


@app.route('/edit_expense/<int:expense_id>', methods=['GET'])
def edit_expense(expense_id):
    user_id = session.get("user_id")
    if not user_id:
        flash("Please log in first!", "error")
        return redirect(url_for("expense_tracker"))

    conn = get_db_connection()
    cursor = conn.cursor()
    expense = cursor.execute("SELECT * FROM expenses WHERE id = ? AND user_id = ?", (expense_id, user_id)).fetchone()
    conn.close()

    if not expense:
        flash("Expense not found!", "error")
        return redirect(url_for("expense_tracker"))

    return render_template('edit_expense.html', expense=expense)

@app.route('/update_expense/<int:expense_id>', methods=['POST'])
def update_expense(expense_id):
    user_id = session.get("user_id")
    if not user_id:
        flash("Please log in first!", "error")
        return redirect(url_for("expense_tracker"))

    name = request.form['expense-name']
    amount = float(request.form['expense-amount'])
    category = request.form['expense-category']

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE expenses
        SET name = ?, amount = ?, category = ?
        WHERE id = ? AND user_id = ?
    ''', (name, amount, category, expense_id, user_id))
    conn.commit()
    conn.close()

    flash("Expense updated successfully!", "success")
    return redirect(url_for("expense_tracker"))

@app.route('/banking')
def banking():
    return render_template('banking.html')

@app.route('/investments')
def investments():
    return render_template('investments.html')

@app.route('/learning')
def learning():
    return render_template('learning.html')

@app.route('/profile')
def profile():
    user_id = session.get('user_id')
    if not user_id:
        return "No user logged in. Please <a href='/add_user'>register</a> first."
        
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    users = conn.execute('SELECT * FROM users').fetchall()  # Fetch all users for display
    conn.close()
    
    return render_template('profile.html', user=user, users=users)



# SIP Calculator Route
@app.route('/sip_calculator', methods=['GET', 'POST'])
def sip_calculator():
    result = None
    if request.method == 'POST':
        monthly_investment = float(request.form['monthly_investment'])
        annual_rate = float(request.form['annual_rate'])
        years = float(request.form['years'])
        
        n = years * 12  # Total months
        r = (annual_rate / 100) / 12  # Monthly interest rate
        
        future_value = monthly_investment * (((1 + r) ** n - 1) / r) * (1 + r)
        result = round(future_value, 2)
    
    return render_template('sip_emi.html', calculator_type='SIP', result=result)

# EMI Calculator Route
@app.route('/emi_calculator', methods=['GET', 'POST'])
def emi_calculator():
    result = None
    if request.method == 'POST':
        loan_amount = float(request.form['loan_amount'])
        annual_rate = float(request.form['annual_rate'])
        tenure_years = float(request.form['tenure_years'])
        
        tenure_months = tenure_years * 12
        monthly_rate = (annual_rate / 100) / 12
        
        emi = (loan_amount * monthly_rate * (math.pow(1 + monthly_rate, tenure_months))) / (math.pow(1 + monthly_rate, tenure_months) - 1)
        result = round(emi, 2)
    
    return render_template('sip_emi.html', calculator_type='EMI', result=result)

if __name__ == '__main__':
    app.run(debug=True)
