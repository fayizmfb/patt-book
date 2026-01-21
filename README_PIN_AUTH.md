# PIN Authentication System for Patt Book v1

## Overview
Secure phone number + PIN authentication system that works without WhatsApp OTP dependency. Ready for immediate release with zero WhatsApp costs.

## Architecture

```
services/
 └── pin_auth.py           # PIN validation & security logic
database.py                # Updated with PIN storage functions
routes/
 └── pin_auth.py          # API endpoints for PIN authentication
```

## Authentication Flow

### 1️⃣ New User Setup
```
POST /api/auth/check-phone
→ Returns: user_exists: false, requires_setup: true

POST /api/auth/setup-account
→ Creates retailer with hashed PIN
→ Returns: success, token, device_id
```

### 2️⃣ Returning User Login
```
POST /api/auth/check-phone
→ Returns: user_exists: true, requires_pin: true

POST /api/auth/login
→ Verifies PIN against hash
→ Creates session with device tracking
→ Returns: success, token, retailer info
```

## Security Features

### ✅ PIN Storage
- **Hashed Storage**: PINs are hashed using `werkzeug.security.generate_password_hash()`
- **No Plain Text**: PINs never stored in plain text
- **Secure Verification**: `check_password_hash()` for verification

### ✅ Rate Limiting
- **Max Attempts**: 5 wrong PIN attempts
- **Lock Duration**: 15 minutes after limit reached
- **Attempt Tracking**: Per-phone attempt counting
- **Auto Reset**: Attempts reset on successful login

### ✅ Session + Device Control
- **Device Tracking**: Each login associated with device_id
- **One Device One Session**: New login invalidates old sessions
- **JWT Tokens**: Secure token-based authentication
- **Audit Logging**: All login attempts logged

## API Endpoints

### POST /api/auth/check-phone
Check if phone number exists and determine next step.

**Request:**
```json
{
    "phone": "9876543210"
}
```

**Response (New User):**
```json
{
    "success": true,
    "message": "New phone number. Please create your account.",
    "user_exists": false,
    "requires_setup": true
}
```

**Response (Existing User):**
```json
{
    "success": true,
    "message": "Phone number found. Please enter your PIN.",
    "user_exists": true,
    "requires_pin": true,
    "attempts_remaining": 5
}
```

### POST /api/auth/setup-account
Create new account with PIN.

**Request:**
```json
{
    "phone": "9876543210",
    "shop_name": "Test Store",
    "shop_address": "123 Test Street",
    "pin": "1234",
    "confirm_pin": "1234"
}
```

**Response:**
```json
{
    "success": true,
    "message": "Account created successfully!",
    "retailer": {
        "id": 1,
        "phone": "9876543210",
        "shop_name": "Test Store",
        "shop_address": "123 Test Street"
    },
    "token": "eyJ...",
    "device_id": "uuid-string"
}
```

### POST /api/auth/login
Login with phone number and PIN.

**Request:**
```json
{
    "phone": "9876543210",
    "pin": "1234"
}
```

**Response (Success):**
```json
{
    "success": true,
    "message": "Login successful!",
    "retailer": {
        "id": 1,
        "phone": "9876543210",
        "shop_name": "Test Store",
        "shop_address": "123 Test Street"
    },
    "token": "eyJ...",
    "device_id": "uuid-string"
}
```

**Response (Wrong PIN):**
```json
{
    "success": false,
    "message": "Invalid PIN",
    "attempts_remaining": 4
}
```

**Response (Account Locked):**
```json
{
    "success": false,
    "message": "Account locked due to too many failed attempts. Try again in 15 minutes.",
    "locked": true,
    "lock_time_remaining": 15
}
```

## Database Schema

### Retailers Table (Updated)
```sql
CREATE TABLE retailers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    phone TEXT UNIQUE NOT NULL,
    shop_name TEXT NOT NULL,
    shop_address TEXT NOT NULL,
    shop_photo_url TEXT,
    pin_hash TEXT,              -- NEW: Hashed PIN storage
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Error Handling

### Validation Errors
- **Phone**: "Valid 10-digit phone number required"
- **PIN**: "PIN must be 4-6 digits"
- **Shop Name**: "Shop name must be at least 2 characters"
- **Shop Address**: "Shop address must be at least 5 characters"

### Authentication Errors
- **User Not Found**: "User not found"
- **Invalid PIN**: "Invalid PIN"
- **Account Locked**: "Account locked due to too many failed attempts"
- **PIN Mismatch**: "PIN confirmation does not match"

## Testing

Run the test script to verify all functionality:

```bash
# Start the Flask app first
python app.py

# In another terminal, run tests
python test_pin_auth.py
```

**Test Coverage:**
- ✅ New user phone check
- ✅ Account setup with PIN
- ✅ Existing user login
- ✅ Wrong PIN handling
- ✅ Rate limiting (5 attempts + lock)
- ✅ Invalid phone validation
- ✅ Non-existent user handling
- ✅ Complete authentication flow

## Security Considerations

### ✅ Implemented
- PIN hashing with werkzeug
- Rate limiting with lockout
- Device-based session control
- Audit logging for compliance
- Input validation and sanitization

### 🔒 Future Enhancements
- PIN change functionality
- Admin PIN reset interface
- WhatsApp/email OTP recovery (v2)
- Session timeout management
- Multi-factor authentication option

## Migration from OTP

When WhatsApp OTP becomes available:
1. Keep PIN system as backup
2. Add OTP as optional recovery method
3. Implement hybrid authentication
4. No breaking changes to existing users

## Production Deployment

### Environment Variables
```bash
JWT_SECRET=your-production-secret-key
TEST_MODE=false
```

### Database
- SQLite database automatically initialized
- PIN hashes stored securely
- Audit logs for compliance

### Security Checklist
- ✅ PINs are hashed, never plain text
- ✅ Rate limiting prevents brute force
- ✅ Device tracking prevents session hijacking
- ✅ JWT tokens with expiration
- ✅ All inputs validated
- ✅ Error messages don't leak information

## Admin PIN Reset

For v1, PIN reset requires database access:

```sql
-- Update PIN hash for retailer
UPDATE retailers SET pin_hash = 'new-hash' WHERE phone = '9876543210';
```

Future versions will include admin interface for PIN resets.
