"""
Model Configuration Module

This module provides a lightweight configuration class specifically for the models package,
decoupled from CLI-specific settings.
"""

import os
import logging
from typing import Optional, Dict, Any
from pathlib import Path

########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)


########################################################################
#                               CLASSES                                #
########################################################################
class ModelConfig:
    """
    Configuration class for model-related settings.

    This class handles API keys, model directories, and other model-specific
    configuration without depending on CLI-specific settings.
    """

    def __init__(
        self,
        models_directory: Optional[str] = None,
        openai_api_token: Optional[str] = None,
        anthropic_api_token: Optional[str] = None,
        huggingface_api_token: Optional[str] = None,
        openrouter_api_token: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize model configuration.

        Args:
            models_directory: Directory where models are stored
            openai_api_token: OpenAI API key
            anthropic_api_token: Anthropic API key
            huggingface_api_token: HuggingFace API key
            openrouter_api_token: OpenRouter API key
            **kwargs: Additional configuration options
        """
        # Set default models directory
        self.models_directory = models_directory or self._get_default_models_dir()

        # API tokens - try environment variables if not provided
        self.openai_api_token = openai_api_token or os.getenv('OPENAI_API_KEY')
        self.anthropic_api_token = anthropic_api_token or os.getenv('ANTHROPIC_API_KEY')
        self.huggingface_api_token = huggingface_api_token or os.getenv('HUGGINGFACE_API_KEY')
        self.openrouter_api_token = openrouter_api_token or os.getenv('OPENROUTER_API_KEY')

        # Store additional configuration
        self.additional_config = kwargs

        # Ensure models directory exists
        self._ensure_models_directory()

        logger.debug(f"ModelConfig initialized with models_directory: {self.models_directory}")
        self._log_api_key_status()

    def _get_default_models_dir(self) -> str:
        """Get the default models directory."""
        # Use a sensible default in the project structure
        default_dir = os.path.join(os.path.expanduser("~"), ".claia", "models")
        return default_dir

    def _ensure_models_directory(self) -> None:
        """Ensure the models directory exists."""
        try:
            Path(self.models_directory).mkdir(parents=True, exist_ok=True)
            logger.debug(f"Models directory ensured: {self.models_directory}")
        except Exception as e:
            logger.error(f"Failed to create models directory {self.models_directory}: {e}")
            raise

    def _log_api_key_status(self) -> None:
        """Log which API keys are available (without exposing them)."""
        keys_status = []

        if self.openai_api_token:
            keys_status.append("OpenAI")
        if self.anthropic_api_token:
            keys_status.append("Anthropic")
        if self.huggingface_api_token:
            keys_status.append("HuggingFace")
        if self.openrouter_api_token:
            keys_status.append("OpenRouter")

        if keys_status:
            logger.debug(f"Available API keys: {', '.join(keys_status)}")
        else:
            logger.debug("No API keys configured")

    def get_api_token(self, provider: str) -> Optional[str]:
        """
        Get API token for a specific provider.

        Args:
            provider: Provider name (openai, anthropic, huggingface, openrouter)

        Returns:
            API token if available, None otherwise
        """
        provider_lower = provider.lower()

        if provider_lower in ['openai', 'openai_api']:
            return self.openai_api_token
        elif provider_lower in ['anthropic', 'anthropic_api']:
            return self.anthropic_api_token
        elif provider_lower in ['huggingface', 'hf', 'huggingface_api']:
            return self.huggingface_api_token
        elif provider_lower in ['openrouter', 'openrouter_api']:
            return self.openrouter_api_token
        else:
            logger.warning(f"Unknown API provider: {provider}")
            return None

    def has_api_token(self, provider: str) -> bool:
        """
        Check if API token is available for a provider.

        Args:
            provider: Provider name

        Returns:
            True if API token is available, False otherwise
        """
        return self.get_api_token(provider) is not None

    def set_api_token(self, provider: str, token: str) -> None:
        """
        Set API token for a provider.

        Args:
            provider: Provider name
            token: API token
        """
        provider_lower = provider.lower()

        if provider_lower in ['openai', 'openai_api']:
            self.openai_api_token = token
        elif provider_lower in ['anthropic', 'anthropic_api']:
            self.anthropic_api_token = token
        elif provider_lower in ['huggingface', 'hf', 'huggingface_api']:
            self.huggingface_api_token = token
        elif provider_lower in ['openrouter', 'openrouter_api']:
            self.openrouter_api_token = token
        else:
            logger.warning(f"Unknown API provider: {provider}")

        logger.debug(f"API token set for provider: {provider}")

    def get_config_value(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value.

        Args:
            key: Configuration key
            default: Default value if key not found

        Returns:
            Configuration value
        """
        # Check standard attributes first
        if hasattr(self, key):
            return getattr(self, key)

        # Check additional config
        return self.additional_config.get(key, default)

    def set_config_value(self, key: str, value: Any) -> None:
        """
        Set a configuration value.

        Args:
            key: Configuration key
            value: Configuration value
        """
        if hasattr(self, key):
            setattr(self, key, value)
        else:
            self.additional_config[key] = value

        logger.debug(f"Configuration value set: {key}")

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'ModelConfig':
        """
        Create ModelConfig from dictionary.

        Args:
            config_dict: Configuration dictionary

        Returns:
            ModelConfig instance
        """
        return cls(**config_dict)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert ModelConfig to dictionary.

        Returns:
            Configuration dictionary (without sensitive tokens)
        """
        config = {
            'models_directory': self.models_directory,
            'has_openai_token': bool(self.openai_api_token),
            'has_anthropic_token': bool(self.anthropic_api_token),
            'has_huggingface_token': bool(self.huggingface_api_token),
            'has_openrouter_token': bool(self.openrouter_api_token),
        }
        config.update(self.additional_config)
        return config

    def __repr__(self) -> str:
        """String representation without exposing sensitive information."""
        return f"ModelConfig(models_directory='{self.models_directory}', api_keys={list(self._get_available_providers())})"

    def _get_available_providers(self) -> list:
        """Get list of providers with available API keys."""
        providers = []
        if self.openai_api_token:
            providers.append('openai')
        if self.anthropic_api_token:
            providers.append('anthropic')
        if self.huggingface_api_token:
            providers.append('huggingface')
        if self.openrouter_api_token:
            providers.append('openrouter')
        return providers
