"""
Configuration manager for bot configurations.
Handles saving/loading bot configs to/from YAML file.
"""

import yaml
import os
import uuid
from typing import Dict, Any, Optional
from datetime import datetime

class ConfigManager:
    def __init__(self, config_file: str = "botfather/bot_registry.yaml"):
        """Initialize config manager with config file path."""
        self.config_file = config_file
        self._ensure_config_file_exists()
    
    def _ensure_config_file_exists(self):
        """Create config file if it doesn't exist."""
        os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
        if not os.path.exists(self.config_file):
            self._save_config({})
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            print(f"Error loading config: {e}")
            return {}
    
    def _save_config(self, config: Dict[str, Any]):
        """Save configuration to YAML file."""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
        except Exception as e:
            print(f"Error saving config: {e}")
    
    def add_bot(self, bot_config: Dict[str, Any]) -> str:
        """Add a new bot configuration and return its ID."""
        config = self._load_config()
        bot_id = str(uuid.uuid4())[:8]  # Short UUID
        
        # Add metadata
        bot_config.update({
            'id': bot_id,
            'created_at': datetime.now().isoformat(),
            'active': False
        })
        
        config[bot_id] = bot_config
        self._save_config(config)
        return bot_id
    
    def get_bot(self, bot_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific bot configuration."""
        config = self._load_config()
        return config.get(bot_id)
    
    def get_user_bots(self, user_id: int) -> Dict[str, Dict[str, Any]]:
        """Get all bots belonging to a specific user."""
        config = self._load_config()
        user_bots = {}
        
        for bot_id, bot_config in config.items():
            if bot_config.get('owner_id') == user_id:
                user_bots[bot_id] = bot_config
        
        return user_bots
    
    def update_bot(self, bot_id: str, updates: Dict[str, Any]) -> bool:
        """Update a bot configuration."""
        config = self._load_config()
        
        if bot_id in config:
            config[bot_id].update(updates)
            config[bot_id]['updated_at'] = datetime.now().isoformat()
            self._save_config(config)
            return True
        
        return False
    
    def update_bot_status(self, bot_id: str, active: bool) -> bool:
        """Update bot's active status."""
        return self.update_bot(bot_id, {'active': active})
    
    def delete_bot(self, bot_id: str) -> bool:
        """Delete a bot configuration."""
        config = self._load_config()
        
        if bot_id in config:
            del config[bot_id]
            self._save_config(config)
            return True
        
        return False
    
    def get_all_bots(self) -> Dict[str, Dict[str, Any]]:
        """Get all bot configurations."""
        return self._load_config()
    
    def get_active_bots(self) -> Dict[str, Dict[str, Any]]:
        """Get all active bot configurations."""
        config = self._load_config()
        active_bots = {}
        
        for bot_id, bot_config in config.items():
            if bot_config.get('active', False):
                active_bots[bot_id] = bot_config
        
        return active_bots
