"""
EventEngine - Event processing system for game logic.

Provides a declarative event system with trigger queuing, condition evaluation,
probability-based execution, and action handling.
"""

from __future__ import annotations
from typing import Dict, List, Optional, Any, Set, Callable, TYPE_CHECKING
from dataclasses import dataclass, field
from enum import Enum
import heapq

if TYPE_CHECKING:
    from gradquest.core.expression_parser import ExpressionParser


class ActionResult(Enum):
    """Result of an action execution."""
    CONTINUE = "continue"  # Continue to next action
    STOP = "stop"  # Stop processing this event
    WAIT = "wait"  # Wait for user input


@dataclass
class EventCondition:
    """A condition that must be met for an event to fire."""
    id: str
    expression: str
    
    def evaluate(self, parser: ExpressionParser) -> bool:
        """Evaluate the condition using the expression parser."""
        try:
            result = parser.evaluate(self.expression)
            return bool(result)
        except Exception:
            return False


@dataclass
class EventAction:
    """An action to execute when an event fires."""
    id: str
    params: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        # Flatten params if they're nested under the action definition
        if not self.params:
            self.params = {}


@dataclass
class GameEvent:
    """A game event that can be triggered and executed."""
    id: str
    trigger: str  # Trigger that activates this event
    actions: List[EventAction] = field(default_factory=list)
    conditions: List[EventCondition] = field(default_factory=list)
    probability: float = 1.0  # Probability of execution (0-1)
    once: bool = False  # Fire only once per game
    priority: int = 0  # Higher priority events execute first
    exclusions: List[str] = field(default_factory=list)  # Events to disable after firing
    enabled: bool = True
    
    def check_conditions(self, parser: ExpressionParser) -> bool:
        """Check if all conditions are met."""
        return all(cond.evaluate(parser) for cond in self.conditions)


@dataclass
class TriggerEntry:
    """An entry in the trigger queue."""
    trigger_id: str
    probability: float
    priority: int
    sequence: int  # For stable sorting
    
    def __lt__(self, other: TriggerEntry) -> bool:
        # Higher priority first, then by sequence
        if self.priority != other.priority:
            return self.priority > other.priority
        return self.sequence < other.sequence


class EventActionContext:
    """Context passed to action handlers during execution."""
    
    def __init__(self, engine: EventEngine, event: GameEvent):
        self.engine = engine
        self.event = event
        self.variable_store = engine.variable_store
        self.parser = engine.parser
        self.result = ActionResult.CONTINUE
        
        # For user interaction
        self.pending_message: Optional[str] = None
        self.pending_choices: List[Dict[str, Any]] = []
        self.user_choice: Optional[int] = None
    
    def display_message(self, message: str, confirm_key: str = "OK") -> None:
        """Queue a message to display to the user."""
        self.pending_message = message
        self.result = ActionResult.WAIT
    
    def display_choices(self, choices: List[Dict[str, Any]]) -> None:
        """Queue choices for the user to select from."""
        self.pending_choices = choices
        self.result = ActionResult.WAIT
    
    def stop_event(self) -> None:
        """Stop processing the current event."""
        self.result = ActionResult.STOP


class EventEngine:
    """
    Event processing engine.
    
    Manages event registration, trigger queuing, condition evaluation,
    and action execution.
    """
    
    def __init__(self, variable_store, parser: ExpressionParser):
        self.variable_store = variable_store
        self.parser = parser
        
        # All registered events
        self._events: Dict[str, GameEvent] = {}
        
        # Events indexed by trigger
        self._trigger_index: Dict[str, List[str]] = {}
        
        # Disabled events
        self._disabled: Set[str] = set()
        
        # Events that have fired (for 'once' events)
        self._occurred: Set[str] = set()
        
        # Trigger queue (priority queue)
        self._trigger_queue: List[TriggerEntry] = []
        self._sequence_counter = 0
        
        # Action handlers
        self._action_handlers: Dict[str, Callable[[EventAction, EventActionContext], None]] = {}
        
        # Random function for probability checks
        self._random_func: Callable[[], float] = lambda: __import__('random').random()
    
    def set_random_func(self, func: Callable[[], float]) -> None:
        """Set the random function for probability checks."""
        self._random_func = func
    
    def register_event(self, event: GameEvent) -> None:
        """Register an event."""
        self._events[event.id] = event
        
        # Index by trigger
        if event.trigger not in self._trigger_index:
            self._trigger_index[event.trigger] = []
        self._trigger_index[event.trigger].append(event.id)
    
    def register_action_handler(
        self, 
        action_id: str, 
        handler: Callable[[EventAction, EventActionContext], None]
    ) -> None:
        """Register a handler for an action type."""
        self._action_handlers[action_id] = handler
    
    def enable_event(self, event_id: str) -> None:
        """Enable an event."""
        self._disabled.discard(event_id)
        if event_id in self._events:
            self._events[event_id].enabled = True
    
    def disable_event(self, event_id: str) -> None:
        """Disable an event."""
        self._disabled.add(event_id)
        if event_id in self._events:
            self._events[event_id].enabled = False
    
    def is_event_enabled(self, event_id: str) -> bool:
        """Check if an event is enabled."""
        return event_id not in self._disabled
    
    def has_event_occurred(self, event_id: str) -> bool:
        """Check if an event has occurred (fired at least once)."""
        return event_id in self._occurred
    
    def trigger(self, trigger_id: str, probability: float = 1.0, priority: int = 0) -> None:
        """Queue a trigger for processing."""
        entry = TriggerEntry(
            trigger_id=trigger_id,
            probability=probability,
            priority=priority,
            sequence=self._sequence_counter
        )
        self._sequence_counter += 1
        heapq.heappush(self._trigger_queue, entry)
    
    def has_pending_triggers(self) -> bool:
        """Check if there are pending triggers to process."""
        return len(self._trigger_queue) > 0
    
    def process_next_trigger(self) -> Optional[EventActionContext]:
        """
        Process the next trigger in the queue.
        
        Returns:
            EventActionContext if an event was processed and needs user interaction,
            None if no events need interaction or queue is empty.
        """
        if not self._trigger_queue:
            return None
        
        entry = heapq.heappop(self._trigger_queue)
        
        # Apply trigger probability
        if entry.probability < 1.0 and self._random_func() > entry.probability:
            return None
        
        # Get events for this trigger
        event_ids = self._trigger_index.get(entry.trigger_id, [])
        
        for event_id in event_ids:
            event = self._events.get(event_id)
            if not event:
                continue
            
            # Skip disabled events
            if not event.enabled or event_id in self._disabled:
                continue
            
            # Skip already-fired 'once' events
            if event.once and event_id in self._occurred:
                continue
            
            # Check conditions
            if not event.check_conditions(self.parser):
                continue
            
            # Apply event probability
            if event.probability < 1.0 and self._random_func() > event.probability:
                continue
            
            # Execute the event
            context = self._execute_event(event)
            
            # Mark as occurred
            self._occurred.add(event_id)
            
            # Handle exclusions
            for excluded_id in event.exclusions:
                self.disable_event(excluded_id)
            
            # Disable if 'once' event
            if event.once:
                self.disable_event(event_id)
            
            # Return context if user interaction needed
            if context.result == ActionResult.WAIT:
                return context
        
        return None
    
    def _execute_event(self, event: GameEvent) -> EventActionContext:
        """Execute all actions in an event."""
        context = EventActionContext(self, event)
        
        for action in event.actions:
            if context.result == ActionResult.STOP:
                break
            
            handler = self._action_handlers.get(action.id)
            if handler:
                handler(action, context)
            else:
                # Unknown action, log warning
                pass
        
        return context
    
    def continue_event(self, context: EventActionContext, choice: Optional[int] = None) -> EventActionContext:
        """
        Continue event execution after user interaction.
        
        Args:
            context: The context from the paused event
            choice: The user's choice (if applicable)
        
        Returns:
            Updated context
        """
        context.user_choice = choice
        context.result = ActionResult.CONTINUE
        context.pending_message = None
        context.pending_choices = []
        
        # Continue processing from where we left off
        # (In a full implementation, we'd track the action index)
        
        return context
    
    def reset(self) -> None:
        """Reset the event engine to initial state."""
        self._disabled.clear()
        self._occurred.clear()
        self._trigger_queue.clear()
        self._sequence_counter = 0
        
        # Re-enable all events
        for event in self._events.values():
            event.enabled = True
    
    def get_event(self, event_id: str) -> Optional[GameEvent]:
        """Get an event by ID."""
        return self._events.get(event_id)
    
    def get_all_events(self) -> List[GameEvent]:
        """Get all registered events."""
        return list(self._events.values())
