# Retail App - Core Accounting System

A simple Flask-based accounting system for small retailers to manage customer credits and payments.

## Features

- **Customer Master**: Store customer information (name, phone, address)
- **Credit Entry**: Record credits with automatic due date calculation (5-30 days)
- **Payment Entry**: Record payments with balance validation (prevents negative balances)
- **Overdue Detection**: Identify overdue accounts where balance > 0 and due date < today
- **Ageing Report**: Categorize outstanding balances by age buckets (0-30, 31-60, 61+ days)
- **Customer Ledger**: View complete transaction history for each customer

## Installation

1. **Install Python** (Python 3.7 or higher recommended)

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application**:
   ```bash
   python app.py
   ```

4. **Access the application**:
   Open your browser and navigate to: `http://localhost:5000`

## Usage

### 1. Add Customers
- Click "Add Customer" in the navigation
- Fill in customer details (name is required)
- Submit to add the customer to the master

### 2. Add Credit Entries
- Click "Add Credit" in the navigation
- Select a customer
- Enter the credit amount
- Enter due days (5-30 days)
- The due date will be calculated automatically (entry date + due days)

### 3. Add Payment Entries
- Click "Add Payment" in the navigation
- Select a customer
- Enter the payment amount
- The system will prevent payments exceeding outstanding balance

### 4. View Overdue Entries
- Click "Overdue" in the navigation
- View all credits where balance > 0 and due date < today
- See how many days overdue each entry is

### 5. View Ageing Report
- Click "Ageing Report" in the navigation
- See outstanding balances grouped by age buckets:
  - 0-30 days
  - 31-60 days
  - 61+ days

### 6. View Customer Ledger
- From the customer list, click "Ledger" next to any customer
- View all credit and payment entries
- See total credits, total payments, and outstanding balance

## Database

The application uses SQLite database (`retail_app.db`) which is automatically created on first run.

### Database Schema

- **customers**: Customer master data (id, name, phone, address)
- **credits**: Credit entries (id, customer_id, amount, entry_date, due_days, due_date)
- **payments**: Payment entries (id, customer_id, amount, payment_date)

## Code Structure

```
.
├── app.py              # Main Flask application with all routes
├── database.py         # Database initialization and connection management
├── models.py           # Data models and helper functions
├── requirements.txt    # Python dependencies
├── retail_app.db      # SQLite database (created automatically)
└── templates/         # HTML templates
    ├── base.html
    ├── index.html
    ├── add_customer.html
    ├── view_customer.html
    ├── add_credit.html
    ├── add_payment.html
    ├── overdue.html
    ├── ageing.html
    └── ledger.html
```

## Code Explanation

### app.py - Main Application
Contains all Flask routes and business logic:
- **Customer routes**: List, view, and add customers
- **Credit routes**: Add credit entries with auto-calculated due dates
- **Payment routes**: Add payments with balance validation
- **Overdue route**: Query credits where due_date < today and balance > 0
- **Ageing route**: Group outstanding balances by age buckets
- **Ledger route**: Show all transactions for a customer

### database.py - Database Management
- **init_db()**: Creates database tables if they don't exist
- **get_db()**: Returns a database connection with dictionary-like row access
- Sets up indexes for better query performance

### models.py - Helper Functions
Contains utility functions:
- **calculate_due_date()**: Calculates due date from entry date and due days
- **get_customer_balance()**: Calculates outstanding balance for a customer
- **get_overdue_credits()**: Retrieves overdue credits (alternative implementation)

## Notes

- The application runs in debug mode by default (for development)
- Change `app.secret_key` in production
- Database is automatically initialized on first run
- All amounts are stored as REAL (float) in SQLite
- Dates are stored as DATE type in SQLite

## License

This is a simple educational project. Feel free to use and modify as needed.

