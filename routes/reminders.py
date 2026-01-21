"""
Reminder Routes - API endpoints for message previews
No WhatsApp API calls - pure template rendering only
"""

from flask import Blueprint, request, jsonify
from services.message_templates import (
    generate_message, 
    TEMPLATE_DUE, 
    TEMPLATE_OUTSTANDING,
    validate_template_data
)

reminders_bp = Blueprint('reminders', __name__, url_prefix='/api/reminders')

@reminders_bp.route('/preview', methods=['POST'])
def preview_message():
    """
    Generate message preview without sending
    Safe for development/testing
    """
    try:
        data = request.get_json()
        
        # Validate required fields
        template_type = data.get('template_type')
        message_data = data.get('data', {})
        
        if not template_type:
            return jsonify({
                'success': False,
                'message': 'template_type is required'
            }), 400
        
        # Validate template data
        validation = validate_template_data(template_type, message_data)
        if not validation['valid']:
            return jsonify({
                'success': False,
                'message': 'Validation failed',
                'errors': validation['errors']
            }), 400
        
        # Generate message
        message = generate_message(template_type, message_data)
        
        return jsonify({
            'success': True,
            'message': 'Message preview generated',
            'data': {
                'template_type': template_type,
                'message_text': message,
                'preview_mode': True
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error generating preview: {str(e)}'
        }), 500

@reminders_bp.route('/templates', methods=['GET'])
def list_templates():
    """
    Get available message templates
    """
    try:
        from services.message_templates import get_available_templates
        
        templates = get_available_templates()
        
        return jsonify({
            'success': True,
            'data': {
                'templates': templates,
                'count': len(templates)
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error fetching templates: {str(e)}'
        }), 500

@reminders_bp.route('/validate', methods=['POST'])
def validate_template():
    """
    Validate template data without generating message
    """
    try:
        data = request.get_json()
        
        template_type = data.get('template_type')
        message_data = data.get('data', {})
        
        if not template_type:
            return jsonify({
                'success': False,
                'message': 'template_type is required'
            }), 400
        
        validation = validate_template_data(template_type, message_data)
        
        return jsonify({
            'success': True,
            'data': {
                'template_type': template_type,
                'valid': validation['valid'],
                'errors': validation['errors']
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error validating template: {str(e)}'
        }), 500
