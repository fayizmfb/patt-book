import re

with open('app.py', 'r') as f:
    content = f.read()
    
# Simple string replacement to remove the problematic line
content = content.replace(
    "            return jsonify({'success': False, 'message': 'Device ID is required'})",
    ""
)

with open('app.py', 'w') as f:
    f.write(content)
    print('Removed duplicate device ID check')
