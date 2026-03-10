"""
Email Service

Send emails using SMTP (Gmail) with HTML templates.
"""

import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
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

    def send_broadcast_template(
        self,
        request: Any,  # DowntimeNotificationRequest or dict
        recipients: List[Dict[str, Any]]
    ) -> int:
        """
        Send a themed broadcast email to multiple recipients.
        
        Args:
            request: Notification request object (DowntimeNotificationRequest or similar)
            recipients: List of recipient dictionaries with 'email' key
            
        Returns:
            Number of successfully sent emails
        """
        try:
            # Handle both object and dict
            if hasattr(request, 'dict'):
                req_dict = request.dict()
            else:
                req_dict = request
            
            # Extract common data
            notif_type = req_dict.get('type', 'PLANNED_MAINTENANCE')
            priority = req_dict.get('priority', 'MEDIUM')
            subject = req_dict.get('content', {}).get('subject', 'System Notification')
            message_body = req_dict.get('content', {}).get('message_body', '')
            
            # Formatting labels
            type_label = notif_type.replace('_', ' ')
            header_text = "Service Outage" if notif_type == "EMERGENCY_OUTAGE" else "New Features" if notif_type == "FEATURE_UPGRADE" else "System Maintenance"
            
            # Format times
            start_time = req_dict.get('schedule', {}).get('start_time')
            end_time = req_dict.get('schedule', {}).get('end_time')
            
            if start_time and isinstance(start_time, datetime):
                start_time = start_time.strftime('%b %d, %Y - %I:%M %p')
            if end_time and isinstance(end_time, datetime):
                end_time = end_time.strftime('%b %d, %Y - %I:%M %p')
            
            # Format components as tags
            components = req_dict.get('affected_components', [])
            components_tags = "".join([f'<span class="component-tag">{c}</span>' for c in (components or [])])
            
            # Parse structured message body if it's JSON
            message_content = message_body
            import json
            try:
                structured = json.loads(message_body)
                if isinstance(structured, dict):
                    html_content = f'<p style="font-weight: 600; color: #111827; margin-bottom: 15px;">{structured.get("summary", "")}</p>'
                    
                    sections = [
                        ('Features', 'features', 'color: #2563eb'),
                        ('Improvements', 'improvements', 'color: #059669'),
                        ('Bug Fixes', 'bug_fixes', 'color: #dc2626'),
                        ('Breaking Changes', 'breaking_changes', 'color: #9333ea'),
                        ('Known Issues', 'known_issues', 'color: #ea580c')
                    ]
                    
                    for title, key, style in sections:
                        items = structured.get(key, [])
                        if items:
                            html_content += f'<div style="font-size: 13px; font-weight: 700; text-transform: uppercase; margin: 20px 0 10px 0; {style}">{title}</div>'
                            html_content += '<ul style="padding-left: 0; margin-top: 0;">'
                            for item in items:
                                # Determine bullet color based on section
                                border_color = "#3b82f6" if key == 'features' else "#ef4444" if key == 'bug_fixes' else "#10b981" if key == 'improvements' else "#9ca3af"
                                html_content += f'<li style="list-style: none; border-left: 3px solid {border_color}; padding-left: 12px; margin-bottom: 8px; font-size: 14px;">{item}</li>'
                            html_content += '</ul>'
                    
                    message_content = html_content
            except:
                # If not JSON, use simple formatting for newlines
                message_content = f'<p style="white-space: pre-wrap;">{message_body}</p>'
            
            # Prepare template variables
            variables = {
                'type': notif_type,
                'type_label': type_label,
                'header_text': header_text,
                'priority': priority,
                'subject': subject,
                'message_content': message_content,
                'start_time': start_time or 'N/A',
                'end_time': end_time or 'N/A',
                'components_tags': components_tags or 'All System Components',
                'platform_url': settings.AGILEMIND_PLATFORM_URL
            }
            
            # Render template
            html_body = self._load_template('broadcast_notification.html', variables)
            
            # Broadcast to all
            sent_count = 0
            for recipient in recipients:
                email = recipient.get('email')
                if email:
                    if self.send_email(email, subject, html_body):
                        sent_count += 1
            
            logger.info(f"Broadcasted {notif_type} notification to {sent_count} recipients")
            return sent_count
            
        except Exception as e:
            logger.error(f"Error in send_broadcast_template: {e}")
            return 0


# Global email service instance
email_service = EmailService()
