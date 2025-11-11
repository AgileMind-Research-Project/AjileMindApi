# Email Templates

This directory contains HTML email templates for the AgileMind platform.

## Available Templates

### 1. `tenant_welcome.html`
**Purpose:** Welcome email sent to new company (tenant) administrators when they register.

**Variables:**
- `{{company_name}}` - Company/organization name
- `{{email}}` - Administrator email address
- `{{tenant_id}}` - Unique tenant identifier
- `{{login_url}}` - URL to login page

**Usage:** Sent when a new company registers on the platform.

---

### 2. `user_welcome.html`
**Purpose:** Welcome email sent to new users invited to join a company workspace.

**Variables:**
- `{{first_name}}` - User's first name
- `{{last_name}}` - User's last name
- `{{company_name}}` - Company/organization name
- `{{email}}` - User's email address
- `{{temporary_password}}` - Auto-generated temporary password
- `{{role}}` - User's role (e.g., Developer, Project Manager)
- `{{login_url}}` - URL to login page

**Usage:** Sent when a Super Admin or Admin invites a new user to the workspace.

---

### 3. `password_reset.html`
**Purpose:** Password reset email with secure token link.

**Variables:**
- `{{first_name}}` - User's first name
- `{{reset_url}}` - Complete URL with reset token

**Usage:** Sent when a user requests a password reset via the "Forgot Password" feature.

---

## How to Edit Templates

### Step 1: Locate the Template
Navigate to `app/services/email_templates/` and open the HTML file you want to edit.

### Step 2: Modify the HTML/CSS
- Edit the HTML structure as needed
- Modify inline CSS styles for visual changes
- Keep variable placeholders in the format `{{variable_name}}`

### Step 3: Preview Changes
Use an HTML email testing tool like:
- [Litmus](https://www.litmus.com/)
- [Email on Acid](https://www.emailonacid.com/)
- Or simply open in a browser for basic preview

### Step 4: Test Email Rendering
After making changes, test the email by triggering the corresponding action:
- **Tenant Welcome:** Register a new company
- **User Welcome:** Invite a new user
- **Password Reset:** Request password reset

---

## Design Guidelines

### Color Schemes
Each template uses a distinct color scheme:
- **Tenant Welcome:** Purple/Indigo gradient (`#667eea`, `#764ba2`)
- **User Welcome:** Green gradient (`#10b981`, `#059669`)
- **Password Reset:** Red gradient (`#ef4444`, `#dc2626`)

### Best Practices
1. **Mobile Responsive:** All templates use responsive design
2. **Fallback Fonts:** System fonts ensure cross-platform compatibility
3. **Inline CSS:** Styles are inline for maximum email client compatibility
4. **Alt Text:** Images should include alt text for accessibility
5. **Test Across Clients:** Test in Gmail, Outlook, Apple Mail, etc.

### Common Components
- **Header:** Gradient background with title
- **Content:** Main body with padding
- **CTA Button:** Call-to-action button with hover effects
- **Info Boxes:** Colored boxes for important information
- **Footer:** Company info and links

---

## Variable Syntax

Variables use double curly braces: `{{variable_name}}`

**Example:**
```html
<p>Hello {{first_name}}!</p>
<p>Welcome to {{company_name}}.</p>
```

**Important:** 
- Do NOT change variable names in templates
- Variable names must match what's defined in `email_service.py`
- If you need new variables, update both the template and the service

---

## Adding New Templates

### Step 1: Create HTML File
Create a new `.html` file in this directory (e.g., `new_template.html`)

### Step 2: Define Template Structure
Use the existing templates as reference for structure and styling.

### Step 3: Update email_service.py
Add a new method in `EmailService` class to load and send the template:

```python
def send_custom_email(self, email: str, **variables) -> bool:
    template_path = os.path.join(os.path.dirname(__file__), 'email_templates', 'new_template.html')
    html_body = self._load_template(template_path, variables)
    subject = "Your Subject Here"
    return self.send_email(email, subject, html_body)
```

### Step 4: Test Thoroughly
Test the new template across multiple email clients and devices.

---

## Troubleshooting

### Template Not Loading
- Ensure file path is correct
- Check file permissions
- Verify template file exists

### Variables Not Replacing
- Check variable names match exactly (case-sensitive)
- Ensure `{{` and `}}` brackets are not broken
- Verify variables are passed in the service method

### Styling Issues
- Some email clients strip certain CSS
- Use inline styles instead of `<style>` tags when possible
- Test in target email clients (Outlook, Gmail, etc.)

---

## Support

For questions or issues with email templates, contact:
- Technical Lead
- Development Team
- Email: dev@agilemind.com

---

**Last Updated:** November 12, 2025
