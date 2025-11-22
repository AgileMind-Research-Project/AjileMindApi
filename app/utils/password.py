"""
Password Utilities

Password hashing, validation, and policy enforcement.
"""

import re
import secrets
import string
import bcrypt
from typing import Tuple, List
from app.core.config import settings
from app.core.logger import logger


def hash_password(password: str) -> str:
    """
    Hash password using bcrypt.
    
    Args:
        password: Plain text password
    
    Returns:
        Hashed password
    
    Note:
        Bcrypt has a 72-byte limit. Passwords are truncated to 72 bytes
        before hashing to comply with this limitation.
    """
    # Truncate password to 72 bytes (bcrypt limitation)
    password_bytes = password.encode('utf-8')[:72]
    # Generate salt and hash the password
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify plain password against hashed password.
    
    Args:
        plain_password: Plain text password
        hashed_password: Hashed password from database
    
    Returns:
        True if password matches, False otherwise
    
    Note:
        Truncates password to 72 bytes before verification to match hashing behavior.
    """
    try:
        # Truncate password to 72 bytes (bcrypt limitation)
        password_bytes = plain_password.encode('utf-8')[:72]
        hashed_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except Exception as e:
        logger.error(f"Password verification error: {str(e)}")
        return False


def validate_password(password: str) -> Tuple[bool, List[str]]:
    """
    Validate password against policy requirements.
    
    Args:
        password: Password to validate
    
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    
    # Check minimum length
    if len(password) < settings.PASSWORD_MIN_LENGTH:
        errors.append(f"Password must be at least {settings.PASSWORD_MIN_LENGTH} characters")
    
    # Check uppercase
    if settings.PASSWORD_REQUIRE_UPPERCASE and not re.search(r"[A-Z]", password):
        errors.append("Password must contain at least one uppercase letter")
    
    # Check lowercase
    if settings.PASSWORD_REQUIRE_LOWERCASE and not re.search(r"[a-z]", password):
        errors.append("Password must contain at least one lowercase letter")
    
    # Check numbers
    if settings.PASSWORD_REQUIRE_NUMBERS and not re.search(r"\d", password):
        errors.append("Password must contain at least one number")
    
    # Check symbols
    if settings.PASSWORD_REQUIRE_SYMBOLS and not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        errors.append("Password must contain at least one symbol")
    
    is_valid = len(errors) == 0
    
    return is_valid, errors


def get_password_requirements() -> dict:
    """
    Get password policy requirements for frontend validation.
    
    Returns:
        Dictionary of requirements
    """
    return {
        "min_length": settings.PASSWORD_MIN_LENGTH,
        "require_uppercase": settings.PASSWORD_REQUIRE_UPPERCASE,
        "require_lowercase": settings.PASSWORD_REQUIRE_LOWERCASE,
        "require_numbers": settings.PASSWORD_REQUIRE_NUMBERS,
        "require_symbols": settings.PASSWORD_REQUIRE_SYMBOLS,
    }


def check_password_strength(password: str) -> dict:
    """
    Check which password requirements are met.
    
    Args:
        password: Password to check
    
    Returns:
        Dictionary of requirement checks
    """
    return {
        "min_length": len(password) >= settings.PASSWORD_MIN_LENGTH,
        "has_uppercase": bool(re.search(r"[A-Z]", password)),
        "has_lowercase": bool(re.search(r"[a-z]", password)),
        "has_number": bool(re.search(r"\d", password)),
        "has_symbol": bool(re.search(r"[!@#$%^&*(),.?\":{}|<>]", password)),
    }


def generate_user_password(first_name: str, email: str) -> str:
    """
    Generate temporary password for new users.
    
    Format: {FirstName}{EmailLocalPart}@123
    Example: John with john.doe@acme.com -> Johnjohn.doe@123
    
    If doesn't meet policy, add additional characters until it does.
    
    Args:
        first_name: User's first name
        email: User's email
    
    Returns:
        Generated password that meets policy
    """
    # Extract email local part (before @)
    email_local = email.split("@")[0]
    
    # Capitalize first letter of first name
    first_name_capitalized = first_name.capitalize()
    
    # Create base password
    base_password = f"{first_name_capitalized}{email_local}{settings.DEFAULT_PASSWORD_SUFFIX}"
    
    # Check if it meets policy
    is_valid, errors = validate_password(base_password)
    
    if is_valid:
        logger.info(f"Generated password for {email}: {len(base_password)} chars")
        return base_password
    
    # If not valid, add a symbol at the end
    password_with_symbol = f"{base_password}!"
    is_valid, errors = validate_password(password_with_symbol)
    
    if is_valid:
        logger.info(f"Generated password with symbol for {email}: {len(password_with_symbol)} chars")
        return password_with_symbol
    
    # If still not valid, generate a random strong password
    logger.warning(f"Using random password for {email} as auto-generated didn't meet policy")
    return generate_random_password()


def generate_random_password(length: int = 12) -> str:
    """
    Generate a random strong password.
    
    Args:
        length: Password length (default: 12)
    
    Returns:
        Random password meeting all requirements
    """
    # Ensure we have at least one of each required type
    password_chars = []
    
    if settings.PASSWORD_REQUIRE_UPPERCASE:
        password_chars.append(secrets.choice(string.ascii_uppercase))
    
    if settings.PASSWORD_REQUIRE_LOWERCASE:
        password_chars.append(secrets.choice(string.ascii_lowercase))
    
    if settings.PASSWORD_REQUIRE_NUMBERS:
        password_chars.append(secrets.choice(string.digits))
    
    if settings.PASSWORD_REQUIRE_SYMBOLS:
        password_chars.append(secrets.choice("!@#$%^&*"))
    
    # Fill the rest with random characters
    all_chars = string.ascii_letters + string.digits + "!@#$%^&*"
    remaining_length = length - len(password_chars)
    
    for _ in range(remaining_length):
        password_chars.append(secrets.choice(all_chars))
    
    # Shuffle to avoid predictable pattern
    secrets.SystemRandom().shuffle(password_chars)
    
    password = ''.join(password_chars)
    
    # Verify it meets policy
    is_valid, _ = validate_password(password)
    if not is_valid:
        # Recursively try again if somehow it doesn't meet policy
        return generate_random_password(length)
    
    return password


def generate_reset_token() -> str:
    """
    Generate secure password reset token.
    
    Returns:
        Random token string
    """
    return secrets.token_urlsafe(32)
