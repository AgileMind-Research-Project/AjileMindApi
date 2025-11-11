"""
Email Service

Send emails using SMTP (Gmail) with HTML templates.
"""

import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional, Dict, Any
from app.core.config import settings
from app.core.logger import logger


class EmailService:
    """Email service for sending emails via SMTP with template support"""
    
    def __init__(self):
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_user = settings.SMTP_USER
        self.smtp_password = settings.SMTP_APP_PASSWORD
        self.from_email = settings.SMTP_FROM_EMAIL
        self.from_name = settings.SMTP_FROM_NAME
        self.template_dir = os.path.join(os.path.dirname(__file__), 'email_templates')
    
    def _load_template(self, template_name: str, variables: Dict[str, Any]) -> str:
        """
        Load HTML template from file and replace variables.
        
        Args:
            template_name: Name of template file (e.g., 'tenant_welcome.html')
            variables: Dictionary of variables to replace in template
        
        Returns:
            HTML string with variables replaced
        """
        try:
            template_path = os.path.join(self.template_dir, template_name)
            
            with open(template_path, 'r', encoding='utf-8') as file:
                template_content = file.read()
            
            # Replace all variables in template
            for key, value in variables.items():
                placeholder = f"{{{{{key}}}}}"  # {{variable_name}}
                template_content = template_content.replace(placeholder, str(value))
            
            return template_content
            
        except FileNotFoundError:
            logger.error(f"Email template not found: {template_name}")
            raise
        except Exception as e:
            logger.error(f"Error loading email template {template_name}: {e}")
            raise
    
    def send_email(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: Optional[str] = None
    ) -> bool:
        """
        Send email via SMTP.
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            html_body: HTML email body
            text_body: Plain text email body (fallback)
        
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = to_email
            msg['Subject'] = subject
            
            # Add text part if provided
            if text_body:
                part1 = MIMEText(text_body, 'plain')
                msg.attach(part1)
            
            # Add HTML part
            part2 = MIMEText(html_body, 'html')
            msg.attach(part2)
            
            # Connect to SMTP server and send
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()  # Secure the connection
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
            
            logger.info(f"Email sent successfully to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False
    
    def send_tenant_welcome_email(
        self,
        email: str,
        company_name: str,
        tenant_id: str
    ) -> bool:
        """
        Send welcome email to new tenant super admin using template.
        
        Args:
            email: Admin email
            company_name: Company name
            tenant_id: Tenant ID
        
        Returns:
            True if sent successfully
        """
        subject = f"🎉 Welcome to AgileMind - Your Account is Ready, {company_name}!"
        
        # Prepare template variables
        variables = {
            'company_name': company_name,
            'email': email,
            'tenant_id': tenant_id,
            'login_url': f"{settings.AGILEMIND_PLATFORM_URL}/login"
        }
        
        # Load and render template
        html_body = self._load_template('tenant_welcome.html', variables)
        
        return self.send_email(email, subject, html_body)
    
    def send_user_welcome_email(
        self,
        email: str,
        first_name: str,
        last_name: str,
        company_name: str,
        role: str,
        temporary_password: str
    ) -> bool:
        """
        Send welcome email to new user with login credentials using template.
        
        Args:
            email: User email
            first_name: User first name
            last_name: User last name
            company_name: Company name
            role: User role
            temporary_password: Temporary password
        
        Returns:
            True if sent successfully
        """
        subject = f"🎊 Welcome to {company_name} on AgileMind!"
        
        # Prepare template variables
        variables = {
            'first_name': first_name,
            'last_name': last_name,
            'email': email,
            'company_name': company_name,
            'role': role,
            'temporary_password': temporary_password,
            'login_url': f"{settings.AGILEMIND_PLATFORM_URL}/login"
        }
        
        # Load and render template
        html_body = self._load_template('user_welcome.html', variables)
        
        return self.send_email(email, subject, html_body)
    
    def send_password_reset_email(
        self,
        email: str,
        first_name: str,
        reset_token: str
    ) -> bool:
        """
        Send password reset email with reset link using template.
        
        Args:
            email: User email
            first_name: User first name
            reset_token: Password reset token
        
        Returns:
            True if sent successfully
        """
        subject = "🔒 Password Reset Request - AgileMind"
        reset_url = f"{settings.AGILEMIND_PLATFORM_URL}/auth/reset-password?token={reset_token}"
        
        # Prepare template variables
        variables = {
            'first_name': first_name,
            'reset_url': reset_url
        }
        
        # Load and render template
        html_body = self._load_template('password_reset.html', variables)
        
        return self.send_email(email, subject, html_body)


# Global email service instance
email_service = EmailService()
