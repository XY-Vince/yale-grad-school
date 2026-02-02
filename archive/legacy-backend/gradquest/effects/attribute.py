"""
Attribute - Player and game attribute system.

Provides attribute definitions with base values and modifiers.
"""

from __future__ import annotations
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field


@dataclass
class AttributeModifier:
    """A modifier that affects an attribute value."""
    source: str  # What applied this modifier (e.g., status effect ID)
    value: float
    operation: str = "add"  # "add", "multiply", "set"
    priority: int = 0  # Higher priority applies later
    
    def apply(self, base_value: float) -> float:
        """Apply this modifier to a value."""
        if self.operation == "add":
            return base_value + self.value
        elif self.operation == "multiply":
            return base_value * self.value
        elif self.operation == "set":
            return self.value
        return base_value


class Attribute:
    """
    A player or game attribute with a base value and modifiers.
    
    Supports:
    - Base value
    - Stacking modifiers from various sources
    - Min/max clamping
    - Change callbacks
    """
    
    def __init__(
        self,
        id: str,
        name: str,
        base_value: float = 0.0,
        min_value: float = float('-inf'),
        max_value: float = float('inf'),
    ):
        self.id = id
        self.name = name
        self.base_value = base_value
        self.min_value = min_value
        self.max_value = max_value
        
        self._modifiers: List[AttributeModifier] = []
        self._cached_value: Optional[float] = None
        self._on_change: Optional[Callable[[float, float], None]] = None
    
    def add_modifier(self, modifier: AttributeModifier) -> None:
        """Add a modifier to this attribute."""
        self._modifiers.append(modifier)
        self._modifiers.sort(key=lambda m: m.priority)
        self._invalidate_cache()
    
    def remove_modifier(self, source: str) -> None:
        """Remove all modifiers from a source."""
        self._modifiers = [m for m in self._modifiers if m.source != source]
        self._invalidate_cache()
    
    def clear_modifiers(self) -> None:
        """Remove all modifiers."""
        self._modifiers.clear()
        self._invalidate_cache()
    
    @property
    def value(self) -> float:
        """Get the computed final value."""
        if self._cached_value is None:
            self._compute_value()
        return self._cached_value
    
    @value.setter
    def value(self, new_base: float) -> None:
        """Set the base value."""
        old_value = self.value
        self.base_value = new_base
        self._invalidate_cache()
        
        if self._on_change and old_value != self.value:
            self._on_change(old_value, self.value)
    
    def _compute_value(self) -> None:
        """Compute the final value with all modifiers."""
        result = self.base_value
        
        for modifier in self._modifiers:
            result = modifier.apply(result)
        
        # Clamp to limits
        result = max(self.min_value, min(self.max_value, result))
        
        self._cached_value = result
    
    def _invalidate_cache(self) -> None:
        """Invalidate the cached value."""
        old_value = self._cached_value
        self._cached_value = None
        
        # Notify if value changed
        if self._on_change and old_value is not None:
            new_value = self.value
            if old_value != new_value:
                self._on_change(old_value, new_value)
    
    def on_change(self, callback: Callable[[float, float], None]) -> None:
        """Set callback for value changes: callback(old_value, new_value)"""
        self._on_change = callback
    
    def get_modifiers(self) -> List[AttributeModifier]:
        """Get a copy of current modifiers."""
        return self._modifiers.copy()


class AttributeManager:
    """Manages a collection of attributes."""
    
    def __init__(self):
        self._attributes: Dict[str, Attribute] = {}
    
    def register(self, attribute: Attribute) -> None:
        """Register an attribute."""
        self._attributes[attribute.id] = attribute
    
    def get(self, id: str) -> Optional[Attribute]:
        """Get an attribute by ID."""
        return self._attributes.get(id)
    
    def get_value(self, id: str, default: float = 0.0) -> float:
        """Get an attribute's current value."""
        attr = self._attributes.get(id)
        return attr.value if attr else default
    
    def set_value(self, id: str, value: float) -> None:
        """Set an attribute's base value."""
        attr = self._attributes.get(id)
        if attr:
            attr.value = value
    
    def add_modifier(self, attr_id: str, modifier: AttributeModifier) -> None:
        """Add a modifier to an attribute."""
        attr = self._attributes.get(attr_id)
        if attr:
            attr.add_modifier(modifier)
    
    def remove_modifier(self, attr_id: str, source: str) -> None:
        """Remove modifiers from an attribute by source."""
        attr = self._attributes.get(attr_id)
        if attr:
            attr.remove_modifier(source)
    
    def get_all(self) -> Dict[str, Attribute]:
        """Get all attributes."""
        return self._attributes.copy()
    
    def reset(self) -> None:
        """Reset all attributes to base values and clear modifiers."""
        for attr in self._attributes.values():
            attr.clear_modifiers()
