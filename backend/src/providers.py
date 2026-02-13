"""
AI Provider Integrations

Provides abstractions for different AI providers (Copilot, Bedrock, etc.)
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict
import os
import json
import logging

logger = logging.getLogger(__name__)


def _resolve_env_value(value: Optional[str]) -> Optional[str]:
    if not isinstance(value, str):
        return value
    trimmed = value.strip()
    if trimmed.startswith("${") and trimmed.endswith("}"):
        env_key = trimmed[2:-1].strip()
        return os.getenv(env_key)
    return value

# Try to import boto3 for AWS Bedrock support
try:
    import boto3
    HAS_BOTO3 = True
except ImportError:
    HAS_BOTO3 = False
    logger.warning("[PROVIDERS] boto3 not installed. AWS Bedrock will use mock responses.")


class AIProvider(ABC):
    """Base class for AI providers."""
    
    def __init__(self, name: str, config: Dict = None):
        self.name = name
        self.config = config or {}
        self.initialized = False
    
    @abstractmethod
    def initialize(self) -> bool:
        """Initialize the provider with credentials and configuration."""
        pass
    
    @abstractmethod
    def send_message(self, message: str, session_context: Optional[Dict] = None) -> str:
        """Send a message to the AI provider and get a response."""
        pass
    
    @abstractmethod
    def validate_config(self) -> bool:
        """Validate that the configuration is valid."""
        pass



class CopilotProvider(AIProvider):
    """GitHub Copilot AI Provider."""
    
    def __init__(self, config: Dict = None):
        super().__init__("copilot", config)
    
    def initialize(self) -> bool:
        """Initialize Copilot provider."""
        logger.info(f"[COPILOT INIT] Initializing Copilot provider")
        if not self.validate_config():
            logger.error(f"[COPILOT INIT] Initialization failed - invalid configuration")
            return False
        self.initialized = True
        logger.info(f"[COPILOT INIT] Copilot provider initialized successfully")
        return True
    
    def validate_config(self) -> bool:
        """Validate Copilot configuration."""
        api_key = _resolve_env_value(self.config.get("api_key")) or os.getenv("COPILOT_API_KEY")
        if not api_key:
            logger.warning(f"[COPILOT VALIDATION] Missing or empty API key")
            return False
        logger.info(f"[COPILOT VALIDATION] API key configured")
        return True
    
    def send_message(self, message: str, session_context: Optional[Dict] = None) -> str:
        """Send message to Copilot."""
        if not self.initialized:
            return "Error: Copilot provider not initialized"
        
        history = (session_context or {}).get("history") or []
        logger.info(f"[COPILOT MESSAGE] Using mock response (real API not implemented)")
        if history:
            return f"Copilot (mock) response to: {message}\n(History messages: {len(history)})"
        return f"Copilot (mock) response to: {message}"


class BedrockProvider(AIProvider):
    """AWS Bedrock AI Provider."""
    
    def __init__(self, config: Dict = None):
        super().__init__("aws_bedrock", config)
        self.bedrock_client = None
    
    def initialize(self) -> bool:
        """Initialize Bedrock provider."""
        logger.info(f"[BEDROCK INIT] Initializing Bedrock provider")
        if not self.validate_config():
            logger.error(f"[BEDROCK INIT] Initialization failed - invalid configuration")
            return False

        effective_config = self._resolve_effective_config()
        
        # Try to create AWS client
        if HAS_BOTO3:
            try:
                logger.info(f"[BEDROCK INIT] Creating AWS Bedrock client")
                self.bedrock_client = boto3.client(
                    'bedrock-runtime',
                    region_name=effective_config.get('region', 'us-east-1'),
                    aws_access_key_id=effective_config.get('access_key_id'),
                    aws_secret_access_key=effective_config.get('secret_access_key'),
                    aws_session_token=effective_config.get('session_token') or None
                )
                logger.info(f"[BEDROCK INIT] AWS Bedrock client created successfully")
            except Exception as e:
                logger.warning(f"[BEDROCK INIT] Failed to create AWS client: {str(e)}")
                logger.warning(f"[BEDROCK INIT] Will use mock responses")
                self.bedrock_client = None
        else:
            logger.warning(f"[BEDROCK INIT] boto3 not installed, using mock responses")
        
        self.initialized = True
        logger.info(f"[BEDROCK INIT] Bedrock provider initialized successfully")
        return True
    
    def validate_config(self) -> bool:
        """Validate Bedrock configuration."""
        effective_config = self._resolve_effective_config()
        required_fields = ["access_key_id", "secret_access_key", "region", "model_id"]
        missing_fields = []
        empty_fields = []

        for field in required_fields:
            if field not in effective_config:
                missing_fields.append(field)
            elif not effective_config.get(field):
                empty_fields.append(field)
        
        if missing_fields or empty_fields:
            logger.warning(f"[BEDROCK VALIDATION] Config invalid: missing={missing_fields}, empty={empty_fields}")
            logger.debug(f"[BEDROCK VALIDATION] Current config keys: {list(self.config.keys())}")
            return False
        
        logger.info(f"[BEDROCK VALIDATION] All required fields present and non-empty")
        return True
    
    def send_message(self, message: str, session_context: Optional[Dict] = None) -> str:
        """Send message to Bedrock."""
        if not self.initialized:
            return "Error: Bedrock provider not initialized"
        
        model_id = self.config.get("model_id", "anthropic.claude-3-sonnet-20240229-v1:0")
        inference_profile_id = self.config.get("inference_profile_id")

        if inference_profile_id:
            logger.info(f"[BEDROCK MESSAGE] Using inference profile ID: {inference_profile_id}")
            model_id = inference_profile_id
        elif model_id == "anthropic.claude-opus-4-5-20251101-v1:0":
            model_id = "global.anthropic.claude-opus-4-5-20251101-v1:0"
            logger.info("[BEDROCK MESSAGE] Using global inference profile for Opus 4.5")
        
        # If we have boto3 and a client, use real AWS Bedrock
        if HAS_BOTO3 and self.bedrock_client:
            try:
                logger.info(f"[BEDROCK MESSAGE] Calling AWS Bedrock API with model: {model_id}")
                
                # Prepare the message for Claude model using correct Bedrock API format
                history = (session_context or {}).get("history") or []
                messages = history if history else [
                    {
                        "role": "user",
                        "content": message
                    }
                ]
                system_prompt = (session_context or {}).get("system")
                request_body = {
                    "anthropic_version": self.config.get("anthropic_version", "bedrock-2023-05-31"),
                    "max_tokens": int(self.config.get("max_tokens", 4096)),
                    "messages": messages,
                    "temperature": float(self.config.get("temperature", 0.7))
                }

                if system_prompt:
                    request_body["system"] = system_prompt
                
                logger.debug(f"[BEDROCK MESSAGE] Request: {json.dumps(request_body, indent=2)}")
                
                # Call Bedrock API - note: contentType is critical for the request
                response = self.bedrock_client.invoke_model(
                    modelId=model_id,
                    contentType='application/json',
                    accept='application/json',
                    body=json.dumps(request_body)
                )
                
                # Parse response
                response_body = json.loads(response['body'].read())
                logger.debug(f"[BEDROCK MESSAGE] Response: {json.dumps(response_body, indent=2)}")
                
                # Extract the text from the response
                # For Claude models, the response format is: content[0].text
                if 'content' in response_body and len(response_body['content']) > 0:
                    ai_response = response_body['content'][0].get('text', 'No response')
                else:
                    ai_response = 'No response from Bedrock'
                
                logger.info(f"[BEDROCK MESSAGE] Successfully received response from Bedrock")
                return ai_response
                
            except Exception as e:
                error_msg = f"Error calling AWS Bedrock: {str(e)}"
                logger.error(f"[BEDROCK MESSAGE] {error_msg}")
                logger.exception(f"[BEDROCK MESSAGE] Full exception:")
                return error_msg
        
        # Fallback to mock response if boto3 not available or client not initialized
        logger.info(f"[BEDROCK MESSAGE] Using mock response (boto3 unavailable or client not initialized)")
        return f"Mock Bedrock ({model_id}) response to: {message}"

    def _resolve_effective_config(self) -> Dict:
        """Resolve config with environment variable fallbacks."""
        return {
            "access_key_id": _resolve_env_value(self.config.get("access_key_id")) or os.getenv("AWS_ACCESS_KEY_ID"),
            "secret_access_key": _resolve_env_value(self.config.get("secret_access_key")) or os.getenv("AWS_SECRET_ACCESS_KEY"),
            "session_token": _resolve_env_value(self.config.get("session_token")) or os.getenv("AWS_SESSION_TOKEN"),
            "region": _resolve_env_value(self.config.get("region")) or os.getenv("AWS_DEFAULT_REGION") or os.getenv("AWS_REGION"),
            "model_id": self.config.get("model_id"),
            "inference_profile_id": self.config.get("inference_profile_id"),
            "anthropic_version": self.config.get("anthropic_version"),
            "max_tokens": self.config.get("max_tokens"),
            "temperature": self.config.get("temperature")
        }


class ProviderRegistry:
    """Registry for managing AI providers."""
    
    def __init__(self):
        self.providers: Dict[str, AIProvider] = {}
        self.active_provider: Optional[str] = None
    
    def register_provider(self, provider: AIProvider):
        """Register a new provider."""
        self.providers[provider.name] = provider
    
    def get_provider(self, name: str) -> Optional[AIProvider]:
        """Get a provider by name."""
        return self.providers.get(name)
    
    def set_active_provider(self, name: str) -> bool:
        """Set the active provider."""
        if name in self.providers:
            self.active_provider = name
            return True
        return False
    
    def get_active_provider(self) -> Optional[AIProvider]:
        """Get the currently active provider."""
        if self.active_provider and self.active_provider in self.providers:
            return self.providers[self.active_provider]
        return None
    
    def list_providers(self) -> List[str]:
        """List all registered providers."""
        return list(self.providers.keys())
    
    def send_message(self, message: str, session_context: Optional[Dict] = None) -> str:
        """Send message using the active provider."""
        provider = self.get_active_provider()
        if not provider:
            return "Error: No active provider configured"
        
        if not provider.initialized:
            provider.initialize()
        
        if not provider.initialized:
            return f"Error: Failed to initialize {provider.name}"
        
        return provider.send_message(message, session_context)
    
    def update_provider_config(self, name: str, config: Dict) -> bool:
        """Update configuration for a provider."""
        provider = self.get_provider(name)
        if provider:
            provider.config.update(config)
            # Reinitialize with new config
            provider.initialized = False
            return provider.initialize()
        return False


# Global provider registry
provider_registry = ProviderRegistry()

# Register default providers
provider_registry.register_provider(CopilotProvider())
provider_registry.register_provider(BedrockProvider())
