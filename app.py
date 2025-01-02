from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from datetime import datetime, timedelta



app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///finance.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

@app.route('/')
def index():
    return render_template('index.html')

from flask import jsonify

@app.route('/signup', methods=['POST'])
def signup():
    full_name = request.form['full_name']
    email = request.form['email']
    username = request.form['username']
    password = bcrypt.generate_password_hash(request.form['password']).decode('utf-8')

    if User.query.filter_by(email=email).first():
        return jsonify({'status': 'error', 'message': 'Email already exists!'}), 400
    if User.query.filter_by(username=username).first():
        return jsonify({'status': 'error', 'message': 'Username already exists!'}), 400

    new_user = User(full_name=full_name, email=email, username=username, password=password)
    db.session.add(new_user)
    db.session.commit()
    return jsonify({'status': 'success', 'message': 'Sign-up successful! Please login.'}), 200

@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']
    user = User.query.filter_by(username=username).first()

    if user and bcrypt.check_password_hash(user.password, password):
        return jsonify({'status': 'success', 'redirect_url': url_for('welcome', username=user.username)}), 200
    else:
        return jsonify({'status': 'error', 'message': 'Invalid username or password.'}), 401

@app.route('/welcome/<username>')
def welcome(username):
    return render_template('welcome.html', username=username)





@app.route('/dashboard')
def dashboard():
    today = datetime.today()

    # Fetch upcoming bills from the database
    upcoming_bills = Bill.query.filter(
        Bill.due_date <= (today + timedelta(days=2)).strftime('%Y-%m-%d'),
        Bill.due_date >= today.strftime('%Y-%m-%d')
    ).all()

    # Calculate the number of bills to be paid
    bills_to_pay = len([bill for bill in upcoming_bills if bill.due_date >= today.strftime('%Y-%m-%d')])

    # Fetch accounts for the user and calculate the total balance
    user_id = 1  # Assuming the user ID is 1 for now
    accounts = Account.query.filter_by(user_id=user_id).all()
    total_balance = sum(account.balance for account in accounts)

    # Fetch all goals from the database
    goals = Goal.query.all()  # Fetch goals directly from the database
    goals_achieved = []

    # Find the goals that have been achieved
    for goal in goals:
        if total_balance >= goal.target_amount:
            goals_achieved.append(goal)

    # Example: Expense data for the bar graph
    expenses_data = [
        {"category": "Expenses", "value": 40},
        {"category": "Income", "value": 60},
        {"category": "Other", "value": 20}
    ]

    return render_template(
        'dashboard.html', 
        username='User',
        total_balance=total_balance, 
        bills_to_pay=bills_to_pay,
        goals_achieved=goals_achieved,
        expenses_data=expenses_data, 
        upcoming_bills=upcoming_bills
    )

class Account(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    card_number = db.Column(db.String(20), nullable=False)
    account_name = db.Column(db.String(100), nullable=False)
    balance = db.Column(db.Float, nullable=False, default=0.0)  # New balance field

@app.route('/balances', methods=['GET', 'POST'])
def balances():
    if request.method == 'POST':
        card_number = request.form['card_number']
        account_name = request.form['account_name']
        balance = float(request.form['balance']) 

        user_id = 1  # Assuming a fixed user_id for now
        new_account = Account(user_id=user_id, card_number=card_number, account_name=account_name, balance=balance)
        db.session.add(new_account)
        db.session.commit()
        flash('Account added successfully!', 'success')
        return redirect(url_for('balances'))

    user_id = 1  # Assuming a fixed user_id for now
    accounts = Account.query.filter_by(user_id=user_id).all()
    
    # Calculate the total balance
    total_balance = sum(account.balance for account in accounts)

    return render_template('balances.html', username='User', accounts=accounts, total_balance=total_balance)


# Add the 'category' column to the Transaction model
class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    type = db.Column(db.String(10), nullable=False)
    category = db.Column(db.String(50), nullable=False)  # New category field

@app.route('/transactions', methods=['GET', 'POST'])
def transactions():
    if request.method == 'POST':
        account_id = int(request.form['account_id'])
        amount = float(request.form['amount'])
        trans_type = request.form['type']
        category = request.form['category']  # Capture the category from the form

        account = Account.query.get(account_id)
        if not account:
            flash("Invalid account selected.", "danger")
            return redirect(url_for('transactions'))

        # Update balance based on transaction type
        if trans_type == 'Credit':
            account.balance += amount
        elif trans_type == 'Debit':
            if account.balance < amount:
                flash("Insufficient balance for this transaction.", "danger")
                return redirect(url_for('transactions'))
            account.balance -= amount

        # Create a new transaction record
        new_transaction = Transaction(account_id=account_id, amount=amount, type=trans_type, category=category)
        db.session.add(new_transaction)
        db.session.commit()

        flash('Transaction added successfully, and balance updated!', 'success')
        return redirect(url_for('transactions'))
    
    transactions = Transaction.query.all()  # Fetch all transactions
    accounts = Account.query.all()  # Fetch all accounts for the dropdown
    return render_template('transactions.html', transactions=transactions, accounts=accounts)


class Bill(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    bill_name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(200), nullable=False)
    due_date = db.Column(db.String(50), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.String(50), nullable=False, default='CURRENT_TIMESTAMP')


@app.route('/bills', methods=['GET', 'POST'])
def bills():
    if request.method == 'POST':
        
        bill_name = request.form['bill_name']
        description = request.form['description']
        due_date = request.form['due_date']
        amount = float(request.form['amount'])

        new_bill = Bill(bill_name=bill_name, description=description, due_date=due_date, amount=amount)
        db.session.add(new_bill)
        db.session.commit()

        flash('Bill added successfully!', 'success')
        return redirect(url_for('bills'))

    bills = Bill.query.all()  
    return render_template('bills.html', bills=bills)


@app.route('/expenses')
def expenses():
    # Fetch the transaction data categorized as Expenses, Income, and Other
    expenses_total = db.session.query(db.func.sum(Transaction.amount)).filter(Transaction.category == 'Expenses').scalar() or 0
    income_total = db.session.query(db.func.sum(Transaction.amount)).filter(Transaction.category == 'Income').scalar() or 0
    other_total = db.session.query(db.func.sum(Transaction.amount)).filter(Transaction.category == 'Other').scalar() or 0

    # Calculate total and percentages
    total = expenses_total + income_total + other_total
    expenses_percentage = (expenses_total / total * 100) if total > 0 else 0
    income_percentage = (income_total / total * 100) if total > 0 else 0
    other_percentage = (other_total / total * 100) if total > 0 else 0

    # Fetch all transactions
    transactions = Transaction.query.all()

    # Pass the data to the HTML template
    return render_template(
        'expenses.html',
        expenses=expenses_total,
        income=income_total,
        other=other_total,
        expenses_percentage=expenses_percentage,
        income_percentage=income_percentage,
        other_percentage=other_percentage,
        transactions=transactions  # Pass the transactions list to the template
    )


class Goal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    goal_name = db.Column(db.String(100), nullable=False)
    target_amount = db.Column(db.Float, nullable=False)

@app.route('/goals', methods=['GET', 'POST'])
def goals():
    if request.method == 'POST':
        goal_name = request.form['goal_name']
        target_amount = float(request.form['target_amount'])
        new_goal = Goal(goal_name=goal_name, target_amount=target_amount)
        db.session.add(new_goal)
        db.session.commit()
        return redirect(url_for('goals'))

    goals = Goal.query.all()
    return render_template('goals.html', goals=goals)



if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
