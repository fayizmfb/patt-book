from app import app
from flask import url_for
import sqlite3
from datetime import datetime

# Test the debtor_details route
with app.test_request_context():
    from flask import request
    # Simulate GET request to /debtors
    with app.test_client() as client:
        response = client.get('/debtors')
        print(f'Response status: {response.status_code}')
        if response.status_code == 200:
            print('Route is accessible')
            # Check if the response contains expected content
            content = response.get_data(as_text=True)
            if 'Bob Johnson' in content and 'Jane Smith' in content and 'John Doe' in content:
                print('All test customers found in response')
            else:
                print('Some test customers missing from response')
                print('Response preview:', content[:500])
        else:
            print(f'Route error: {response.get_data(as_text=True)}')