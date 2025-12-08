"""
Service layer for hook management operations.
"""

import os
import sys
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.engine import Engine

# Add parent directory to path to import baselinr
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

try:
    from baselinr.config.schema import HookConfig, BaselinrConfig
    from baselinr.events import EventBus, DataDriftDetected
    from baselinr.cli import _create_hook
    BASELINR_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Baselinr modules not available: {e}")
    BASELINR_AVAILABLE = False

from config_service import ConfigService

logger = logging.getLogger(__name__)


class HookService:
    """Service for hook management operations."""
    
    def __init__(self, config_service: ConfigService):
        """
        Initialize hook service.
        
        Args:
            config_service: ConfigService instance for loading/saving config
        """
        self.config_service = config_service
    
    def list_hooks(self) -> tuple[List[Dict[str, Any]], bool]:
        """
        List all hooks from configuration.
        
        Returns:
            Tuple of (list of hooks with IDs, hooks_enabled flag)
        """
        try:
            config = self.config_service.load_config()
            hooks_config = config.get("hooks", {})
            hooks_enabled = hooks_config.get("enabled", True)
            hooks_list = hooks_config.get("hooks", [])
            
            hooks_with_ids = []
            for idx, hook in enumerate(hooks_list):
                hooks_with_ids.append({
                    "id": str(idx),
                    "hook": hook,
                })
            
            return hooks_with_ids, hooks_enabled
        except Exception as e:
            logger.error(f"Failed to list hooks: {e}")
            return [], True
    
    def get_hook(self, hook_id: str) -> Optional[Dict[str, Any]]:
        """
        Get specific hook by ID.
        
        Args:
            hook_id: Hook identifier (array index as string)
            
        Returns:
            Hook dictionary with ID, or None if not found
        """
        try:
            hooks_list, _ = self.list_hooks()
            hook_id_int = int(hook_id)
            
            if hook_id_int < 0 or hook_id_int >= len(hooks_list):
                return None
            
            return hooks_list[hook_id_int]
        except (ValueError, IndexError) as e:
            logger.error(f"Invalid hook ID: {hook_id}, error: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to get hook: {e}")
            return None
    
    def save_hook(self, hook_id: Optional[str], hook_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Save hook (create or update).
        
        Args:
            hook_id: Hook identifier (None for new, string index for update)
            hook_config: Hook configuration dictionary
            
        Returns:
            Saved hook with ID
            
        Raises:
            ValueError: If hook config is invalid
            RuntimeError: If config save fails
        """
        if not BASELINR_AVAILABLE:
            raise RuntimeError("Baselinr modules not available")
        
        # Validate hook config
        try:
            validated_hook = HookConfig(**hook_config)
        except Exception as e:
            logger.error(f"Hook validation failed: {e}")
            raise ValueError(f"Invalid hook configuration: {e}")
        
        # Load current config
        config = self.config_service.load_config()
        
        # Ensure hooks section exists
        if "hooks" not in config:
            config["hooks"] = {"enabled": True, "hooks": []}
        if "hooks" not in config["hooks"]:
            config["hooks"]["hooks"] = []
        
        hooks_list = config["hooks"]["hooks"]
        
        # Convert validated hook back to dict
        hook_dict = validated_hook.model_dump(exclude_none=True)
        
        if hook_id is None:
            # Create new hook
            hooks_list.append(hook_dict)
            new_id = str(len(hooks_list) - 1)
        else:
            # Update existing hook
            hook_id_int = int(hook_id)
            if hook_id_int < 0 or hook_id_int >= len(hooks_list):
                raise ValueError(f"Hook ID out of range: {hook_id}")
            hooks_list[hook_id_int] = hook_dict
            new_id = hook_id
        
        # Save config
        try:
            saved_config = self.config_service.save_config(config)
            saved_hooks = saved_config.get("hooks", {}).get("hooks", [])
            
            if hook_id is None:
                saved_hook = saved_hooks[-1]
            else:
                saved_hook = saved_hooks[hook_id_int]
            
            return {
                "id": new_id,
                "hook": saved_hook,
            }
        except Exception as e:
            logger.error(f"Failed to save hook: {e}")
            raise RuntimeError(f"Failed to save hook: {e}")
    
    def delete_hook(self, hook_id: str) -> bool:
        """
        Delete hook by ID.
        
        Args:
            hook_id: Hook identifier (array index as string)
            
        Returns:
            True if deleted, False if not found
        """
        try:
            hook_id_int = int(hook_id)
            
            # Load current config
            config = self.config_service.load_config()
            
            # Ensure hooks section exists
            if "hooks" not in config:
                config["hooks"] = {"enabled": True, "hooks": []}
            if "hooks" not in config["hooks"]:
                config["hooks"]["hooks"] = []
            
            hooks_list = config["hooks"]["hooks"]
            
            if hook_id_int < 0 or hook_id_int >= len(hooks_list):
                return False
            
            # Remove hook
            hooks_list.pop(hook_id_int)
            
            # Save config
            self.config_service.save_config(config)
            
            return True
        except (ValueError, IndexError) as e:
            logger.error(f"Invalid hook ID: {hook_id}, error: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to delete hook: {e}")
            return False
    
    def set_hooks_enabled(self, enabled: bool) -> bool:
        """
        Set master switch for all hooks.
        
        Args:
            enabled: Whether hooks are enabled
            
        Returns:
            True if successful
        """
        try:
            config = self.config_service.load_config()
            
            # Ensure hooks section exists
            if "hooks" not in config:
                config["hooks"] = {"enabled": enabled, "hooks": []}
            else:
                config["hooks"]["enabled"] = enabled
            
            # Save config
            self.config_service.save_config(config)
            
            return True
        except Exception as e:
            logger.error(f"Failed to set hooks enabled: {e}")
            return False
    
    def test_hook(self, hook_config: Dict[str, Any]) -> tuple[bool, str, Optional[str], Optional[Dict[str, Any]]]:
        """
        Test hook by creating a test event and sending it through the hook.
        
        Args:
            hook_config: Hook configuration dictionary to test
            
        Returns:
            Tuple of (success, message, error, test_event)
        """
        if not BASELINR_AVAILABLE:
            return False, "Baselinr modules not available", "Baselinr modules not available", None
        
        try:
            # Validate hook config
            validated_hook = HookConfig(**hook_config)
            
            # Create hook instance
            hook = _create_hook(validated_hook)
            
            # Create test event
            test_event = DataDriftDetected(
                event_type="DataDriftDetected",
                timestamp=datetime.utcnow(),
                table="test_table",
                column="test_column",
                metric="mean",
                baseline_value=100.0,
                current_value=110.0,
                change_percent=10.0,
                drift_severity="medium",
                explanation="Test event for hook validation",
                metadata={}
            )
            
            # Send event through hook
            try:
                hook.handle_event(test_event)
                return True, "Hook test successful", None, test_event.to_dict()
            except Exception as e:
                error_msg = str(e)
                logger.error(f"Hook test failed: {error_msg}")
                return False, f"Hook test failed: {error_msg}", error_msg, test_event.to_dict()
        
        except ValueError as e:
            error_msg = f"Invalid hook configuration: {e}"
            logger.error(error_msg)
            return False, error_msg, error_msg, None
        except Exception as e:
            error_msg = f"Failed to test hook: {e}"
            logger.error(error_msg)
            return False, error_msg, str(e), None

