"""
Command execution allowlist and sandboxing for safe shell command handling.
Prevents arbitrary command execution by validating against approved patterns.
"""

import re
import logging
from typing import List, Tuple, Optional

logger = logging.getLogger(__name__)

# Allowlist of safe command prefixes and patterns
SAFE_COMMAND_PATTERNS = [
    # Splunk CLI operations
    r'^splunk\s+',
    r'^curl\s+https?://',  # Only HTTP/HTTPS URLs
    
    # Safe utilities (read-only or low-risk)
    r'^ls\s+',
    r'^pwd$',
    r'^whoami$',
    r'^date$',
    r'^echo\s+',
    r'^grep\s+',
    r'^cat\s+',
    r'^tail\s+',
    r'^head\s+',
    r'^wc\s+',
    r'^find\s+',
    r'^which\s+',
    r'^type\s+',
    
    # Python scripts (specific to this project)
    r'^python[0-9.]*\s+[a-zA-Z0-9_./]+\.py\s+',
    r'^python[0-9.]*\s+-c\s+',
    
    # Git operations (safe ones)
    r'^git\s+(status|log|diff|branch|tag|show)\s+',
    r'^git\s+clone\s+https?://',
    
    # No pipe stdout to /dev/null, redirection to files in /tmp
    r'^[^>|&;`$()]*$',  # No shell metacharacters
]

# Deny patterns - explicitly block dangerous commands
DANGEROUS_PATTERNS = [
    r'rm\s+-rf\s+/',  # Don't allow recursive delete of root
    r'>>\s*/etc/',   # Don't allow writing to /etc
    r'>\s*/etc/',    # Don't allow writing to /etc
    r'sudo\s+',      # No sudo
    r'chmod\s+777',  # Don't allow open permissions
    r';\s*rm\s+',    # Chained delete commands
    r'`.*`',         # Backticks (command substitution)
    r'\$\(',         # $() command substitution
    r'&&\s*rm\s+',   # Chained delete
    r'\|\s*nc\s+',   # Piping to netcat
    r'>>\s*/dev/null\s*;\s*rm',  # rm disguised as background job
]


def is_command_allowed(command: str) -> Tuple[bool, str]:
    """
    Check if a command is safe to execute.
    
    Args:
        command: Shell command to validate
        
    Returns:
        Tuple of (is_allowed: bool, reason: str)
    """
    command = command.strip()
    
    if not command:
        return False, 'Empty command'
    
    # Check deny patterns first (fail-fast)
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            logger.warning(f'Command blocked by deny pattern: {pattern}')
            return False, f'Command contains disallowed pattern'
    
    # Check allow patterns
    for pattern in SAFE_COMMAND_PATTERNS:
        if re.match(pattern, command, re.IGNORECASE):
            logger.info(f'Command allowed: {command[:50]}...')
            return True, 'Command matches safe pattern'
    
    logger.warning(f'Command not in allowlist: {command[:50]}...')
    return False, 'Command not in approved allowlist'


def get_command_restrictions(command: str) -> dict:
    """
    Get runtime restrictions for a command.
    
    Returns:
        dict with keys:
        - timeout: Max seconds to run
        - max_output: Max bytes of output
        - cwd: Working directory (if restricted)
        - env_vars: Dict of allowed env vars
    """
    
    # Default restrictive settings
    restrictions = {
        'timeout': 30,  # 30 second timeout
        'max_output': 1024 * 1024,  # 1MB max output
        'cwd': None,  # Use current working directory
        'env_vars': {},
        'allow_stderr': False,
    }
    
    # Splunk commands get more time (might need to connect to service)
    if command.startswith('splunk'):
        restrictions['timeout'] = 60
        restrictions['max_output'] = 5 * 1024 * 1024  # 5MB for splunk output
        restrictions['allow_stderr'] = True
    
    # Network operations get more output space
    if 'curl' in command or 'wget' in command:
        restrictions['max_output'] = 10 * 1024 * 1024  # 10MB for downloads
    
    return restrictions


def sanitize_output(output: str, max_bytes: int = 1024 * 1024) -> str:
    """
    Sanitize command output to prevent leaking sensitive data.
    Truncates large outputs and redacts common sensitive patterns.
    """
    
    # Truncate if too large
    if len(output) > max_bytes:
        output = output[:max_bytes] + f'\n... (truncated, {len(output) - max_bytes} bytes omitted)'
    
    # Redact common sensitive patterns
    # API keys (generic JWT-like pattern)
    output = re.sub(r'(eyJ[\w\-\.]+)', r'[REDACTED_TOKEN]', output)
    
    # AWS keys
    output = re.sub(r'AKIA[0-9A-Z]{16}', '[REDACTED_AWS_KEY]', output)
    
    # Passwords in URLs (basic auth)
    output = re.sub(r'(://.+?):(.+?)@', r'\1:[REDACTED_PASSWORD]@', output)
    
    return output
