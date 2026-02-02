"""
Registries - Attribute, Item, and Status effect registries.

Provides registry pattern for managing game definitions loaded from YAML.
"""

from __future__ import annotations
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field


@dataclass
class AttributeDefinition:
    """Definition of a player/game attribute."""
    id: str
    name: str
    base_value: float = 0.0
    min_value: float = float('-inf')
    max_value: float = float('inf')
    description: str = ""
    
    def get_clamped_value(self, value: float) -> float:
        """Clamp value to valid range."""
        return max(self.min_value, min(self.max_value, value))


@dataclass
class ItemDefinition:
    """Definition of an inventory item."""
    id: str
    name: str
    description: str = ""
    rarity: str = "common"  # common, uncommon, rare
    max_count: int = -1  # -1 = unlimited
    icon: str = ""
    
    def can_add(self, current_count: int, add_count: int = 1) -> bool:
        """Check if more items can be added."""
        if self.max_count < 0:
            return True
        return current_count + add_count <= self.max_count


@dataclass 
class StatusModifier:
    """A modifier applied by a status effect."""
    attribute: str
    value: float
    operation: str = "add"  # add, multiply


@dataclass
class StatusDefinition:
    """Definition of a status effect."""
    id: str
    name: str
    description: str = ""
    duration: float = float('inf')  # months, Infinity = permanent
    modifiers: List[StatusModifier] = field(default_factory=list)
    icon: str = ""
    
    def is_permanent(self) -> bool:
        """Check if this is a permanent status."""
        return self.duration == float('inf')


class BaseRegistry:
    """Base registry class with common operations."""
    
    def __init__(self):
        self._items: Dict[str, Any] = {}
    
    def register(self, item: Any) -> None:
        """Register an item by its id."""
        self._items[item.id] = item
    
    def get(self, id: str) -> Optional[Any]:
        """Get an item by id."""
        return self._items.get(id)
    
    def has(self, id: str) -> bool:
        """Check if an item exists."""
        return id in self._items
    
    def get_all(self) -> List[Any]:
        """Get all registered items."""
        return list(self._items.values())
    
    def get_all_ids(self) -> List[str]:
        """Get all registered item IDs."""
        return list(self._items.keys())
    
    def clear(self) -> None:
        """Clear all registered items."""
        self._items.clear()
    
    def count(self) -> int:
        """Get number of registered items."""
        return len(self._items)


class AttributeRegistry(BaseRegistry):
    """Registry for player/game attributes."""
    
    def register(self, attr: AttributeDefinition) -> None:
        """Register an attribute definition."""
        super().register(attr)
    
    def get(self, id: str) -> Optional[AttributeDefinition]:
        """Get an attribute definition by id."""
        return super().get(id)
    
    def load_from_yaml(self, data: List[Dict[str, Any]]) -> None:
        """Load attributes from YAML data."""
        for attr_data in data:
            attr = AttributeDefinition(
                id=attr_data['id'],
                name=attr_data.get('name', attr_data['id']),
                base_value=attr_data.get('baseValue', 0.0),
                min_value=attr_data.get('minValue', float('-inf')),
                max_value=attr_data.get('maxValue', float('inf')),
                description=attr_data.get('description', ""),
            )
            self.register(attr)


class ItemRegistry(BaseRegistry):
    """Registry for inventory items."""
    
    def register(self, item: ItemDefinition) -> None:
        """Register an item definition."""
        super().register(item)
    
    def get(self, id: str) -> Optional[ItemDefinition]:
        """Get an item definition by id."""
        return super().get(id)
    
    def load_from_yaml(self, data: List[Dict[str, Any]]) -> None:
        """Load items from YAML data."""
        for item_data in data:
            item = ItemDefinition(
                id=item_data['id'],
                name=item_data.get('name', item_data['id']),
                description=item_data.get('description', ""),
                rarity=item_data.get('rarity', 'common'),
                max_count=item_data.get('maxCount', -1),
                icon=item_data.get('icon', ""),
            )
            self.register(item)


class StatusRegistry(BaseRegistry):
    """Registry for status effects."""
    
    def register(self, status: StatusDefinition) -> None:
        """Register a status definition."""
        super().register(status)
    
    def get(self, id: str) -> Optional[StatusDefinition]:
        """Get a status definition by id."""
        return super().get(id)
    
    def load_from_yaml(self, data: List[Dict[str, Any]]) -> None:
        """Load status effects from YAML data."""
        for status_data in data:
            modifiers = []
            for mod_data in status_data.get('modifiers', []):
                mod = StatusModifier(
                    attribute=mod_data['attribute'],
                    value=mod_data['value'],
                    operation=mod_data.get('operation', 'add'),
                )
                modifiers.append(mod)
            
            duration = status_data.get('duration', float('inf'))
            if duration == 'Infinity':
                duration = float('inf')
            
            status = StatusDefinition(
                id=status_data['id'],
                name=status_data.get('name', status_data['id']),
                description=status_data.get('description', ""),
                duration=duration,
                modifiers=modifiers,
                icon=status_data.get('icon', ""),
            )
            self.register(status)


class ActiveStatus:
    """Tracks an active status effect instance with remaining duration."""
    
    def __init__(self, definition: StatusDefinition):
        self.definition = definition
        self.remaining_duration = definition.duration
    
    def tick(self, months: float = 1.0) -> bool:
        """
        Advance time and check if status has expired.
        
        Returns:
            True if status is still active, False if expired
        """
        if self.definition.is_permanent():
            return True
        
        self.remaining_duration -= months
        return self.remaining_duration > 0
    
    @property
    def id(self) -> str:
        return self.definition.id
