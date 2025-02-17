import pandas as pd
import os
import matplotlib.pyplot as plt
from tabulate import tabulate

# Load the monthly summary data
file_path = 'monthly_summary.csv'
transactions_file = 'transactions.csv'

if not os.path.exists(file_path) or not os.path.exists(transactions_file):
    raise FileNotFoundError("Required CSV files not found. Please generate them first.")

# Read CSV into DataFrame
df = pd.read_csv(file_path, index_col=0, skiprows=1, parse_dates=True)  # Skip header row with labels
transactions_df = pd.read_csv(transactions_file)

# Convert index to datetime and align formats
df.index = pd.to_datetime(df.index, errors='coerce').to_period('M')
transactions_df['date'] = pd.to_datetime(transactions_df['date'])
transactions_df['month'] = transactions_df['date'].dt.to_period('M')

# Extract Income and Expenses
income_transactions = transactions_df[transactions_df['payee'].str.contains(
    'salary|payroll|direct deposit|transfer : DD Equity Account|Doordash Equity Payout', case=False, na=False)]
monthly_income = income_transactions.groupby(transactions_df['month'])[['amount']].sum()
monthly_income.rename(columns={'amount': 'Income'}, inplace=True)

# Group expenses (negative amounts in transactions, excluding transfers)
expenses_transactions = transactions_df[(transactions_df['amount'] < 0) & ~transactions_df['payee'].str.contains(
    '^transfer', case=False, na=False)]
monthly_expenses = expenses_transactions.groupby(expenses_transactions['month'])[['amount']].sum()
monthly_expenses.rename(columns={'amount': 'Expenses'}, inplace=True)

# Compute Monthly Net Cash Flow
monthly_cash_flow = monthly_income.join(monthly_expenses, how='outer').fillna(0)
monthly_cash_flow['Net Cash Flow'] = monthly_cash_flow['Income'] + monthly_cash_flow['Expenses']

# Debt Tracking
credit_card_accounts = [col for col in df.columns if "Credit Card" in col]
if credit_card_accounts:
    df['Credit Card Total'] = df[credit_card_accounts].apply(pd.to_numeric, errors='coerce').sum(axis=1)
    df['Credit Card Total'].fillna(0, inplace=True)
else:
    df['Credit Card Total'] = 0

debt_trend = df[['Credit Card Total']].copy()
debt_trend['Debt Change'] = debt_trend['Credit Card Total'].diff().fillna(0)

# Identify restaurant and food delivery transactions
restaurant_keywords = ['doordash', 'ubereats', 'grubhub', 'postmates', 'restaurant', 'cafe', 'diner', 'bar', 'bistro', 'food', 'eatery', 'steakhouse', 'grill', 'pizza', 'sushi', 'taco', 'bbq']
restaurant_transactions = transactions_df[transactions_df['payee'].str.contains('|'.join(restaurant_keywords), case=False, na=False)]
monthly_restaurant_spending = restaurant_transactions.groupby(restaurant_transactions['month'])[['amount']].sum()
monthly_restaurant_spending.rename(columns={'amount': 'Restaurant & Dining'}, inplace=True)

# Summarize
summary_df = monthly_cash_flow[['Income', 'Expenses', 'Net Cash Flow']].join(
    debt_trend[['Credit Card Total', 'Debt Change']]
).join(monthly_restaurant_spending, how='outer').fillna(0)

summary_df.to_csv('monthly_financial_summary.csv')

# Format values
def format_currency(value):
    return f"${value:,.2f}"

formatted_summary = summary_df.copy()
formatted_summary[['Income', 'Expenses', 'Net Cash Flow', 'Credit Card Total', 'Debt Change', 'Restaurant & Dining']] = \
    formatted_summary[['Income', 'Expenses', 'Net Cash Flow', 'Credit Card Total', 'Debt Change', 'Restaurant & Dining']].applymap(format_currency)

print(tabulate(formatted_summary, headers='keys', tablefmt='grid'))

# Plot Cash Flow Trends
plt.figure(figsize=(10, 5))
plt.plot(summary_df.index.astype(str), summary_df['Net Cash Flow'], marker='o', linestyle='-', label='Net Cash Flow')
plt.axhline(y=0, color='red', linestyle='--')
plt.xlabel("Month")
plt.ylabel("Amount ($)")
plt.title("Monthly Net Cash Flow")
plt.legend()
plt.grid()
plt.show()

# Plot Restaurant Spending Trends
plt.figure(figsize=(10, 5))
plt.plot(summary_df.index.astype(str), summary_df['Restaurant & Dining'], marker='o', linestyle='-', label='Restaurant & Dining', color='green')
plt.xlabel("Month")
plt.ylabel("Amount ($)")
plt.title("Monthly Restaurant & Dining Spending")
plt.legend()
plt.grid()
plt.show()
