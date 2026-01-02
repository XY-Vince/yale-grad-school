"""
Status - Status effect system.

Provides status effects that modify attributes and expire over time.
"""

from __future__ import annotations
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field


@dataclass
class StatusEffect:
    """A modifier applied by a status."""
    attribute: str
    value: float
    operation: str = "add"  # add, multiply


@dataclass
class Status:
    """A status effect definition."""
    id: str
    name: str
    description: str = ""
    duration: float = float('inf')  # months, inf = permanent
    effects: List[StatusEffect] = field(default_factory=list)
    icon: str = "⚡"
    
    def is_permanent(self) -> bool:
        """Check if this status is permanent."""
        return self.duration == float('inf')


class ActiveStatus:
    """An active instance of a status effect."""
    
    def __init__(self, status: Status):
        self.status = status
        self.remaining_duration = status.duration
    
    @property
    def id(self) -> str:
        return self.status.id
    
    @property
    def name(self) -> str:
        return self.status.name
    
    def tick(self, months: float = 1.0) -> bool:
        """
        Advance time and check if still active.
        
        Returns:
            True if still active, False if expired
        """
        if self.status.is_permanent():
            return True
        
        self.remaining_duration -= months
        return self.remaining_duration > 0
    
    def get_remaining_duration(self) -> float:
        """Get remaining duration in months."""
        return self.remaining_duration if not self.status.is_permanent() else float('inf')


class StatusManager:
    """
    Manages active status effects.
    
    Features:
    - Apply/remove status effects
    - Duration tracking
    - Effect application
    - Tick processing
    """
    
    def __init__(self):
        self._definitions: Dict[str, Status] = {}  # status_id -> Status
        self._active: Dict[str, ActiveStatus] = {}  # status_id -> ActiveStatus
        self._on_added: Optional[Callable[[Status], None]] = None
        self._on_removed: Optional[Callable[[Status], None]] = None
    
    def register_status(self, status: Status) -> None:
        """Register a status definition."""
        self._definitions[status.id] = status
    
    def apply(self, status_id: str) -> bool:
        """
        Apply a status effect.
        
        Returns:
            True if status was applied, False if already active or not found
        """
        if status_id in self._active:
            # Refresh duration if already active
            status = self._definitions.get(status_id)
            if status:
                self._active[status_id] = ActiveStatus(status)
            return True
        
        status = self._definitions.get(status_id)
        if not status:
            return False
        
        self._active[status_id] = ActiveStatus(status)
        
        if self._on_added:
            self._on_added(status)
        
        return True
    
    def remove(self, status_id: str) -> bool:
        """
        Remove a status effect.
        
        Returns:
            True if removed, False if not active
        """
        active = self._active.pop(status_id, None)
        if not active:
            return False
        
        if self._on_removed:
            self._on_removed(active.status)
        
        return True
    
    def has(self, status_id: str) -> bool:
        """Check if a status is active."""
        return status_id in self._active
    
    def get(self, status_id: str) -> Optional[ActiveStatus]:
        """Get an active status."""
        return self._active.get(status_id)
    
    def tick(self, months: float = 1.0) -> List[str]:
        """
        Advance time for all active statuses.
        
        Returns:
            List of expired status IDs
        """
        expired = []
        
        for status_id, active in list(self._active.items()):
            if not active.tick(months):
                expired.append(status_id)
        
        for status_id in expired:
            self.remove(status_id)
        
        return expired
    
    def get_all_active(self) -> Dict[str, ActiveStatus]:
        """Get all active statuses."""
        return self._active.copy()
    
    def get_total_effect(self, attribute: str) -> float:
        """
        Calculate total effect on an attribute from all active statuses.
        
        Returns the additive total of all effects on the attribute.
        """
        total = 0.0
        
        for active in self._active.values():
            for effect in active.status.effects:
                if effect.attribute == attribute:
                    if effect.operation == "add":
                        total += effect.value
                    # Note: multiply would need different handling
        
        return total
    
    def clear(self) -> None:
        """Remove all active statuses."""
        for status_id in list(self._active.keys()):
            self.remove(status_id)
    
    def on_status_added(self, callback: Callable[[Status], None]) -> None:
        """Set callback for when a status is added."""
        self._on_added = callback
    
    def on_status_removed(self, callback: Callable[[Status], None]) -> None:
        """Set callback for when a status is removed."""
        self._on_removed = callback
    
    def __iter__(self):
        """Iterate over active status IDs."""
        return iter(self._active.keys())
    
    def __len__(self):
        """Get number of active statuses."""
        return len(self._active)
