# OTP Registration Quick Start Guide

## 🚀 Quick Setup

### Step 1: Install Dependencies

**Backend:**
```bash
cd AjileMindApi
pip install PyJWT==2.9.0
```

### Step 2: Configure Environment

Ensure your `.env` file has SMTP settings:

```env
# Email Configuration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_APP_PASSWORD=your-app-password
SMTP_FROM_EMAIL=noreply@agilemind.com
SMTP_FROM_NAME=AgileMind Platform

# Security
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
```

**Frontend:**

Ensure `.env.local` has:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Step 3: Start Services

**Terminal 1 - Backend:**
```bash
cd AjileMindApi
uvicorn main:app --reload --port 8000
```

**Terminal 2 - Frontend:**
```bash
cd AjileMindWeb
npm run dev
```

### Step 4: Test the Flow

1. Open browser: `http://localhost:3000/otp-register`
2. Enter your email address
3. Check your email for the OTP code
4. Enter the 6-digit code
5. Set company name and password
6. You're registered and logged in!

## 📋 Available Routes

### Backend API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/otp/send-otp` | POST | Send OTP to email |
| `/api/v1/otp/verify-otp` | POST | Verify OTP code |
| `/api/v1/otp/complete-registration` | POST | Complete registration |
| `/api/v1/otp/resend-otp` | POST | Resend OTP code |

### Frontend Pages

| Route | Description |
|-------|-------------|
| `/otp-register` | Email entry page |
| `/otp-register/verify` | OTP verification page |
| `/otp-register/complete` | Complete registration page |

## 🧪 Testing with API

### 1. Send OTP
```bash
curl -X POST http://localhost:8000/api/v1/otp/send-otp \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com"}'
```

Response:
```json
{
  "success": true,
  "message": "OTP sent successfully to your email",
  "data": {
    "token": "eyJhbGci...",
    "email": "t***@example.com",
    "expires_in": 300
  }
}
```

### 2. Verify OTP
```bash
curl -X POST http://localhost:8000/api/v1/otp/verify-otp \
  -H "Content-Type: application/json" \
  -d '{
    "token": "YOUR_TOKEN_FROM_STEP_1",
    "otp": "123456"
  }'
```

### 3. Complete Registration
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

## 🎨 UI Features

### Email Entry Page
- Clean, modern design
- Email validation
- Loading states
- Error handling

### OTP Verification Page
- 6-digit input with auto-advance
- Paste support
- Resend with 60s cooldown
- Masked email display
- Timer indication

### Complete Registration Page
- Company name input
- Password strength indicator
- Real-time validation
- Password confirmation

## 🔒 Security Features

✅ Stateless (no OTP in database)  
✅ JWT encryption  
✅ 5-minute OTP expiration  
✅ 15-minute verification token expiration  
✅ Password policy enforcement  
✅ Email masking in UI  

## 📧 Email Template

Users receive a beautifully designed email with:
- Large, prominent OTP code
- 5-minute expiration notice
- Security warnings
- Professional branding

## ⚡ Key Features

1. **No Password Initially** - Users only need email
2. **Fast Verification** - 6-digit code, quick to type
3. **Secure** - JWT-based, stateless design
4. **User-Friendly** - Auto-advance inputs, paste support
5. **Resend Support** - Users can request new codes
6. **Complete Flow** - Three-step wizard

## 🎯 User Journey

```
Step 1: Enter Email
   ↓
Step 2: Receive & Enter OTP (6 digits)
   ↓
Step 3: Set Company Name & Password
   ↓
Done: Auto-login to Dashboard
```

## 🛠️ Files Created

### Backend
- `app/services/otp_service.py` - OTP logic
- `app/schemas/otp_schemas.py` - Request/response models
- `app/api/v1/otp.py` - API endpoints
- `main.py` - Updated with OTP router

### Frontend
- `src/app/otp-register/page.tsx` - Email entry
- `src/app/otp-register/verify/page.tsx` - OTP verification
- `src/app/otp-register/complete/page.tsx` - Complete registration
- `src/app/page.tsx` - Updated with OTP link

## 📚 Documentation

See `OTP_IMPLEMENTATION.md` for complete documentation including:
- Architecture details
- Security features
- API documentation
- Email templates
- Error handling
- Troubleshooting

## 🐛 Common Issues

**Issue:** Email not received  
**Solution:** Check SMTP settings, spam folder, or use a test email service

**Issue:** OTP expired  
**Solution:** Click "Resend Code" to get a new OTP

**Issue:** Invalid token  
**Solution:** Ensure SECRET_KEY matches in .env

**Issue:** CORS error  
**Solution:** Verify NEXT_PUBLIC_API_URL and backend CORS settings

## 💡 Tips

1. Use Gmail App Password for SMTP (not regular password)
2. Test with real email first
3. Check backend logs for OTP codes during development
4. Use incognito/private window for clean testing
5. Clear sessionStorage between tests

## 🎉 Success!

Once set up, users can register in under 2 minutes with just their email!

---

**Need Help?**  
Check logs, review documentation, or contact the development team.
