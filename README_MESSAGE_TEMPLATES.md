# Message Template System

## Overview
Pure message template system for Patt Book - no API calls, no database writes. Safe for preview mode and ready for WhatsApp integration later.

## Architecture

```
services/
 └── message_templates.py    # Pure template functions
routes/
 └── reminders.py          # API endpoints for previews
```

## Template Types

### DUE_REMINDER
Notifies customer about a specific due amount.

**Required fields:**
- `customer_name` (string)
- `shop_name` (string) 
- `due_amount` (number)

**Example:**
```python
data = {
    "customer_name": "Rahul",
    "shop_name": "Ravi Stores", 
    "due_amount": 2350
}
msg = generate_message(TEMPLATE_DUE, data)
```

### TOTAL_OUTSTANDING
Notifies customer about total outstanding amount.

**Required fields:**
- `customer_name` (string)
- `shop_name` (string)
- `total_outstanding` (number)

**Example:**
```python
data = {
    "customer_name": "Rahul",
    "shop_name": "Ravi Stores",
    "total_outstanding": 8420
}
msg = generate_message(TEMPLATE_OUTSTANDING, data)
```

## API Endpoints

### POST /api/reminders/preview
Generate message preview without sending.

**Request:**
```json
{
    "template_type": "DUE_REMINDER",
    "data": {
        "customer_name": "Rahul",
        "shop_name": "Ravi Stores",
        "due_amount": 2350
    }
}
```

**Response:**
```json
{
    "success": true,
    "message": "Message preview generated",
    "data": {
        "template_type": "DUE_REMINDER",
        "message_text": "Hi Rahul,\nYour due amount at Ravi Stores is Rs2350.00.\n\nView full details in Patt Book app.",
        "preview_mode": true
    }
}
```

### GET /api/reminders/templates
List available template types.

### POST /api/reminders/validate
Validate template data without generating message.

## Safety Features

✅ **Pure Functions** - No side effects, no API calls
✅ **Error-Safe** - Default values for missing fields
✅ **Type Validation** - Numeric validation for amounts
✅ **Preview Mode** - Safe for development/testing
✅ **WhatsApp Ready** - Easy switch to live mode later

## Usage Examples

```python
from services.message_templates import generate_message, TEMPLATE_DUE

# Generate due reminder
data = {"customer_name": "Rahul", "shop_name": "Ravi Stores", "due_amount": 2350}
msg = generate_message(TEMPLATE_DUE, data)

# Generate with defaults (missing fields get safe defaults)
msg = generate_message(TEMPLATE_DUE, {"customer_name": "Rahul"})
```

## Testing

Run the test script to verify functionality:

```bash
python test_message_templates.py
```

## Future WhatsApp Integration

When ready to switch to live WhatsApp:

1. Add WhatsApp API calls in routes (not in templates)
2. Keep template functions pure
3. Add environment variable for preview/live mode
4. No template code changes needed
