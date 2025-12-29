"""
JWT Token Utilities

JWT token creation, validation, and management.
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from fastapi import HTTPException, status, Header
from app.core.config import settings
from app.core.logger import logger
import boto3
import json
from botocore.exceptions import ClientError


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create JWT access token.
    
    Args:
        data: Data to encode in token (user_id, email, tenant_name, role)
        expires_delta: Optional custom expiration time
    
    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access"
    })
    
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    
    logger.debug(f"Created access token for user: {data.get('sub')}")
    
    return encoded_jwt


def create_refresh_token(data: dict) -> str:
    """
    Create JWT refresh token.
    
    Args:
        data: Data to encode in token (user_id, tenant_name)
    
    Returns:
        Encoded JWT refresh token
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "refresh"
    })
    
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    
    logger.debug(f"Created refresh token for user: {data.get('sub')}")
    
    return encoded_jwt


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decode and validate JWT token.
    
    Args:
        token: JWT token string
    
    Returns:
        Decoded token payload or None if invalid
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError as e:
        logger.warning(f"Token decode failed: {e}")
        return None


def verify_token(token: str, token_type: str = "access") -> Optional[Dict[str, Any]]:
    """
    Verify JWT token and check type.
    
    Args:
        token: JWT token string
        token_type: Expected token type ("access" or "refresh")
    
    Returns:
        Decoded token payload or None if invalid
    """
    payload = decode_token(token)
    
    if payload is None:
        return None
    
    # Check token type
    if payload.get("type") != token_type:
        logger.warning(f"Invalid token type. Expected: {token_type}, Got: {payload.get('type')}")
        return None
    
    # Check expiration
    exp = payload.get("exp")
    if exp is None:
        logger.warning("Token missing expiration")
        return None
    
    if datetime.fromtimestamp(exp) < datetime.utcnow():
        logger.warning("Token expired")
        return None
    
    return payload


def get_user_from_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Extract user information from access token.
    
    Args:
        token: JWT access token
    
    Returns:
        Dictionary with user info including tenant_name and schema
    """
    payload = verify_token(token, token_type="access")
    
    if payload is None:
        return None
    
    tenant_name = payload.get("tenant_name")
    # Generate schema name from tenant name (convert to snake_case)
    schema = None
    if tenant_name:
        # Convert tenant name to schema format (e.g., "Acme Corp" -> "acme_corp")
        schema = tenant_name.lower().replace(" ", "_")
    
    return {
        "user_id": payload.get("sub"),
        "id": payload.get("sub"),  # Add id field for compatibility
        "email": payload.get("email"),
        "tenant_name": tenant_name,
        "schema": schema,  # Add schema field
        "tenant_schema": schema,  # Add alias for compatibility
        "role": payload.get("role")
    }


def create_token_pair(user_data: dict) -> Dict[str, str]:
    """
    Create both access and refresh tokens.
    
    Args:
        user_data: User data to encode (user_id, email, tenant_name, role)
    
    Returns:
        Dictionary with access_token and refresh_token
    """
    access_token = create_access_token(user_data)
    
    # Refresh token only needs minimal data
    refresh_data = {
        "sub": user_data["sub"],
        "tenant_name": user_data.get("tenant_name")
    }
    refresh_token = create_refresh_token(refresh_data)
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "Bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60  # seconds
    }


async def get_current_user_from_token(authorization: str = Header(None, alias="Authorization")) -> Dict[str, Any]:
    """
    FastAPI dependency to extract and validate user from Authorization header.
    
    Args:
        authorization: Authorization header value (Bearer <token>)
    
    Returns:
        Dictionary with user info
    
    Raises:
        HTTPException: If token is missing or invalid
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Extract token from "Bearer <token>" format
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format. Expected: Bearer <token>",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = parts[1]
    user_info = get_user_from_token(token)
    
    if user_info is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user_info

def get_secrets():
    client = boto3.client("secretsmanager")

    secrets_result = {}

    # 1. List all secrets
    paginator = client.get_paginator("list_secrets")

    for page in paginator.paginate():
        for item in page.get("SecretList", []):
            name = item["Name"]

            # 2. Get each secret's decrypted value
            value_resp = client.get_secret_value(SecretId=name)
            
            if "SecretString" in value_resp:
                value_raw = value_resp["SecretString"]
            else:
                value_raw = value_resp["SecretBinary"].decode("utf-8")

            # Try convert value to JSON (if it's JSON)
            try:
                value = json.loads(value_raw)
            except:
                value = value_raw

            # Store in output dict
            secrets_result[name] = value

    return secrets_result

def create_secret(secret_name, secret_value):
    client = boto3.client("secretsmanager")
    
    try:
        response = client.create_secret(
            Name=secret_name,
            SecretString=secret_value
        )
        print("Secret created:",response)
        return {
            "success": True,
            "message": f"Secret '{response.get('Name')}' created successfully."
        }
    
    except ClientError as e:
        return {
            "success": False,
            "message": f"Failed to create secret '{secret_name}'. Error: {e}"
        }


def get_secret(secret_name):
    """
    Retrieve a secret value from AWS Secrets Manager.
    
    Args:
        secret_name: Name of the secret to retrieve
    
    Returns:
        Dict with success status and secret_value or error message
    """
    client = boto3.client("secretsmanager")
    
    try:
        response = client.get_secret_value(SecretId=secret_name)
        
        if "SecretString" in response:
            secret_value = response["SecretString"]
        else:
            secret_value = response["SecretBinary"].decode("utf-8")
        
        return {
            "success": True,
            "secret_value": secret_value
        }
    
    except ClientError as e:
        error_code = e.response['Error']['Code']
        
        if error_code == 'ResourceNotFoundException':
            return {
                "success": False,
                "message": f"Secret '{secret_name}' not found."
            }
        elif error_code == 'InvalidRequestException':
            return {
                "success": False,
                "message": f"Invalid request for secret '{secret_name}'."
            }
        elif error_code == 'InvalidParameterException':
            return {
                "success": False,
                "message": f"Invalid parameter for secret '{secret_name}'."
            }
        else:
            return {
                "success": False,
                "message": f"Error retrieving secret '{secret_name}': {e}"
            }
    except Exception as e:
        return {
            "success": False,
            "message": f"Unexpected error retrieving secret '{secret_name}': {e}"
        }
