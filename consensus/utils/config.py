"""
Configuration Loader
Load and validate configuration files
"""

import os
from pathlib import Path
from typing import Any, Dict
import yaml

from consensus.ui import display_error, display_warning


DEFAULT_CONFIG = {
    "app": {
        "name": "Consensus-CLI",
        "version": "0.1.0",
    },
    "research": {
        "default_iterations": 5,
        "min_iterations": 3,
        "max_iterations": 10,
        "consensus_threshold": 0.85,
    },
    "models": {
        "proxy": {
            "api_base": "http://localhost:4000",
            "api_key": "",
        },
        "default_model": "gpt-4o",
        "agents": {
            "orchestrator": {
                "model": "gpt-4o",
                "temperature": 0.7,
            },
            "researcher": {
                "model": "gpt-4o",
                "temperature": 0.5,
            },
            "critic": {
                "model": "gpt-4o",
                "temperature": 0.9,
            },
            "architect": {
                "model": "gpt-4o",
                "temperature": 0.3,
            },
            "estimator": {
                "model": "gpt-4o",
                "temperature": 0.5,
            },
        },
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
        display_warning(f"Config file not found: {config_path}")
        display_warning("Using default configuration")
        return config

    try:
        with open(path, "r") as f:
            user_config = yaml.safe_load(f)

        if user_config:
            # Merge user config with defaults
            config = _merge_configs(config, user_config)

    except Exception as e:
        display_error(f"Error loading config: {str(e)}")
        display_warning("Using default configuration")
        return config

    return config


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
            display_error(f"Missing required config section: {section}")
            return False

    # Validate research settings
    research = config.get("research", {})
    if research.get("default_iterations", 0) < 1:
        display_error("default_iterations must be at least 1")
        return False

    if research.get("min_iterations", 0) < 1:
        display_error("min_iterations must be at least 1")
        return False

    if research.get("max_iterations", 0) < research.get("min_iterations", 0):
        display_error("max_iterations must be >= min_iterations")
        return False

    return True


def get_model_config(config: Dict[str, Any], agent: str) -> Dict[str, Any]:
    """
    Get model configuration for a specific agent.

    Args:
        config: Full configuration
        agent: Agent name

    Returns:
        Agent-specific model configuration
    """
    agents_config = config.get("models", {}).get("agents", {})
    return agents_config.get(agent, {})


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
