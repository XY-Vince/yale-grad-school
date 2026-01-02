"""
Item - Inventory item system.

Provides item definitions and inventory management.
"""

from __future__ import annotations
from typing import Dict, Optional, Callable, List
from dataclasses import dataclass


@dataclass
class Item:
    """An item definition."""
    id: str
    name: str
    description: str = ""
    rarity: str = "common"  # common, uncommon, rare, legendary
    max_stack: int = -1  # -1 = unlimited
    icon: str = "📦"
    
    def can_stack(self, current: int, add: int = 1) -> bool:
        """Check if more items can be stacked."""
        if self.max_stack < 0:
            return True
        return current + add <= self.max_stack


class Inventory:
    """
    Player inventory for managing items.
    
    Features:
    - Add/remove items
    - Stack limits
    - Change callbacks
    - Iteration support
    """
    
    def __init__(self):
        self._items: Dict[str, int] = {}  # item_id -> count
        self._definitions: Dict[str, Item] = {}  # item_id -> Item definition
        self._on_change: Optional[Callable[[str, int, int], None]] = None
    
    def register_item(self, item: Item) -> None:
        """Register an item definition."""
        self._definitions[item.id] = item
    
    def add(self, item_id: str, count: int = 1) -> int:
        """
        Add items to inventory.
        
        Args:
            item_id: The item ID
            count: Number to add
            
        Returns:
            Number actually added (may be less if stack limit reached)
        """
        old_count = self._items.get(item_id, 0)
        definition = self._definitions.get(item_id)
        
        if definition and definition.max_stack >= 0:
            max_add = definition.max_stack - old_count
            count = min(count, max(0, max_add))
        
        new_count = old_count + count
        self._items[item_id] = new_count
        
        if self._on_change and old_count != new_count:
            self._on_change(item_id, old_count, new_count)
        
        return count
    
    def remove(self, item_id: str, count: int = 1) -> bool:
        """
        Remove items from inventory.
        
        Args:
            item_id: The item ID
            count: Number to remove
            
        Returns:
            True if successful, False if not enough items
        """
        old_count = self._items.get(item_id, 0)
        
        if old_count < count:
            return False
        
        new_count = old_count - count
        if new_count == 0:
            del self._items[item_id]
        else:
            self._items[item_id] = new_count
        
        if self._on_change:
            self._on_change(item_id, old_count, new_count)
        
        return True
    
    def get_count(self, item_id: str) -> int:
        """Get the count of an item."""
        return self._items.get(item_id, 0)
    
    def has(self, item_id: str, count: int = 1) -> bool:
        """Check if player has at least the specified count."""
        return self.get_count(item_id) >= count
    
    def clear(self, item_id: Optional[str] = None) -> None:
        """Clear items. If item_id is None, clear all."""
        if item_id:
            old_count = self._items.get(item_id, 0)
            if item_id in self._items:
                del self._items[item_id]
                if self._on_change:
                    self._on_change(item_id, old_count, 0)
        else:
            old_items = self._items.copy()
            self._items.clear()
            if self._on_change:
                for item_id, old_count in old_items.items():
                    self._on_change(item_id, old_count, 0)
    
    def get_all(self) -> Dict[str, int]:
        """Get all items with non-zero counts."""
        return {k: v for k, v in self._items.items() if v > 0}
    
    def get_all_with_definitions(self) -> List[tuple]:
        """Get all items with their definitions."""
        result = []
        for item_id, count in self._items.items():
            if count > 0:
                definition = self._definitions.get(item_id)
                result.append((item_id, count, definition))
        return result
    
    def on_change(self, callback: Callable[[str, int, int], None]) -> None:
        """Set callback for inventory changes: callback(item_id, old_count, new_count)"""
        self._on_change = callback
    
    def __iter__(self):
        """Iterate over item IDs with non-zero counts."""
        return iter(k for k, v in self._items.items() if v > 0)
    
    def __len__(self):
        """Get number of unique items."""
        return sum(1 for v in self._items.values() if v > 0)
