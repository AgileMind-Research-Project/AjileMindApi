# Email Templates - Developer Guide

## 📧 Quick Reference for Developers

### Directory Structure
```
app/services/
├── email_service.py          # Main email service
└── email_templates/
    ├── README.md              # Detailed documentation
    ├── DEVELOPER_GUIDE.md     # This file - quick reference
    ├── tenant_welcome.html    # Company registration email
    ├── user_welcome.html      # User invitation email
    └── password_reset.html    # Password reset email
```

---

## 🚀 Quick Start

### How to Edit Email Templates

1. **Navigate to template directory:**
   ```
   cd app/services/email_templates/
   ```

2. **Open the HTML file you want to edit:**
   - `tenant_welcome.html` - New company welcome
   - `user_welcome.html` - New user invitation
   - `password_reset.html` - Password reset

3. **Edit the HTML/CSS directly:**
   - Modify text content
   - Update styles (inline CSS)
   - Change colors, fonts, layout
   - Keep variable placeholders: `{{variable_name}}`

4. **Save the file** - Changes take effect immediately (no restart needed)

5. **Test the email** by triggering the action:
   - Register a new company
   - Invite a user
   - Request password reset

---

## 🎨 Template Variables

### Tenant Welcome (`tenant_welcome.html`)
```html
{{company_name}}    <!-- Company/organization name -->
{{email}}           <!-- Admin email address -->
{{tenant_id}}       <!-- Unique tenant ID -->
{{login_url}}       <!-- Login page URL -->
```

### User Welcome (`user_welcome.html`)
```html
{{first_name}}          <!-- User's first name -->
{{last_name}}           <!-- User's last name -->
{{email}}               <!-- User's email -->
{{company_name}}        <!-- Company name -->
{{role}}                <!-- User's role -->
{{temporary_password}}  <!-- Auto-generated password -->
{{login_url}}           <!-- Login page URL -->
```

### Password Reset (`password_reset.html`)
```html
{{first_name}}      <!-- User's first name -->
{{reset_url}}       <!-- Full password reset URL with token -->
```

---

## 🎯 Common Customizations

### Change Header Color
```html
<div class="header" style="background: linear-gradient(135deg, #YOUR_COLOR_1 0%, #YOUR_COLOR_2 100%);">
```

### Update Button Style
```html
.cta-button { 
    background: linear-gradient(135deg, #YOUR_COLOR_1 0%, #YOUR_COLOR_2 100%);
}
```

### Modify Company Name in Footer
```html
<p class="company">Your Company Name</p>
```

### Update Support Email
```html
<a href="mailto:your-support@email.com">Contact Support</a>
```

### Change Links
```html
<a href="https://your-docs-url.com">Documentation</a>
<a href="https://your-privacy-url.com">Privacy Policy</a>
```

---

## ⚠️ Important Rules

### ✅ DO
- Edit HTML content freely
- Modify CSS styles
- Change colors, fonts, spacing
- Update company information
- Add new sections if needed
- Test changes before deploying

### ❌ DON'T
- Change variable names: `{{variable_name}}`
- Remove variable placeholders
- Break the HTML structure
- Remove closing tags
- Forget to test on multiple email clients

---

## 🧪 Testing Emails

### Local Testing
1. **Register a test company:**
   ```bash
   # Use API or frontend registration
   POST /api/v1/auth/register
   ```

2. **Check email was sent:**
   - Look in logs: `logs/app.log`
   - Check your email inbox
   - Use a test email service like [Mailtrap](https://mailtrap.io/)

### Email Client Testing
Test in these clients:
- ✉️ Gmail (Web & Mobile)
- 📧 Outlook (Web & Desktop)
- 📱 Apple Mail (iOS)
- 🔧 Thunderbird

### Online Testing Tools
- [Litmus](https://www.litmus.com/) - Professional testing
- [Email on Acid](https://www.emailonacid.com/) - Cross-client preview
- [PutsMail](https://putsmail.com/) - Free HTML email testing

---

## 🎨 Color Schemes

### Current Templates
```css
/* Tenant Welcome - Purple/Indigo */
Primary: #667eea
Secondary: #764ba2

/* User Welcome - Green */
Primary: #10b981
Secondary: #059669

/* Password Reset - Red */
Primary: #ef4444
Secondary: #dc2626
```

### Suggested Alternatives
```css
/* Blue Professional */
Primary: #3b82f6
Secondary: #2563eb

/* Orange Energetic */
Primary: #f97316
Secondary: #ea580c

/* Teal Modern */
Primary: #14b8a6
Secondary: #0d9488
```

---

## 🔧 Advanced: Adding New Template

### Step 1: Create HTML File
```bash
touch app/services/email_templates/your_new_template.html
```

### Step 2: Copy Existing Template Structure
Use `tenant_welcome.html` as base and modify.

### Step 3: Define Variables
Add placeholders like: `{{your_variable}}`

### Step 4: Update email_service.py
```python
def send_your_custom_email(self, email: str, **kwargs) -> bool:
    subject = "Your Subject"
    
    variables = {
        'your_variable': kwargs.get('your_variable'),
        # Add more variables
    }
    
    html_body = self._load_template('your_new_template.html', variables)
    return self.send_email(email, subject, html_body)
```

### Step 5: Call from Your Code
```python
from app.services.email_service import email_service

email_service.send_your_custom_email(
    email="user@example.com",
    your_variable="value"
)
```

---

## 📝 Style Guidelines

### Typography
```css
/* Headers */
font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;

/* Monospace (for credentials) */
font-family: 'Courier New', monospace;
```

### Spacing
```css
/* Content padding */
padding: 40px 30px;

/* Section margins */
margin: 25px 0;

/* Mobile responsive */
@media only screen and (max-width: 600px) {
    padding: 30px 20px;
}
```

### Colors
```css
/* Text */
Primary Text: #333
Secondary Text: #64748b
Muted Text: #94a3b8

/* Backgrounds */
White: #ffffff
Light Gray: #f8fafc
Border: #e2e8f0
```

---

## 🐛 Troubleshooting

### Template Not Loading
**Error:** `FileNotFoundError`
```python
# Check file path in email_service.py
self.template_dir = os.path.join(os.path.dirname(__file__), 'email_templates')
```

### Variables Not Replacing
**Issue:** Variables show as `{{variable_name}}` in email
```python
# Ensure variable is in the variables dict
variables = {
    'company_name': company_name,  # ✅ Correct
    # 'company_name': None,        # ❌ Will show {{company_name}}
}
```

### Styling Not Working
**Issue:** Styles not applied in email client
- Use inline styles instead of `<style>` tags
- Some CSS properties are not supported in emails
- Test in actual email clients, not just browser

### Email Not Sending
**Check:**
1. SMTP settings in `.env`
2. App password for Gmail
3. Network/firewall settings
4. Logs: `logs/app.log`

---

## 📚 Additional Resources

- [Email Template Best Practices](https://www.campaignmonitor.com/dev-resources/guides/)
- [HTML Email Guide](https://templates.mailchimp.com/getting-started/html-email-basics/)
- [CSS Support in Email](https://www.campaignmonitor.com/css/)
- [Email Accessibility](https://www.litmus.com/blog/ultimate-guide-accessible-emails/)

---

## 🤝 Need Help?

- **Documentation:** `email_templates/README.md`
- **Code Issues:** Check `app/services/email_service.py`
- **Questions:** Contact the development team

---

**Last Updated:** November 12, 2025
**Maintainer:** Backend Team
