"""
Actions - Event action handlers.

Provides action handler retrieval for event processing.
Actions are registered with the GameEngine; this module provides
utility functions for action handling.
"""

from __future__ import annotations
from typing import Dict, Callable, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from gradquest.core.event_engine import EventAction, EventActionContext


# Action handler type
ActionHandler = Callable[['EventAction', 'EventActionContext'], None]

# Registry of custom action handlers
_custom_handlers: Dict[str, ActionHandler] = {}


def register_action_handler(action_id: str, handler: ActionHandler) -> None:
    """
    Register a custom action handler.
    
    Args:
        action_id: The action type ID
        handler: The handler function
    """
    _custom_handlers[action_id] = handler


def get_action_handler(action_id: str) -> ActionHandler | None:
    """
    Get a registered action handler.
    
    Args:
        action_id: The action type ID
        
    Returns:
        The handler function or None if not found
    """
    return _custom_handlers.get(action_id)


def has_action_handler(action_id: str) -> bool:
    """Check if an action handler is registered."""
    return action_id in _custom_handlers


def clear_action_handlers() -> None:
    """Clear all registered action handlers."""
    _custom_handlers.clear()
