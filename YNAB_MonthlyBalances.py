import ynab
import os
import pandas as pd
from dotenv import load_dotenv
from tabulate import tabulate
from datetime import datetime

# Load environment variables from .env file
load_dotenv()

# Retrieve the API key from environment variables
YNAB_API_KEY = os.getenv("YNAB_API_KEY")

if not YNAB_API_KEY:
    raise ValueError("Please set the YNAB_API_KEY environment variable.")

# Configure the YNAB client
configuration = ynab.Configuration(access_token=YNAB_API_KEY)

# Account classification logic
def classify_account(account_name):
    """Categorizes an account into Saving, Credit Card, or Investment based on its name."""
    if "CC" in account_name or "Visa" in account_name or "RedCard" in account_name or "Bonvoy" in account_name or "Sapphire" in account_name:
        return "Credit Card"
    elif any(keyword in account_name for keyword in ["401(k)", "IRA"]):
        return "Retirement"
    elif any(keyword in account_name for keyword in ["Brokerage","Equity"]):
        return "Investment"
    else:
        return "Saving"

# Initialize the YNAB API client
with ynab.ApiClient(configuration) as api_client:
    budgets_api = ynab.BudgetsApi(api_client)
    transactions_api = ynab.TransactionsApi(api_client)

    try:
        budget_id = '41f3b139-6577-4197-9803-69324d30b3a2'
        budget_response = budgets_api.get_budget_by_id(budget_id)
        budget = budget_response.data.budget
        print(f"Selected Budget: {budget.name}")
    except ynab.ApiException as e:
        print(f"Error retrieving budget: {e}")
        raise

try:
    # Fetch all transactions for the selected budget
    transactions_response = transactions_api.get_transactions(budget_id)
    transactions = transactions_response.data.transactions

    if not transactions:
        print("No transactions found in the selected budget.")
    else:
        # Prepare data for DataFrame
        transaction_data = []
        for transaction in transactions:
            transaction_data.append({
                'date': transaction.var_date,  
                'amount': transaction.amount / 1000,  
                'payee': transaction.payee_name,  
                'category': transaction.category_name,  
                'account': transaction.account_name  
            })

        # Convert to DataFrame
        transactions_df = pd.DataFrame(transaction_data)
        
        # Save raw transactions to CSV
        transactions_df.to_csv('transactions.csv', index=False)
        
        # Ensure date is in datetime format
        transactions_df['date'] = pd.to_datetime(transactions_df['date'])
        transactions_df['month'] = transactions_df['date'].dt.to_period('M')

        # Exclude current month transactions
        current_month = pd.Period(datetime.today().strftime('%Y-%m'), freq='M')
        transactions_df = transactions_df[transactions_df['month'] < current_month]

        # Sum transactions by account and month
        monthly_summary = transactions_df.groupby(['account', 'month'])['amount'].sum().reset_index()

        # Ensure all months are included in the summary (even if no transactions)
        all_months = pd.period_range(start=monthly_summary['month'].min(), end=monthly_summary['month'].max(), freq='M')
        all_accounts = monthly_summary['account'].unique()

        # Create a full DataFrame with all months and accounts
        full_index = pd.MultiIndex.from_product([all_accounts, all_months], names=['account', 'month'])
        monthly_summary = monthly_summary.set_index(['account', 'month']).reindex(full_index, fill_value=0).reset_index()

        # Sort by account and month
        monthly_summary = monthly_summary.sort_values(by=['account', 'month'])

        # Compute Running Balance Correctly
        monthly_summary['running_balance'] = monthly_summary.groupby('account')['amount'].cumsum()

        # Pivot to have accounts as columns and months as rows
        pivot_summary = monthly_summary.pivot(index='month', columns='account', values='running_balance')

        # Ensure consistent formatting
        pivot_summary = pivot_summary.fillna(0).round(2)  # Replace NaNs with 0 and round to 2 decimal places

        # Add Row 2: Account Classification
        classification_row = pd.DataFrame([{
            account: classify_account(account) for account in pivot_summary.columns
        }], index=["Category"])
        
        pivot_summary = pd.concat([classification_row, pivot_summary])

        # Save to CSV
        pivot_summary.to_csv('monthly_summary.csv')

        # Print formatted summary table
        print(tabulate(monthly_summary, headers='keys', tablefmt='grid'))
        print(f"CSV files are saved in: {os.getcwd()}")

except ynab.ApiException as e:
    print(f"Error retrieving transactions: {e}")
    raise
