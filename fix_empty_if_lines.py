import re

with open('app.py', 'r') as f:
    content = f.read()
    
# Remove the empty if block (lines 522-524)
content = content.replace(
    "        \n        if not device_id:\n        \n        \n        if not device_id:",
        "        if not device_id:"
)

with open('app.py', 'w') as f:
    f.write(content)
    print('Removed empty if block lines')
