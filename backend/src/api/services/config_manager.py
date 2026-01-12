import json
import os
from typing import Dict, Any

# IMPORT LOGGER
from src.utils.logging_config import get_logger

logger = get_logger(__name__)

CONFIG_FILE_PATH = "config/config.json"

def load_config() -> Dict[str, Any]:
    """Load configuration from config.json."""
    if not os.path.exists(CONFIG_FILE_PATH):
        logger.warning(f"Config file not found at {CONFIG_FILE_PATH}. Using empty default.")
        return {}
    
    try:
        with open(CONFIG_FILE_PATH, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to decode JSON from {CONFIG_FILE_PATH}: {e}", exc_info=True)
        return {}
    except Exception as e:
        logger.error(f"Unexpected error loading config: {e}", exc_info=True)
        return {}

def save_config(config: Dict[str, Any]) -> None:
    """Save configuration to config.json."""
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(CONFIG_FILE_PATH), exist_ok=True)
        
        with open(CONFIG_FILE_PATH, 'w') as f:
            json.dump(config, f, indent=2)
        logger.info("Configuration saved successfully.")
    except Exception as e:
        logger.error(f"Failed to save configuration: {e}", exc_info=True)