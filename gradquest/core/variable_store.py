"""
VariableStore - Centralized game state variable management.

Provides dictionary-based storage for numeric variables, items, and status effects
with clamping, change observation, and JSON serialization support.
"""

from __future__ import annotations
from typing import Dict, Set, Tuple, Callable, Optional, Any
import json
import math


class VariableStore:
    """
    Centralized storage for all game state variables.
    
    Features:
    - Numeric variables with min/max clamping
    - Item counting (inventory)
    - Status effect tracking
    - Observable change events
    - JSON serialization for save/load
    """
    
    def __init__(self):
        # Numeric variables (e.g., player.hope, year, month)
        self._vars: Dict[str, float] = {}
        
        # Variable limits for clamping (name -> (min, max))
        self._limits: Dict[str, Tuple[float, float]] = {}
        
        # Countable items (e.g., idea, paper, figure)
        self._items: Dict[str, int] = {}
        
        # Active status effects (e.g., exhaustion, unhappyAdvisor)
        self._status: Set[str] = set()
        
        # Change callback: called when any variable changes
        self._on_change: Optional[Callable[[str, float, float], None]] = None
        
        # Item change callback
        self._on_item_change: Optional[Callable[[str, int, int], None]] = None
        
        # Status change callback
        self._on_status_change: Optional[Callable[[str, bool], None]] = None
    
    # ==================== Variable Management ====================
    
    def set_var(self, name: str, value: float) -> None:
        """Set a variable value with automatic clamping."""
        old_value = self._vars.get(name, 0.0)
        
        # Apply limits if defined
        if name in self._limits:
            low, high = self._limits[name]
            value = max(low, min(high, value))
        
        self._vars[name] = value
        
        # Notify change
        if self._on_change and old_value != value:
            self._on_change(name, old_value, value)
    
    def get_var(self, name: str, default: float = 0.0) -> float:
        """Get a variable value, returning default if not set."""
        return self._vars.get(name, default)
    
    def has_var(self, name: str) -> bool:
        """Check if a variable exists."""
        return name in self._vars
    
    def set_var_limits(self, name: str, min_val: float, max_val: float) -> None:
        """Set min/max limits for a variable."""
        self._limits[name] = (min_val, max_val)
        
        # Re-clamp existing value if present
        if name in self._vars:
            self.set_var(name, self._vars[name])
    
    def add_var(self, name: str, delta: float) -> None:
        """Add to a variable value."""
        current = self.get_var(name)
        self.set_var(name, current + delta)
    
    def get_all_vars(self) -> Dict[str, float]:
        """Get a copy of all variables."""
        return self._vars.copy()
    
    # ==================== Item Management ====================
    
    def add_item(self, name: str, count: int = 1) -> None:
        """Add items to inventory."""
        old_count = self._items.get(name, 0)
        new_count = old_count + count
        self._items[name] = max(0, new_count)
        
        if self._on_item_change and old_count != self._items[name]:
            self._on_item_change(name, old_count, self._items[name])
    
    def remove_item(self, name: str, count: int = 1) -> bool:
        """Remove items from inventory. Returns True if successful."""
        current = self._items.get(name, 0)
        if current < count:
            return False
        self.add_item(name, -count)
        return True
    
    def get_item_count(self, name: str) -> int:
        """Get count of an item."""
        return self._items.get(name, 0)
    
    def has_item(self, name: str, count: int = 1) -> bool:
        """Check if player has at least 'count' of an item."""
        return self.get_item_count(name) >= count
    
    def clear_items(self, name: str) -> None:
        """Remove all of a specific item."""
        old_count = self._items.get(name, 0)
        self._items[name] = 0
        
        if self._on_item_change and old_count != 0:
            self._on_item_change(name, old_count, 0)
    
    def get_all_items(self) -> Dict[str, int]:
        """Get a copy of all items with non-zero counts."""
        return {k: v for k, v in self._items.items() if v > 0}
    
    # ==================== Status Management ====================
    
    def add_status(self, name: str) -> None:
        """Add a status effect."""
        if name not in self._status:
            self._status.add(name)
            if self._on_status_change:
                self._on_status_change(name, True)
    
    def remove_status(self, name: str) -> None:
        """Remove a status effect."""
        if name in self._status:
            self._status.discard(name)
            if self._on_status_change:
                self._on_status_change(name, False)
    
    def has_status(self, name: str) -> bool:
        """Check if a status effect is active."""
        return name in self._status
    
    def get_all_status(self) -> Set[str]:
        """Get a copy of all active status effects."""
        return self._status.copy()
    
    def clear_status(self) -> None:
        """Remove all status effects."""
        for status in list(self._status):
            self.remove_status(status)
    
    # ==================== Callbacks ====================
    
    def on_variable_changed(self, callback: Callable[[str, float, float], None]) -> None:
        """Set callback for variable changes: callback(name, old_value, new_value)"""
        self._on_change = callback
    
    def on_item_changed(self, callback: Callable[[str, int, int], None]) -> None:
        """Set callback for item changes: callback(name, old_count, new_count)"""
        self._on_item_change = callback
    
    def on_status_changed(self, callback: Callable[[str, bool], None]) -> None:
        """Set callback for status changes: callback(name, is_added)"""
        self._on_status_change = callback
    
    # ==================== Serialization ====================
    
    def to_json(self) -> str:
        """Serialize state to JSON string."""
        def encode_value(v: float) -> Any:
            if math.isinf(v):
                return "Infinity" if v > 0 else "-Infinity"
            if math.isnan(v):
                return "NaN"
            return v
        
        data = {
            "vars": {k: encode_value(v) for k, v in self._vars.items()},
            "items": self._items,
            "status": list(self._status),
            "limits": {k: list(v) for k, v in self._limits.items()}
        }
        return json.dumps(data, indent=2)
    
    def from_json(self, json_str: str) -> None:
        """Deserialize state from JSON string."""
        def decode_value(v: Any) -> float:
            if v == "Infinity":
                return float('inf')
            if v == "-Infinity":
                return float('-inf')
            if v == "NaN":
                return float('nan')
            return float(v)
        
        data = json.loads(json_str)
        
        self._limits = {k: tuple(v) for k, v in data.get("limits", {}).items()}
        self._vars = {k: decode_value(v) for k, v in data.get("vars", {}).items()}
        self._items = data.get("items", {})
        self._status = set(data.get("status", []))
    
    def reset(self) -> None:
        """Reset all state to initial values."""
        self._vars.clear()
        self._items.clear()
        self._status.clear()
        # Keep limits as they define the game rules
