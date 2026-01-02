# Retail App - Core Accounting System

A simple Flask-based accounting system for small retailers to manage customer credits and payments with immediate WhatsApp notifications.

## Features

- **Customer Master**: Store customer information (name, phone, address)
- **Credit Entry**: Record credits with immediate WhatsApp notification to customers
- **Payment Entry**: Record payments with balance validation (prevents negative balances)
- **Debtor Management**: View customers with outstanding balances
- **Customer Ledger**: View complete transaction history for each customer
- **Manual Reminders**: Send follow-up WhatsApp messages from the Debtors section

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

## WhatsApp Configuration

The application integrates with WhatsApp Business API for customer notifications:

1. **Configure API credentials** in Settings:
   - WhatsApp API URL
   - API Key/Token
   - Store name (used in messages)

2. **Message Triggers**:
   - **Credit Entry**: Automatic notification when credit is recorded
   - **Manual Follow-up**: Retailer-initiated from Debtor Details section

3. **Message Content**:
   - Store name and customer greeting
   - Current transaction amount
   - Total outstanding balance
   - Professional, non-spam messaging

## Usage

### 1. Add Customers
- Click "Add Customer" in the navigation
- Fill in customer details (name is required)
- Submit to add the customer to the master

### 2. Add Credit Entries
- Click "Add Credit" in the navigation
- Select a customer
- Enter the credit amount
- The system automatically sends a WhatsApp message to the customer with:
  - Store name
  - Customer name
  - Current purchase amount
  - Total outstanding balance after the entry

### 3. Add Payment Entries
- Click "Add Payment" in the navigation
- Select a customer
- Enter the payment amount
- The system will prevent payments exceeding outstanding balance

### 4. View Debtor Details
- Click "Debtor Details" in the navigation (or from Dashboard)
- View all customers with outstanding balances
- Send manual follow-up WhatsApp reminders using the "Send Message" button

### 5. View Customer Ledger
- From the customer list, click "Ledger" next to any customer
- View all credit and payment entries
- See total credits, total payments, and outstanding balance

## Database

The application uses SQLite database (`retail_app.db`) which is automatically created on first run.

### Database Schema

- **customers**: Customer master data (id, name, phone, address)
- **credits**: Credit entries (id, customer_id, amount, entry_date, due_days*, due_date*)
- **payments**: Payment entries (id, customer_id, amount, payment_date)

*Note: `due_days` and `due_date` columns are maintained for backward compatibility but are no longer used in the simplified workflow.

## Code Structure

```
.
├── app.py              # Main Flask application with all routes
├── database.py         # Database initialization and connection management
├── models.py           # Data models and helper functions
├── whatsapp_helper.py  # WhatsApp API integration functions
├── requirements.txt    # Python dependencies
├── retail_app.db      # SQLite database (created automatically)
└── templates/         # HTML templates
    ├── base.html
    ├── index.html
    ├── add_customer.html
    ├── view_customer.html
    ├── add_credit.html
    ├── add_payment.html
    ├── debtor_details.html
    └── ledger.html
```

## Code Explanation

### app.py - Main Application
Contains all Flask routes and business logic:
- **Customer routes**: List, view, and add customers
- **Credit routes**: Add credit entries with automatic WhatsApp notifications
- **Payment routes**: Add payments with balance validation
- **Debtor routes**: Show customers with outstanding balances and manual reminder functionality
- **Ledger route**: Show all transactions for a customer

### database.py - Database Management
- **init_db()**: Creates database tables if they don't exist
- **get_db()**: Returns a database connection with dictionary-like row access
- Sets up indexes for better query performance

### models.py - Helper Functions
Contains utility functions:
- **get_customer_balance()**: Calculates outstanding balance for a customer

### whatsapp_helper.py - WhatsApp Integration
Contains WhatsApp Business API functions:
- **send_whatsapp_message()**: Sends messages via WhatsApp API
- **prepare_credit_entry_message()**: Creates notification message for new credit entries
- **prepare_manual_reminder_message()**: Creates follow-up reminder messages

## Notes

- The application runs in debug mode by default (for development)
- Change `app.secret_key` in production
- Database is automatically initialized on first run
- All amounts are stored as REAL (float) in SQLite
- Dates are stored as DATE type in SQLite
- WhatsApp notifications are sent only on credit entries and manual follow-ups
- No automatic scheduling or due-date based reminders
- Retailers have full manual control over follow-up messaging

## License

This is a simple educational project. Feel free to use and modify as needed.

