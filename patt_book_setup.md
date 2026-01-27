# Patt Book API - Complete Setup

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r patt_book_requirements.txt
```

### 2. Run the API Server
```bash
python patt_book_api_complete.py
```

### 3. Test the API
The server will start on: http://localhost:5000

## 📱 API Endpoints

### Send OTP
```
POST http://localhost:5000/api/auth/send-otp
Content-Type: application/json

{
  "mobile_number": "1234567890"
}
```

### Verify OTP
```
POST http://localhost:5000/api/auth/verify-otp
Content-Type: application/json

{
  "mobile_number": "1234567890",
  "otp": "242324",
  "user_type": "retailer"
}
```

### Create Account (Retailer)
```
POST http://localhost:5000/api/auth/create-account
Content-Type: application/json

{
  "mobile_number": "1234567890",
  "user_type": "retailer",
  "shop_name": "My Shop",
  "shop_address": "123 Main St",
  "shop_photo_url": "https://example.com/photo.jpg",
  "latitude": 19.0760,
  "longitude": 72.8777
}
```

### Create Account (Customer)
```
POST http://localhost:5000/api/auth/create-account
Content-Type: application/json

{
  "mobile_number": "1234567890",
  "user_type": "customer",
  "customer_name": "John Doe"
}
```

## 🔑 Default OTP
**242324** (hardcoded for testing)

## 📊 Database
- Automatically creates `patt_book.db` SQLite database
- Tables: users, customers, transactions, otp_requests, sessions, reminders

## 🌐 Mobile App Configuration
Update your mobile app API config to:
```
http://localhost:5000/api
```

## ✅ Features
- ✅ Role-based authentication (Retailer/Customer)
- ✅ OTP verification system
- ✅ JWT token management
- ✅ SQLite database
- ✅ Error handling
- ✅ Ready for mobile app integration
