import pandas as pd
import os
import matplotlib.pyplot as plt
from tabulate import tabulate

# Load the monthly summary data
file_path = 'monthly_summary.csv'
transactions_file = 'transactions.csv'

if not os.path.exists(file_path):
    raise FileNotFoundError("monthly_summary.csv not found. Please generate it first.")
if not os.path.exists(transactions_file):
    raise FileNotFoundError("transactions.csv not found. Please generate it first.")

# Read CSV into DataFrame
df = pd.read_csv(file_path, index_col=0)
transactions_df = pd.read_csv(transactions_file)

# Extract account categories from the first row
account_categories = df.iloc[0]
df = df.iloc[1:].astype(float)  # Convert remaining rows to float for calculations

# Convert index to datetime and filter only December entries for Year-over-Year analysis
df.index = pd.to_datetime(df.index, format='%Y-%m')
df = df[df.index.month == 12]  # Filter December data
df['Year'] = df.index.year  # Extract Year as a column
df.set_index('Year', inplace=True)  # Use Year as Index


# Summarize accounts by category per month
monthly_summary = df.groupby(df.index).sum()
monthly_summary.to_csv('monthly_category_summary.csv')

# Extract direct deposit income from transactions
transactions_df['date'] = pd.to_datetime(transactions_df['date'])
transactions_df['month'] = transactions_df['date'].dt.to_period('M')
income_transactions = transactions_df[transactions_df['payee'].str.contains('salary|payroll|direct deposit|transfer : DD Equity Account|Doordash Equity Payout', case=False, na=False)]
annual_income_df = income_transactions.groupby(income_transactions['date'].dt.to_period('Y'))[['amount']].sum()
annual_income_df.rename(columns={'amount': 'Income'}, inplace=True)
annual_income_df.index.name = 'Year' #Rename index column to year
annual_income_df.index = annual_income_df.index.astype(str).astype(int) #Convert to year-integer


print(annual_income_df.head())  # Ensure correct names: 'Year' index & 'Income' column



# Group accounts into categories
credit_cards = df.loc[:, account_categories[account_categories == "Credit Card"].index]
free_cash_flow = df.loc[:, account_categories[account_categories == "Saving"].index]
investments = df.loc[:, account_categories[account_categories == "Investment"].index]
retirement = df.loc[:, account_categories[account_categories == "Retirement"].index]

# Compute December Year-End Balances
df['Credit Card Total'] = credit_cards.sum(axis=1)
df['Free Cash Flow'] = free_cash_flow.sum(axis=1)
df['Investment Total'] = investments.sum(axis=1)
df['Retirement Total'] = retirement.sum(axis=1)

# Compute Year-over-Year Changes
df_change = df.diff()

# Compute Financial Ratios for Each Year
financial_ratios = []
for year in df.index:
    totals = df.loc[year]
    previous_year = year - 1 if year - 1 in df.index else None
    previous_totals = df.loc[previous_year] if previous_year else None

    total_debt = abs(totals['Credit Card Total'])
    total_liquid_assets = totals['Free Cash Flow']
    total_investments = totals['Investment Total']
    total_retirement = totals['Retirement Total']

    debt_ratio = total_debt / (total_liquid_assets + total_investments + total_retirement) if total_liquid_assets + total_investments + total_retirement > 0 else 0
    liquidity_ratio = total_liquid_assets / total_debt if total_debt > 0 else float('inf')
    net_worth = total_liquid_assets + total_investments + total_retirement - total_debt

    # Retirement Savings % calculation (YoY Change in Retirement Savings / Annual Income)
    retirement_savings_yoy_change = df_change.loc[year, 'Retirement Total'] if year in df_change.index else 0
    annual_income = annual_income_df['Income'].get(year, 0)

    retirement_savings_ratio = retirement_savings_yoy_change / annual_income if annual_income > 0 else 0

    annual_savings_ratio = (total_investments + total_retirement) / annual_income if annual_income > 0 else 0

    financial_ratios.append({
        "Year": year,
        "Debt Ratio": debt_ratio,
        "Liquidity Ratio": liquidity_ratio,
        "Net Worth": net_worth,
        "Retirement Savings %": retirement_savings_ratio,
        "Annual Savings % vs Income": annual_savings_ratio,
        "Total Debt": -total_debt,
        "Total Liquid Asset": total_liquid_assets,
        "Total Investment": total_investments,
        "Total Retirement": total_retirement,
    })

# Convert to DataFrame and Save
financial_ratios_df = pd.DataFrame(financial_ratios)
financial_ratios_df.set_index("Year", inplace=True)

financial_ratios_df = financial_ratios_df.merge(annual_income_df, left_index=True, right_index=True, how="left")

print(financial_ratios_df.head())  # Ensure correct names: 'Year' index & 'Income' column

financial_ratios_df['Income'].fillna(0, inplace=True)  # Ensure missing values are filled with zero

financial_ratios_df.to_csv('annual_summary.csv')
print(f"CSV files are saved in: {os.getcwd()}")

# Format values
def format_currency(value):
    return f"${value:,.2f}"

def format_percentage(value):
    return f"{value * 100:.2f}%"  # Convert ratio to percentage

# Apply formatting
formatted_summary = financial_ratios_df.copy()
formatted_summary[['Debt Ratio', 'Liquidity Ratio', 'Retirement Savings %', 'Annual Savings % vs Income']] = \
    formatted_summary[['Debt Ratio', 'Liquidity Ratio', 'Retirement Savings %', 'Annual Savings % vs Income']].applymap(format_percentage)

formatted_summary[['Net Worth', 'Total Debt', 'Total Liquid Asset', 'Total Investment', 'Total Retirement', 'Income']] = \
    formatted_summary[['Net Worth', 'Total Debt', 'Total Liquid Asset', 'Total Investment', 'Total Retirement', 'Income']].applymap(format_currency)

# Print formatted table
print(tabulate(formatted_summary, headers='keys', tablefmt='grid'))

# Create figure and bar chart
fig, ax1 = plt.subplots(figsize=(10, 6))

# Plot stacked bar chart for assets and debt
financial_ratios_df[['Total Debt', 'Total Liquid Asset', 'Total Investment', 'Total Retirement']].plot(
    kind='bar', stacked=True, ax=ax1, width=0.8, color=['#FF9999', '#99CCFF', '#66CC66', '#FFD700']
)

# Customize primary Y-axis
ax1.set_xlabel("Year")
ax1.set_ylabel("Amount ($)")
ax1.set_title("Annual Financial Overview")
ax1.legend(loc='upper left')
ax1.grid(axis='y', linestyle='--', alpha=0.7)

# Create secondary Y-axis for income
ax2 = ax1.twinx()
ax2.plot(financial_ratios_df.index, financial_ratios_df['Income'], marker='o', linestyle='-', color='black', linewidth=2, label="Income")

# Customize secondary Y-axis
ax2.set_ylabel("Annual Income ($)")
ax2.legend(loc='upper right')

# Show the plot
plt.show()
print(annual_income_df)

#print(income_transactions[['date', 'amount']].groupby(income_transactions['date'].dt.to_period('Y')).sum())
