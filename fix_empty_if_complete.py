import re

with open('app.py', 'r') as f:
    content = f.read()
    
# Remove the empty if block completely
content = content.replace(
    "        if not device_id:\n        \n        \n        if not device_id:",
    "        if not device_id:"
)

with open('app.py', 'w') as f:
    f.write(content)
    print('Fixed empty if block completely')
