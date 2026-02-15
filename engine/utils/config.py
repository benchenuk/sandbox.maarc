"""
Configuration Loader
Load and validate configuration files
"""

import os
import re
from pathlib import Path
from typing import Any, Dict
import yaml

from rich.console import Console

console = Console()

# Pattern to match ${ENV_VAR} or ${ENV_VAR:-default}
ENV_PLACEHOLDER_PATTERN = re.compile(r'\$\{([^}]+)\}')


DEFAULT_CONFIG = {
    "app": {
        "name": "Consensus-CLI",
        "version": "0.3.0",
    },
    "research": {
        "default_iterations": 5,
        "min_iterations": 3,
        "max_iterations": 10,
        "consensus_threshold": 0.85,
    },
    "orchestrator": {
        "provider": "litellm_proxy",
        "temperature": 0.7,
        "team_generation": {
            "min_agents": 3,
            "max_agents": 5,
            "require_skeptic": True,
        },
    },
    "models": {
        "providers": {
            "litellm_proxy": {
                "enabled": True,
                "api_base": "http://localhost:4000",
                "api_key": "",
                "default_model": "gpt-4o",
            },
        },
        "routing_strategy": "single",
    },
    "agents": {
        "default": {
            "provider": "litellm_proxy",
            "temperature": 0.7,
        },
    },
    "synthesizer": {
        "provider": "litellm_proxy",
        "temperature": 0.3,
    },
    "output": {
        "format": "markdown",
        "directory": "reports",
        "include_raw_transcripts": False,
    },
    "human_in_the_loop": {
        "enabled": True,
        "checkpoint_frequency": "every_cycle",
        "pause_on_conflicts": True,
    },
    "ui": {
        "show_spinner": True,
        "color_enabled": True,
        "verbose": False,
    },
}


def load_config(config_path: str = "config.yaml") -> Dict[str, Any]:
    """
    Load configuration from YAML file.

    Args:
        config_path: Path to configuration file

    Returns:
        Configuration dictionary
    """
    # Start with default config
    config = DEFAULT_CONFIG.copy()

    # Check if config file exists
    path = Path(config_path)
    if not path.exists():
        console.print(f"[yellow]Warning: Config file not found: {config_path}[/]")
        console.print("[yellow]Using default configuration[/]")
        return config

    try:
        with open(path, "r") as f:
            user_config = yaml.safe_load(f)

        if user_config:
            # Merge user config with defaults
            config = _merge_configs(config, user_config)

    except Exception as e:
        console.print(f"[red]Error loading config: {str(e)}[/]")
        console.print("[yellow]Using default configuration[/]")
        return config

    # Resolve environment variable placeholders
    config = _resolve_env_placeholders(config)

    return config


def _resolve_env_placeholders(obj: Any) -> Any:
    """
    Recursively resolve environment variable placeholders in config.
    
    Supports:
      - ${VAR_NAME} -> value of VAR_NAME or empty string if not set
      - ${VAR_NAME:-default} -> value of VAR_NAME or 'default' if not set
    """
    if isinstance(obj, dict):
        return {k: _resolve_env_placeholders(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_resolve_env_placeholders(item) for item in obj]
    elif isinstance(obj, str):
        return _resolve_placeholder_in_string(obj)
    else:
        return obj


def _resolve_placeholder_in_string(value: str) -> str:
    """Replace ${VAR} or ${VAR:-default} with environment variable values."""
    def replace(match):
        content = match.group(1)
        if ':-' in content:
            var_name, default = content.split(':-', 1)
            return os.getenv(var_name, default)
        else:
            return os.getenv(content, '')
    
    return ENV_PLACEHOLDER_PATTERN.sub(replace, value)


def _merge_configs(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively merge configuration dictionaries"""
    result = base.copy()

    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _merge_configs(result[key], value)
        else:
            result[key] = value

    return result


def validate_config(config: Dict[str, Any]) -> bool:
    """
    Validate configuration.

    Args:
        config: Configuration dictionary

    Returns:
        True if valid, False otherwise
    """
    # Check required sections
    required_sections = ["research", "models", "output", "human_in_the_loop"]
    for section in required_sections:
        if section not in config:
            console.print(f"[red]Error: Missing required config section: {section}[/]")
            return False

    # Validate research settings
    research = config.get("research", {})
    if research.get("default_iterations", 0) < 1:
        console.print("[red]Error: default_iterations must be at least 1[/]")
        return False

    if research.get("min_iterations", 0) < 1:
        console.print("[red]Error: min_iterations must be at least 1[/]")
        return False

    if research.get("max_iterations", 0) < research.get("min_iterations", 0):
        console.print("[red]Error: max_iterations must be >= min_iterations[/]")
        return False

    return True


def get_provider_config(config: Dict[str, Any], provider_name: str) -> Dict[str, Any]:
    """
    Get provider configuration by name.
    
    Args:
        config: Full configuration
        provider_name: Provider name (e.g., 'qwen3-4b', 'stepfun')
    
    Returns:
        Provider configuration dict with api_base, api_key, default_model
    """
    providers = config.get("models", {}).get("providers", {})
    return providers.get(provider_name, {})


def get_enabled_providers(config: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """
    Get all enabled providers.
    
    Args:
        config: Full configuration
    
    Returns:
        Dict of provider_name -> provider_config for enabled providers only
    """
    providers = config.get("models", {}).get("providers", {})
    return {name: cfg for name, cfg in providers.items() if cfg.get("enabled", True)}


def get_orchestrator_provider(config: Dict[str, Any]) -> tuple[str, Dict[str, Any]]:
    """
    Get the orchestrator's provider name and config.
    
    Args:
        config: Full configuration
    
    Returns:
        Tuple of (provider_name, provider_config)
    """
    orch_config = config.get("orchestrator", {})
    provider_name = orch_config.get("provider")
    provider_config = get_provider_config(config, provider_name)
    return provider_name, provider_config


def get_agent_providers(config: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """
    Get provider configuration for spawned agents.
    
    Args:
        config: Full configuration
    
    Returns:
        Dict mapping agent type -> config with 'provider', 'temperature', etc.
        Currently only 'default' is supported.
    """
    return config.get("agents", {})


def ensure_output_directory(config: Dict[str, Any]) -> Path:
    """
    Ensure output directory exists.

    Args:
        config: Configuration

    Returns:
        Path to output directory
    """
    output_dir = config.get("output", {}).get("directory", "reports")
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path
