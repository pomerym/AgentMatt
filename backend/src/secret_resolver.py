"""
Secret Resolver

Resolves secrets from environment variables and Bitwarden references.
"""

from __future__ import annotations

import os
import re
import logging
from typing import Any, Dict, Optional

from .bitwarden_client import BitwardenClient, BitwardenError

logger = logging.getLogger(__name__)


_bitwarden_client: Optional[BitwardenClient] = None
_bitwarden_aliases: Dict[str, Dict[str, str]] = {}


def configure_bitwarden(client: Optional[BitwardenClient], aliases: Optional[Dict[str, Dict[str, str]]] = None) -> None:
    global _bitwarden_client, _bitwarden_aliases
    _bitwarden_client = client
    _bitwarden_aliases = aliases or {}


def resolve_secret_value(value: Any) -> Any:
    if not isinstance(value, str):
        return value

    trimmed = value.strip()
    
    # Handle ${ENV_VAR} references
    if trimmed.startswith("${") and trimmed.endswith("}"):
        env_key = trimmed[2:-1].strip()
        return os.getenv(env_key)

    # Handle pure bw:// references
    if trimmed.startswith("bw://"):
        logger.debug(f"[SECRET_RESOLVER] Resolving pure bw:// reference: {trimmed}")
        return _resolve_bitwarden_reference(trimmed)

    # Handle embedded bw:// references within strings
    if "bw://" in value:
        logger.debug(f"[SECRET_RESOLVER] Found embedded bw:// in message: {value[:100]}")
        def replace_bw_ref(match):
            ref = match.group(0)
            try:
                logger.debug(f"[SECRET_RESOLVER] Replacing: {ref}")
                resolved = _resolve_bitwarden_reference(ref)
                logger.debug(f"[SECRET_RESOLVER] Replaced {ref} with value (length={len(str(resolved))})")
                return resolved
            except Exception as e:
                # If resolution fails, return the original reference
                logger.warning(f"[SECRET_RESOLVER] Failed to resolve {ref}: {e}")
                return ref
        
        # Pattern matches bw://ItemName/field (item name can have spaces, field cannot)
        pattern = r'bw://[^/]+/\S+'
        result = re.sub(pattern, replace_bw_ref, value)
        logger.debug(f"[SECRET_RESOLVER] Final result: {result[:100] if len(result) > 100 else result}")
        return result

    return value


def resolve_config(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: resolve_config(val) for key, val in value.items()}
    if isinstance(value, list):
        return [resolve_config(item) for item in value]
    return resolve_secret_value(value)


def _resolve_bitwarden_reference(reference: str) -> Any:
    logger.debug(f"[SECRET_RESOLVER] _resolve_bitwarden_reference called with: {reference}")
    
    if not _bitwarden_client:
        logger.debug(f"[SECRET_RESOLVER] No Bitwarden client configured, returning reference as-is")
        # Return the reference as-is if Bitwarden is not configured
        return reference

    path = reference[len("bw://"):]
    if not path:
        raise BitwardenError("Bitwarden reference is empty")

    parts = path.split("/", 1)
    alias_or_item = parts[0].strip()
    field = parts[1].strip() if len(parts) > 1 else ""

    logger.debug(f"[SECRET_RESOLVER] alias_or_item={alias_or_item}, field={field}")

    if alias_or_item in _bitwarden_aliases:
        logger.debug(f"[SECRET_RESOLVER] Found alias: {alias_or_item}")
        alias = _bitwarden_aliases[alias_or_item]
        item_name = alias.get("item")
        alias_field = alias.get("field")
        if not field:
            field = alias_field or ""
        if not item_name:
            raise BitwardenError(f"Alias '{alias_or_item}' missing item name")
    else:
        logger.debug(f"[SECRET_RESOLVER] Using {alias_or_item} as item name (not an alias)")
        item_name = alias_or_item

    if not field:
        raise BitwardenError("Bitwarden reference missing field")

    logger.debug(f"[SECRET_RESOLVER] Fetching item '{item_name}', field '{field}'")
    try:
        value = _bitwarden_client.get_secret(item_name, field)
        logger.debug(f"[SECRET_RESOLVER] Successfully resolved {item_name}/{field}")
        return value
    except Exception as e:
        logger.error(f"[SECRET_RESOLVER] Failed to get secret {item_name}/{field}: {e}")
        raise
