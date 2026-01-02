"""
Event loader - Load events from YAML files.

Parses YAML event definitions and creates GameEvent objects.
"""

from __future__ import annotations
from typing import List, Dict, Any, Optional
from pathlib import Path
import yaml

from gradquest.core.event_engine import GameEvent, EventCondition, EventAction


def load_events(path: Path) -> List[GameEvent]:
    """
    Load events from a YAML file.
    
    Args:
        path: Path to the events YAML file
        
    Returns:
        List of GameEvent objects
    """
    if not path.exists():
        return []
    
    with open(path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    if not data:
        return []
    
    events = []
    for event_data in data:
        event = parse_event(event_data)
        if event:
            events.append(event)
    
    return events


def parse_event(data: Dict[str, Any]) -> Optional[GameEvent]:
    """
    Parse a single event from YAML data.
    
    Args:
        data: Event definition dictionary
        
    Returns:
        GameEvent object or None if invalid
    """
    if 'id' not in data:
        return None
    
    # Parse conditions
    conditions = []
    for cond_data in data.get('conditions', []):
        condition = parse_condition(cond_data)
        if condition:
            conditions.append(condition)
    
    # Parse actions
    actions = []
    for action_data in data.get('actions', []):
        action = parse_action(action_data)
        if action:
            actions.append(action)
    
    # Parse probability
    probability = data.get('probability', 1.0)
    if isinstance(probability, str):
        try:
            probability = float(probability)
        except ValueError:
            probability = 1.0
    
    # Parse duration special value
    event = GameEvent(
        id=data['id'],
        trigger=data.get('trigger', 'Manual'),
        actions=actions,
        conditions=conditions,
        probability=probability,
        once=data.get('once', False),
        priority=data.get('priority', 0),
        exclusions=data.get('exclusions', []),
    )
    
    return event


def parse_condition(data: Dict[str, Any]) -> Optional[EventCondition]:
    """Parse a condition from YAML data."""
    cond_id = data.get('id', 'Expression')
    expression = data.get('expression', 'true')
    
    return EventCondition(id=cond_id, expression=str(expression))


def parse_action(data: Dict[str, Any]) -> Optional[EventAction]:
    """Parse an action from YAML data."""
    action_id = data.get('id')
    if not action_id:
        return None
    
    # Extract all params except 'id'
    params = {k: v for k, v in data.items() if k != 'id'}
    
    return EventAction(id=action_id, params=params)


def load_lang(path: Path) -> Dict[str, str]:
    """
    Load localization strings from YAML.
    
    Args:
        path: Path to lang.yaml
        
    Returns:
        Dictionary of key -> translated string
    """
    if not path.exists():
        return {}
    
    with open(path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    if not data:
        return {}
    
    # Flatten nested structure
    result = {}
    _flatten_lang(data, '', result)
    return result


def _flatten_lang(data: Any, prefix: str, result: Dict[str, str]) -> None:
    """Recursively flatten nested language data."""
    if isinstance(data, dict):
        for key, value in data.items():
            new_prefix = f"{prefix}.{key}" if prefix else key
            _flatten_lang(value, new_prefix, result)
    elif isinstance(data, str):
        result[prefix] = data
