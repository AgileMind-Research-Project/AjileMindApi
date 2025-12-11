"""
Domain Extraction Utility

Extracts company domain from email addresses for multi-tenant isolation.
"""

import re
import tldextract
from typing import Optional


def extract_domain_from_email(email: str) -> Optional[str]:
    """
    Real-world domain extractor using Public Suffix List.
    Works for ANY TLD (.com.au, .co.uk, .lk, .gov.lk, etc.)
    """
    if not email or '@' not in email:
        return None

    try:
        _, domain_part = email.split('@', 1)

        # Extract subdomain, domain, suffix using PSL
        res = tldextract.extract(domain_part)

        # res.domain gives the real company/org name
        domain = res.domain.lower()

        # sanitize
        sanitized = re.sub(r'[^a-z0-9]', '', domain)

        return sanitized if sanitized else None

    except Exception:
        return None


def get_tenant_table_name(domain: str) -> str:
    """
    Generate tenant-specific user table name from domain.
    
    Args:
        domain: Company domain
    
    Returns:
        Table name in format: tenant_{domain}
    
    Examples:
        >>> get_tenant_table_name("sliit")
        'tenant_sliit'
        >>> get_tenant_table_name("axixtadigitalalabs")
        'tenant_axixtadigitalalabs'
    """
    return f"tenant_{domain}"


def validate_email_domain(email: str) -> bool:
    """
    Validate that email has a valid domain for tenant isolation.
    
    Args:
        email: Email address
    
    Returns:
        True if email has a valid extractable domain
    """
    domain = extract_domain_from_email(email)
    return domain is not None and len(domain) >= 2
