"""
Test script for message template system
Demonstrates usage without WhatsApp API calls
"""

from services.message_templates import (
    generate_message,
    TEMPLATE_DUE,
    TEMPLATE_OUTSTANDING,
    validate_template_data,
    get_available_templates
)

def test_due_reminder():
    """Test due reminder message generation"""
    print("=== Testing Due Reminder ===")
    
    data = {
        "customer_name": "Rahul",
        "shop_name": "Ravi Stores",
        "due_amount": 2350
    }
    
    # Validate data first
    validation = validate_template_data(TEMPLATE_DUE, data)
    print(f"Validation: {validation}")
    
    # Generate message
    msg = generate_message(TEMPLATE_DUE, data)
    print(f"Message:\n{msg}\n")

def test_total_outstanding():
    """Test total outstanding message generation"""
    print("=== Testing Total Outstanding ===")
    
    data = {
        "customer_name": "Rahul",
        "shop_name": "Ravi Stores",
        "total_outstanding": 8420
    }
    
    # Validate data first
    validation = validate_template_data(TEMPLATE_OUTSTANDING, data)
    print(f"Validation: {validation}")
    
    # Generate message
    msg = generate_message(TEMPLATE_OUTSTANDING, data)
    print(f"Message:\n{msg}\n")

def test_error_handling():
    """Test error handling with missing/invalid data"""
    print("=== Testing Error Handling ===")
    
    # Test with missing data
    data = {"customer_name": "Rahul"}  # Missing amount
    validation = validate_template_data(TEMPLATE_DUE, data)
    print(f"Missing amount validation: {validation}")
    
    # Test with invalid amount
    data = {
        "customer_name": "Rahul",
        "shop_name": "Ravi Stores",
        "due_amount": "invalid"  # Not a number
    }
    validation = validate_template_data(TEMPLATE_DUE, data)
    print(f"Invalid amount validation: {validation}")
    
    # Test message generation with defaults
    msg = generate_message(TEMPLATE_DUE, {"customer_name": "Rahul"})
    print(f"Message with defaults:\n{msg}\n")

def test_available_templates():
    """Test listing available templates"""
    print("=== Testing Available Templates ===")
    
    templates = get_available_templates()
    print(f"Available templates: {templates}\n")

if __name__ == "__main__":
    print("Message Template System Test\n")
    
    test_due_reminder()
    test_total_outstanding()
    test_error_handling()
    test_available_templates()
    
    print("All tests completed successfully!")
