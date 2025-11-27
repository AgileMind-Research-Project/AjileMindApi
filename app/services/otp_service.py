"""
OTP Service

Passwordless email OTP verification using PyJWT (stateless).
"""

import random
import jwt
from datetime import datetime, timedelta
from typing import Tuple, Optional
from app.core.config import settings
from app.core.logger import logger
from app.services.email_service import email_service


class OTPService:
    """OTP service for passwordless authentication using JWT"""
    
    def __init__(self):
        self.secret_key = settings.SECRET_KEY
        self.algorithm = settings.ALGORITHM
        self.otp_expiration_minutes = 5  # OTP expires in 5 minutes
    
    def generate_otp(self) -> str:
        """
        Generate a random 6-digit OTP.
        
        Returns:
            6-digit OTP as string
        """
        return str(random.randint(100000, 999999))
    
    def create_otp_token(self, email: str, otp: str) -> str:
        """
        Create JWT token containing OTP, email, and expiration.
        
        Args:
            email: User email address
            otp: 6-digit OTP
        
        Returns:
            JWT token as string
        """
        try:
            expiration = datetime.utcnow() + timedelta(minutes=self.otp_expiration_minutes)
            
            payload = {
                "email": email,
                "otp": otp,
                "exp": expiration,
                "iat": datetime.utcnow(),
                "type": "otp_verification"
            }
            
            token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
            logger.info(f"OTP token created for email: {email}")
            
            return token
            
        except Exception as e:
            logger.error(f"Error creating OTP token for {email}: {e}")
            raise
    
    def verify_otp_token(self, token: str, provided_otp: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Verify JWT token and check if provided OTP matches.
        
        Args:
            token: JWT token containing OTP
            provided_otp: OTP entered by user
        
        Returns:
            Tuple of (is_valid, email, error_message)
            - is_valid: True if OTP is valid and not expired
            - email: User email if valid, None otherwise
            - error_message: Error description if invalid
        """
        try:
            # Decode JWT token
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm]
            )
            
            # Verify token type
            if payload.get("type") != "otp_verification":
                return False, None, "Invalid token type"
            
            # Extract email and OTP from token
            email = payload.get("email")
            stored_otp = payload.get("otp")
            
            if not email or not stored_otp:
                return False, None, "Invalid token payload"
            
            # Verify OTP matches
            if stored_otp != provided_otp:
                logger.warning(f"Invalid OTP attempt for email: {email}")
                return False, None, "Invalid OTP"
            
            logger.info(f"OTP verified successfully for email: {email}")
            return True, email, None
            
        except jwt.ExpiredSignatureError:
            logger.warning(f"Expired OTP token")
            return False, None, "OTP has expired. Please request a new one."
        
        except jwt.InvalidTokenError as e:
            logger.error(f"Invalid OTP token: {e}")
            return False, None, "Invalid or malformed token"
        
        except Exception as e:
            logger.error(f"Error verifying OTP token: {e}")
            return False, None, "An error occurred during verification"
    
    def send_otp_email(self, email: str, otp: str) -> bool:
        """
        Send OTP to user's email address.
        
        Args:
            email: User email address
            otp: 6-digit OTP
        
        Returns:
            True if email sent successfully
        """
        try:
            subject = "🔐 Your AgileMind Verification Code"
            
            # Create HTML email body
            html_body = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <style>
                    body {{
                        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                        line-height: 1.6;
                        color: #333;
                        background-color: #f4f4f4;
                        margin: 0;
                        padding: 0;
                    }}
                    .container {{
                        max-width: 600px;
                        margin: 40px auto;
                        background-color: #ffffff;
                        border-radius: 12px;
                        overflow: hidden;
                        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                    }}
                    .header {{
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        color: #ffffff;
                        text-align: center;
                        padding: 40px 20px;
                    }}
                    .header h1 {{
                        margin: 0;
                        font-size: 28px;
                        font-weight: 600;
                    }}
                    .content {{
                        padding: 40px 30px;
                    }}
                    .otp-box {{
                        background-color: #f8f9fa;
                        border: 2px dashed #667eea;
                        border-radius: 8px;
                        padding: 30px;
                        text-align: center;
                        margin: 30px 0;
                    }}
                    .otp-code {{
                        font-size: 48px;
                        font-weight: bold;
                        color: #667eea;
                        letter-spacing: 8px;
                        margin: 10px 0;
                    }}
                    .message {{
                        color: #666;
                        font-size: 16px;
                        margin: 20px 0;
                    }}
                    .warning {{
                        background-color: #fff3cd;
                        border-left: 4px solid #ffc107;
                        padding: 15px;
                        margin: 20px 0;
                        border-radius: 4px;
                    }}
                    .footer {{
                        background-color: #f8f9fa;
                        text-align: center;
                        padding: 20px;
                        color: #666;
                        font-size: 14px;
                    }}
                    .button {{
                        display: inline-block;
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        color: #ffffff;
                        padding: 12px 30px;
                        text-decoration: none;
                        border-radius: 6px;
                        margin: 20px 0;
                        font-weight: 600;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>🔐 Verification Code</h1>
                    </div>
                    <div class="content">
                        <p class="message">Hello,</p>
                        <p class="message">
                            You requested to sign up or log in to <strong>AgileMind</strong>. 
                            Please use the verification code below to continue:
                        </p>
                        
                        <div class="otp-box">
                            <p style="margin: 0; color: #666; font-size: 14px;">Your verification code is:</p>
                            <div class="otp-code">{otp}</div>
                            <p style="margin: 0; color: #999; font-size: 12px;">Valid for 5 minutes</p>
                        </div>
                        
                        <p class="message">
                            Enter this code in the verification page to complete your authentication.
                        </p>
                        
                        <div class="warning">
                            <strong>⚠️ Security Notice:</strong><br>
                            • This code expires in 5 minutes<br>
                            • Never share this code with anyone<br>
                            • If you didn't request this code, please ignore this email
                        </div>
                        
                        <p class="message" style="color: #999; font-size: 14px;">
                            If you have any questions, please contact our support team.
                        </p>
                    </div>
                    <div class="footer">
                        <p>© 2025 AgileMind. All rights reserved.</p>
                        <p>This is an automated message, please do not reply.</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            # Plain text fallback
            text_body = f"""
            Your AgileMind Verification Code
            
            Your verification code is: {otp}
            
            This code expires in 5 minutes.
            
            Enter this code in the verification page to complete your authentication.
            
            Security Notice:
            - Never share this code with anyone
            - If you didn't request this code, please ignore this email
            
            © 2025 AgileMind. All rights reserved.
            """
            
            return email_service.send_email(email, subject, html_body, text_body)
            
        except Exception as e:
            logger.error(f"Error sending OTP email to {email}: {e}")
            return False


# Global OTP service instance
otp_service = OTPService()
