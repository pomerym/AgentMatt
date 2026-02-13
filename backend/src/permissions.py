"""
Permission & Authorization System

Provides permission management and audit logging for agent actions.
"""

from typing import Optional, List, Dict
from datetime import datetime
import uuid


class Permission:
    """Represents a permission request for an action."""
    
    def __init__(self, user_id: str, action_type: str, action_description: str, 
                 required: bool = False, auto_grant: bool = False):
        self.id = str(uuid.uuid4())
        self.user_id = user_id
        self.action_type = action_type
        self.action_description = action_description
        self.required = required  # If True, action won't proceed without permission
        self.auto_grant = auto_grant  # If True, automatically grant permission
        self.granted = auto_grant
        self.requested_at = datetime.now()
        self.granted_at = None if not auto_grant else datetime.now()
    
    def grant(self):
        """Grant the permission."""
        self.granted = True
        self.granted_at = datetime.now()
    
    def deny(self):
        """Deny the permission."""
        self.granted = False
        self.granted_at = datetime.now()
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "action_type": self.action_type,
            "action_description": self.action_description,
            "required": self.required,
            "granted": self.granted,
            "requested_at": self.requested_at.isoformat(),
            "granted_at": self.granted_at.isoformat() if self.granted_at else None
        }


class PermissionManager:
    """Manages permissions for actions."""
    
    def __init__(self):
        self.permissions: Dict[str, Permission] = {}
        self.permission_history: List[dict] = []
    
    def request_permission(self, user_id: str, action_type: str, 
                          action_description: str, required: bool = True) -> Permission:
        """Request a permission for an action."""
        # Check if permission is auto-grantable based on rules
        auto_grant = self._should_auto_grant(user_id, action_type)
        
        permission = Permission(user_id, action_type, action_description, required, auto_grant)
        self.permissions[permission.id] = permission
        
        if auto_grant:
            self.permission_history.append({
                "action": "auto_granted",
                "permission_id": permission.id,
                "timestamp": datetime.now().isoformat()
            })
        else:
            self.permission_history.append({
                "action": "requested",
                "permission_id": permission.id,
                "timestamp": datetime.now().isoformat()
            })
        
        return permission
    
    def get_permission(self, permission_id: str) -> Optional[Permission]:
        """Get a permission by ID."""
        return self.permissions.get(permission_id)
    
    def grant_permission(self, permission_id: str) -> bool:
        """Grant a permission by ID."""
        permission = self.get_permission(permission_id)
        if permission:
            permission.grant()
            self.permission_history.append({
                "action": "granted",
                "permission_id": permission_id,
                "timestamp": datetime.now().isoformat()
            })
            return True
        return False
    
    def deny_permission(self, permission_id: str) -> bool:
        """Deny a permission by ID."""
        permission = self.get_permission(permission_id)
        if permission:
            permission.deny()
            self.permission_history.append({
                "action": "denied",
                "permission_id": permission_id,
                "timestamp": datetime.now().isoformat()
            })
            return True
        return False
    
    def get_pending_permissions(self, user_id: str = None) -> List[Permission]:
        """Get all pending permissions."""
        pending = [p for p in self.permissions.values() if not p.granted]
        if user_id:
            pending = [p for p in pending if p.user_id == user_id]
        return pending
    
    def get_permission_history(self) -> List[dict]:
        """Get the permission history."""
        return self.permission_history
    
    def _should_auto_grant(self, user_id: str, action_type: str) -> bool:
        """Determine if a permission should be auto-granted based on rules."""
        # Read-only actions are auto-granted
        safe_actions = ["read", "query", "list", "inspect", "view"]
        return any(action_type.lower().startswith(safe) for safe in safe_actions)


# Singleton permission manager
permission_manager = PermissionManager()
