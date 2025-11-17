import json
import os
from typing import Dict, Any

CONFIG_FILE_PATH = "config/config.json"

def load_config() -> Dict[str, Any]:
    """Load configuration from config.json."""
    if not os.path.exists(CONFIG_FILE_PATH):
        return {}
    with open(CONFIG_FILE_PATH, 'r') as f:
        return json.load(f)

def save_config(config: Dict[str, Any]) -> None:
    """Save configuration to config.json."""
    with open(CONFIG_FILE_PATH, 'w') as f:
        json.dump(config, f, indent=2)