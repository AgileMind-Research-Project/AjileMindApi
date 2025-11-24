# OTP-Based Passwordless Registration Implementation

## Overview

This implementation provides a secure, stateless, passwordless registration system using email OTP (One-Time Password) verification with PyJWT. Users can register without entering a password initially, receiving a 6-digit OTP via email to verify their identity.

## Features

✅ **Stateless OTP Verification** - No database storage of OTP codes  
✅ **JWT-Based Token Management** - All data encrypted in JWT tokens  
✅ **6-Digit OTP Generation** - Random, secure OTP codes  
✅ **Email Delivery** - Beautiful HTML email templates  
✅ **5-Minute Expiration** - OTP expires after 5 minutes  
✅ **Resend Functionality** - Users can request new OTP codes  
✅ **Password Setup After Verification** - Users set password after email verification  
✅ **Complete Frontend Flow** - Three-step registration wizard  

## Architecture

### Backend Components

#### 1. OTP Service (`app/services/otp_service.py`)
- **OTP Generation**: Generates random 6-digit codes
- **JWT Token Creation**: Encodes OTP with email and expiration
- **OTP Verification**: Decodes and validates JWT tokens
- **Email Sending**: Sends beautifully formatted OTP emails

Key Methods:
```python
generate_otp() -> str
create_otp_token(email: str, otp: str) -> str
verify_otp_token(token: str, provided_otp: str) -> Tuple[bool, Optional[str], Optional[str]]
send_otp_email(email: str, otp: str) -> bool
```

#### 2. OTP Schemas (`app/schemas/otp_schemas.py`)
- `SendOTPRequest` - Email input
- `SendOTPResponse` - Token and masked email
- `VerifyOTPRequest` - Token and OTP code
- `VerifyOTPResponse` - Verification token
- `CompleteRegistrationRequest` - Company name and password
- `CompleteRegistrationResponse` - User and tenant data

#### 3. OTP API Routes (`app/api/v1/otp.py`)
- `POST /api/v1/otp/send-otp` - Send OTP to email
- `POST /api/v1/otp/verify-otp` - Verify OTP code
- `POST /api/v1/otp/complete-registration` - Complete registration with password
- `POST /api/v1/otp/resend-otp` - Resend OTP code

### Frontend Components

#### 1. Email Entry Page (`src/app/otp-register/page.tsx`)
- Email input form
- Email validation
- API integration to send OTP
- Navigation to verification page

#### 2. OTP Verification Page (`src/app/otp-register/verify/page.tsx`)
- 6-digit OTP input (auto-focus, auto-advance)
- Paste support for OTP codes
- Resend OTP functionality with cooldown
- Masked email display
- Timer indication (5 minutes)

#### 3. Complete Registration Page (`src/app/otp-register/complete/page.tsx`)
- Company name input
- Password creation with validation
- Password confirmation
- Real-time password strength indicator
- Account creation and auto-login

## User Flow

```
1. User enters email address
   ↓
2. System sends 6-digit OTP to email
   ↓
3. User receives email with OTP code
   ↓
4. User enters OTP code
   ↓
5. System verifies OTP (JWT validation)
   ↓
6. User enters company name and password
   ↓
7. System creates tenant and user account
   ↓
8. User is automatically logged in
```

## Security Features

### 1. Stateless Design
- No OTP storage in database
- All data encrypted in JWT tokens
- Reduces attack surface

### 2. Token Expiration
- OTP tokens expire after 5 minutes
- Verification tokens expire after 15 minutes
- Prevents replay attacks

### 3. JWT Encryption
- Uses HS256 algorithm
- Secret key from environment variables
- Token type verification

### 4. Password Policy
- Minimum 8 characters
- Requires uppercase letter
- Requires lowercase letter
- Requires number
- Requires special character

### 5. Email Masking
- Displays masked email (e.g., u***@example.com)
- Protects privacy in UI

## API Documentation

### 1. Send OTP

**Endpoint:** `POST /api/v1/otp/send-otp`

**Request Body:**
```json
{
  "email": "user@example.com"
}
```

**Response:**
```json
{
  "success": true,
  "message": "OTP sent successfully to your email",
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "email": "u***@example.com",
    "expires_in": 300
  }
}
```

### 2. Verify OTP

**Endpoint:** `POST /api/v1/otp/verify-otp`

**Request Body:**
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "otp": "123456"
}
```

**Response:**
```json
{
  "success": true,
  "message": "OTP verified successfully",
  "data": {
    "verification_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "email": "user@example.com"
  }
}
```

### 3. Complete Registration

**Endpoint:** `POST /api/v1/otp/complete-registration`

**Request Body:**
```json
{
  "verification_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "company_name": "Acme Corporation",
  "password": "SecurePass123!",
  "password_confirmation": "SecurePass123!"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Registration completed successfully. Welcome to AgileMind!",
  "data": {
    "tenant_id": "tn-123456",
    "company_name": "Acme Corporation",
    "user": {
      "user_id": "usr-123456",
      "email": "user@example.com",
      "role": "SUPER_ADMIN"
    },
    "tokens": {
      "access_token": "...",
      "refresh_token": "..."
    }
  }
}
```

### 4. Resend OTP

**Endpoint:** `POST /api/v1/otp/resend-otp`

**Request Body:**
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response:**
```json
{
  "success": true,
  "message": "OTP resent successfully to your email",
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "email": "u***@example.com",
    "expires_in": 300
  }
}
```

## Email Template

The OTP email includes:
- Professional gradient design
- Large, prominent OTP code
- Expiration notice (5 minutes)
- Security warnings
- Responsive design
- Plain text fallback

## Installation & Setup

### Backend

1. **Install PyJWT:**
```bash
pip install PyJWT==2.9.0
```

2. **Ensure SMTP Configuration in `.env`:**
```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_APP_PASSWORD=your-app-password
SMTP_FROM_EMAIL=noreply@agilemind.com
SMTP_FROM_NAME=AgileMind Platform
```

3. **The OTP router is already registered in `main.py`**

### Frontend

1. **Ensure API URL in `.env.local`:**
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

2. **All components are created in:**
   - `/otp-register/page.tsx` - Email entry
   - `/otp-register/verify/page.tsx` - OTP verification
   - `/otp-register/complete/page.tsx` - Complete registration

## Testing

### Manual Testing

1. **Start Backend:**
```bash
cd AjileMindApi
uvicorn main:app --reload
```

2. **Start Frontend:**
```bash
cd AjileMindWeb
npm run dev
```

3. **Test Flow:**
   - Navigate to `http://localhost:3000/otp-register`
   - Enter email address
   - Check email for OTP code
   - Enter OTP code
   - Set company name and password
   - Verify account creation

### API Testing with cURL

**1. Send OTP:**
```bash
curl -X POST http://localhost:8000/api/v1/otp/send-otp \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com"}'
```

**2. Verify OTP:**
```bash
curl -X POST http://localhost:8000/api/v1/otp/verify-otp \
  -H "Content-Type: application/json" \
  -d '{"token": "YOUR_TOKEN", "otp": "123456"}'
```

**3. Complete Registration:**
```bash
curl -X POST http://localhost:8000/api/v1/otp/complete-registration \
  -H "Content-Type: application/json" \
  -d '{
    "verification_token": "YOUR_VERIFICATION_TOKEN",
    "company_name": "Test Company",
    "password": "Test123!@#",
    "password_confirmation": "Test123!@#"
  }'
```

## Error Handling

### Common Error Responses

**1. Invalid Email:**
```json
{
  "success": false,
  "message": "Invalid email format"
}
```

**2. Expired OTP:**
```json
{
  "success": false,
  "message": "OTP has expired. Please request a new one."
}
```

**3. Invalid OTP:**
```json
{
  "success": false,
  "message": "Invalid OTP"
}
```

**4. Weak Password:**
```json
{
  "success": false,
  "message": "Password must contain at least 8 characters, one uppercase letter, one lowercase letter, one number, and one special character"
}
```

## Best Practices

1. **Always use HTTPS in production**
2. **Configure proper SMTP settings**
3. **Monitor email delivery rates**
4. **Implement rate limiting for OTP requests**
5. **Log OTP attempts for security auditing**
6. **Use environment variables for sensitive data**
7. **Implement CAPTCHA for production**

## Future Enhancements

- [ ] Rate limiting per email address
- [ ] SMS OTP as alternative
- [ ] Biometric authentication
- [ ] OAuth integration (Google, Microsoft)
- [ ] Remember device functionality
- [ ] OTP attempt tracking
- [ ] Admin dashboard for OTP analytics

## Troubleshooting

### OTP Email Not Received
1. Check SMTP configuration
2. Verify email server allows sending
3. Check spam/junk folder
4. Verify sender email is not blacklisted

### Token Errors
1. Ensure SECRET_KEY is set correctly
2. Check token expiration times
3. Verify JWT algorithm matches

### Frontend API Errors
1. Verify NEXT_PUBLIC_API_URL is correct
2. Check CORS configuration
3. Ensure backend is running

## License

This implementation is part of the AgileMind Platform and follows the project's licensing terms.

---

**Implementation Date:** November 23, 2025  
**Version:** 1.0.0  
**Author:** AgileMind Development Team
