"""
Configuration Validation

Provides JSON schema validation for configuration files.
"""

import json
import os
from typing import Dict, Tuple, Optional


class ConfigValidator:
    """Validates JSON configuration files against schemas."""
    
    def __init__(self, schema_dir: str):
        self.schema_dir = schema_dir
        self.schemas: Dict[str, dict] = {}
    
    def load_schema(self, schema_name: str) -> Optional[dict]:
        """Load a JSON schema from file."""
        if schema_name in self.schemas:
            return self.schemas[schema_name]
        
        schema_path = os.path.join(self.schema_dir, schema_name)
        if not os.path.exists(schema_path):
            return None
        
        try:
            with open(schema_path) as f:
                schema = json.load(f)
                self.schemas[schema_name] = schema
                return schema
        except Exception as e:
            print(f"Failed to load schema {schema_name}: {e}")
            return None
    
    def validate(self, config: dict, schema_name: str) -> Tuple[bool, Optional[str]]:
        """Validate a configuration against a schema.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        schema = self.load_schema(schema_name)
        if not schema:
            return False, f"Schema {schema_name} not found"
        
        try:
            # Simple validation: check required fields and types
            for required_field in schema.get("required", []):
                if required_field not in config:
                    return False, f"Missing required field: {required_field}"
            
            # Check properties
            for prop_name, prop_schema in schema.get("properties", {}).items():
                if prop_name in config:
                    config_value = config[prop_name]
                    expected_type = prop_schema.get("type")
                    
                    if expected_type and not self._type_matches(config_value, expected_type):
                        return False, f"Field {prop_name} has wrong type (expected {expected_type})"
                    
                    # Check enum values
                    enum_values = prop_schema.get("enum")
                    if enum_values and config_value not in enum_values:
                        return False, f"Field {prop_name} value not in allowed values: {enum_values}"
            
            # Check no additional properties
            if not schema.get("additionalProperties", True):
                allowed_props = set(schema.get("properties", {}).keys())
                config_props = set(config.keys())
                additional = config_props - allowed_props
                if additional:
                    return False, f"Additional properties not allowed: {additional}"
            
            return True, None
        
        except Exception as e:
            return False, f"Validation error: {str(e)}"
    
    def _type_matches(self, value, expected_type: str) -> bool:
        """Check if a value matches an expected type."""
        type_map = {
            "string": str,
            "integer": int,
            "number": (int, float),
            "boolean": bool,
            "object": dict,
            "array": list
        }
        
        if expected_type not in type_map:
            return True  # Unknown type, skip validation
        
        return isinstance(value, type_map[expected_type])


# Create validator instance
CONFIG_DIR = os.path.join(os.path.dirname(__file__), '../config')
config_validator = ConfigValidator(CONFIG_DIR)
