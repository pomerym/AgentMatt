"""
Authentication and security middleware for the AgentMatt API.
Handles API key validation, rate limiting, and audit logging.
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Optional
from fastapi import Request, HTTPException, status
from functools import lru_cache
import json

logger = logging.getLogger(__name__)

# Rate limiting: track API key usage
_rate_limit_cache: dict = {}


def get_api_key() -> str:
    """
    Get API key from environment or config.
    For multi-user deployment, this would come from a proper secrets manager.
    """
    key = os.environ.get('AGENTMATT_API_KEY')
    if not key:
        logger.warning('AGENTMATT_API_KEY not set - generating temporary key for local development')
        key = 'dev-key-insecure-change-in-production'
    return key


def validate_api_key(request: Request) -> str:
    """
    Validate API key from request headers.
    Supports:
    - Authorization: Bearer <key>
    - X-API-Key: <key>
    
    Returns the API key if valid.
    Raises HTTPException if invalid.
    """
    auth_header = request.headers.get('Authorization', '')
    api_key_header = request.headers.get('X-API-Key', '')
    
    provided_key = None
    
    # Try Authorization: Bearer <key>
    if auth_header.startswith('Bearer '):
        provided_key = auth_header[7:]
    # Try X-API-Key header
    elif api_key_header:
        provided_key = api_key_header
    
    if not provided_key:
        logger.warning(f'Missing API key in request from {request.client.host if request.client else "unknown"}')
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Missing or invalid API key'
        )
    
    expected_key = get_api_key()
    
    if provided_key != expected_key:
        logger.warning(f'Invalid API key attempt from {request.client.host if request.client else "unknown"}')
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Invalid API key'
        )
    
    return provided_key


def check_rate_limit(identifier: str, limit_per_min: int = 60) -> bool:
    """
    Simple rate limiting using in-memory cache.
    For production, use Redis or similar.
    
    Args:
        identifier: User/API key identifier
        limit_per_min: Max requests per minute
    
    Returns:
        True if request is allowed, False if rate limited
    """
    now = datetime.now()
    window_start = now - timedelta(minutes=1)
    
    if identifier not in _rate_limit_cache:
        _rate_limit_cache[identifier] = []
    
    # Clean old requests outside the window
    _rate_limit_cache[identifier] = [
        ts for ts in _rate_limit_cache[identifier]
        if ts > window_start
    ]
    
    # Check if limit exceeded
    if len(_rate_limit_cache[identifier]) >= limit_per_min:
        logger.warning(f'Rate limit exceeded for {identifier}')
        return False
    
    # Add current request
    _rate_limit_cache[identifier].append(now)
    return True


def log_action(
    action: str,
    resource: str,
    status_code: int,
    api_key: Optional[str] = None,
    details: Optional[dict] = None,
    error: Optional[str] = None
) -> None:
    """
    Audit log an action for compliance and debugging.
    
    Args:
        action: Type of action (GET, POST, DELETE, EXECUTE_COMMAND, etc.)
        resource: What was accessed/modified
        status_code: HTTP status code or operation result
        api_key: API key used (last 4 chars only for security)
        details: Additional context dict
        error: Error message if applicable
    """
    masked_key = f"...{api_key[-4:]}" if api_key and len(api_key) > 4 else "unknown"
    
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'action': action,
        'resource': resource,
        'status': status_code,
        'api_key': masked_key,
        'details': details or {},
        'error': error
    }
    
    # Log to file for audit trail
    try:
        audit_log_path = '/tmp/agentmatt-audit.log'  # Should use config path
        with open(audit_log_path, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
    except Exception as e:
        logger.error(f'Failed to write audit log: {e}')
    
    # Also log to logger
    log_level = logging.WARNING if error else logging.INFO
    logger.log(
        log_level,
        f'{action} {resource} - Key: {masked_key} - Status: {status_code}' +
        (f' - Error: {error}' if error else '')
    )


def get_safe_error_message(error: Exception) -> str:
    """
    Convert exception to safe error message that doesn't leak internals.
    """
    error_str = str(error).lower()
    
    # Map known errors to generic messages
    if 'permission denied' in error_str or 'unauthorized' in error_str:
        return 'Permission denied'
    elif 'not found' in error_str:
        return 'Resource not found'
    elif 'timeout' in error_str:
        return 'Operation timed out'
    elif 'connection' in error_str:
        return 'Service unavailable'
    else:
        # Default generic message
        return 'An error occurred processing your request'
