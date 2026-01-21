"""
Message Template System for Patt Book
Pure functions - no API calls, no DB writes
Safe for preview mode, ready for WhatsApp later
"""

# Template type constants
TEMPLATE_DUE = "DUE_REMINDER"
TEMPLATE_OUTSTANDING = "TOTAL_OUTSTANDING"

def generate_message(template_type, data):
    """
    Generate message text based on template type and data
    
    Args:
        template_type (str): Template type constant (TEMPLATE_DUE or TEMPLATE_OUTSTANDING)
        data (dict): Data dictionary containing customer and amount information
        
    Returns:
        str: Formatted message text
    """
    # Safe data extraction with defaults
    customer = data.get("customer_name", "Customer")
    shop = data.get("shop_name", "our store")
    
    if template_type == TEMPLATE_DUE:
        amount = data.get("due_amount", 0)
        # Ensure amount is numeric
        try:
            amount = float(amount)
        except (ValueError, TypeError):
            amount = 0
        
        return (
            f"Hi {customer},\n"
            f"Your due amount at {shop} is Rs{amount:.2f}.\n\n"
            f"View full details in Patt Book app."
        )
    
    elif template_type == TEMPLATE_OUTSTANDING:
        amount = data.get("total_outstanding", 0)
        # Ensure amount is numeric
        try:
            amount = float(amount)
        except (ValueError, TypeError):
            amount = 0
        
        return (
            f"Hi {customer},\n"
            f"Your total outstanding amount at {shop} is Rs{amount:.2f}.\n\n"
            f"View full history in Patt Book app."
        )
    
    # Fallback for invalid template types
    return "Invalid message type"

def get_available_templates():
    """
    Get list of available template types
    
    Returns:
        list: List of template type constants
    """
    return [TEMPLATE_DUE, TEMPLATE_OUTSTANDING]

def validate_template_data(template_type, data):
    """
    Validate data for a specific template type
    
    Args:
        template_type (str): Template type to validate
        data (dict): Data to validate
        
    Returns:
        dict: Validation result with 'valid' boolean and 'errors' list
    """
    errors = []
    
    if not isinstance(data, dict):
        errors.append("Data must be a dictionary")
        return {"valid": False, "errors": errors}
    
    # Check required fields
    if template_type == TEMPLATE_DUE:
        if "due_amount" not in data:
            errors.append("Missing required field: due_amount")
        else:
            try:
                float(data["due_amount"])
            except (ValueError, TypeError):
                errors.append("due_amount must be a valid number")
    
    elif template_type == TEMPLATE_OUTSTANDING:
        if "total_outstanding" not in data:
            errors.append("Missing required field: total_outstanding")
        else:
            try:
                float(data["total_outstanding"])
            except (ValueError, TypeError):
                errors.append("total_outstanding must be a valid number")
    
    else:
        errors.append(f"Unknown template type: {template_type}")
    
    return {"valid": len(errors) == 0, "errors": errors}
