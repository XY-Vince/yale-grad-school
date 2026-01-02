"""
GameEngine - Central game controller.

Orchestrates all game systems: state management, event processing,
registries, and game loop execution.
"""

from __future__ import annotations
from typing import Dict, Optional, Any, Callable, TYPE_CHECKING
from pathlib import Path
import random
import yaml

from gradquest.core.variable_store import VariableStore
from gradquest.core.expression_parser import ExpressionParser, create_parser
from gradquest.core.registries import AttributeRegistry, ItemRegistry, StatusRegistry, ActiveStatus
from gradquest.core.event_engine import EventEngine, GameEvent, EventCondition, EventAction, EventActionContext, ActionResult


class EndGameState:
    """End game state information."""
    
    def __init__(self, won: bool, reason: str, message: str = ""):
        self.won = won
        self.reason = reason
        self.message = message


class GameEngine:
    """
    Central game controller orchestrating all game systems.
    
    Responsibilities:
    - Game state via VariableStore
    - Effect registries (Attributes, Items, Status)
    - Event engine integration
    - Game loop with tick() method
    - Win/lose condition checking
    - Game lifecycle management
    """
    
    # Default game settings
    DEFAULT_HOPE = 50
    DEFAULT_PAPERS_REQUIRED = 3
    TICK_INTERVAL_MS = 50  # Original game speed
    
    def __init__(self, data_path: Optional[Path] = None):
        """
        Initialize the game engine.
        
        Args:
            data_path: Path to the ruleset data directory
        """
        # Core systems
        self.variable_store = VariableStore()
        self.parser: Optional[ExpressionParser] = None
        self.event_engine: Optional[EventEngine] = None
        
        # Registries
        self.attribute_registry = AttributeRegistry()
        self.item_registry = ItemRegistry()
        self.status_registry = StatusRegistry()
        
        # Active status effects with duration tracking
        self._active_status: Dict[str, ActiveStatus] = {}
        
        # Data path
        self.data_path = data_path or Path(__file__).parent.parent.parent / "data" / "rulesets" / "default"
        
        # Game state
        self._running = False
        self._ended = False
        self._end_state: Optional[EndGameState] = None
        self._random_seed: Optional[int] = None
        self._rng: Optional[random.Random] = None
        
        # Callbacks for UI
        self._on_message: Optional[Callable[[str], None]] = None
        self._on_choice: Optional[Callable[[list], int]] = None
        self._on_state_update: Optional[Callable[[], None]] = None
        
        # Initialize random
        self._rng = random.Random()
    
    def set_random_seed(self, seed: int) -> None:
        """Set the random seed for reproducible gameplay."""
        self._random_seed = seed
        self._rng = random.Random(seed)
    
    def _random(self) -> float:
        """Get a random float in [0, 1)."""
        return self._rng.random() if self._rng else random.random()
    
    # ==================== Callbacks ====================
    
    def on_message(self, callback: Callable[[str], None]) -> None:
        """Set callback for displaying messages."""
        self._on_message = callback
    
    def on_choice(self, callback: Callable[[list], int]) -> None:
        """Set callback for choice selection."""
        self._on_choice = callback
    
    def on_state_update(self, callback: Callable[[], None]) -> None:
        """Set callback for state updates."""
        self._on_state_update = callback
    
    # ==================== Data Loading ====================
    
    def load_game_data(self) -> None:
        """Load all game data from YAML files."""
        # Load attributes
        attr_path = self.data_path / "attributes.yaml"
        if attr_path.exists():
            with open(attr_path, 'r') as f:
                data = yaml.safe_load(f)
                if data:
                    self.attribute_registry.load_from_yaml(data)
        
        # Load items
        items_path = self.data_path / "items.yaml"
        if items_path.exists():
            with open(items_path, 'r') as f:
                data = yaml.safe_load(f)
                if data:
                    self.item_registry.load_from_yaml(data)
        
        # Load status effects
        status_path = self.data_path / "status.yaml"
        if status_path.exists():
            with open(status_path, 'r') as f:
                data = yaml.safe_load(f)
                if data:
                    self.status_registry.load_from_yaml(data)
        
        # Initialize expression parser
        self.parser = create_parser(
            variable_store=self.variable_store,
            event_engine=None,  # Will be set after event engine is created
            random_seed=self._random_seed
        )
        
        # Initialize event engine
        self.event_engine = EventEngine(self.variable_store, self.parser)
        self.event_engine.set_random_func(self._random)
        
        # Update parser with event engine reference
        self.parser.context['event_engine'] = self.event_engine
        
        # Register action handlers
        self._register_action_handlers()
        
        # Load events
        events_path = self.data_path / "events.yaml"
        if events_path.exists():
            self._load_events(events_path)
    
    def _load_events(self, path: Path) -> None:
        """Load events from YAML file."""
        with open(path, 'r') as f:
            data = yaml.safe_load(f)
        
        if not data:
            return
        
        for event_data in data:
            # Parse conditions
            conditions = []
            for cond_data in event_data.get('conditions', []):
                cond = EventCondition(
                    id=cond_data.get('id', 'Expression'),
                    expression=cond_data.get('expression', 'true')
                )
                conditions.append(cond)
            
            # Parse actions
            actions = []
            for action_data in event_data.get('actions', []):
                action = EventAction(
                    id=action_data.get('id', 'Unknown'),
                    params={k: v for k, v in action_data.items() if k != 'id'}
                )
                actions.append(action)
            
            # Create event
            event = GameEvent(
                id=event_data['id'],
                trigger=event_data.get('trigger', 'Manual'),
                actions=actions,
                conditions=conditions,
                probability=event_data.get('probability', 1.0),
                once=event_data.get('once', False),
                priority=event_data.get('priority', 0),
                exclusions=event_data.get('exclusions', []),
            )
            
            self.event_engine.register_event(event)
    
    def _register_action_handlers(self) -> None:
        """Register all action handlers with the event engine."""
        if not self.event_engine:
            return
        
        self.event_engine.register_action_handler('DisplayMessage', self._action_display_message)
        self.event_engine.register_action_handler('DisplayChoices', self._action_display_choices)
        self.event_engine.register_action_handler('UpdateVariable', self._action_update_variable)
        self.event_engine.register_action_handler('UpdateVariables', self._action_update_variables)
        self.event_engine.register_action_handler('GiveItem', self._action_give_item)
        self.event_engine.register_action_handler('RemoveItem', self._action_remove_item)
        self.event_engine.register_action_handler('SetStatus', self._action_set_status)
        self.event_engine.register_action_handler('RemoveStatus', self._action_remove_status)
        self.event_engine.register_action_handler('TriggerEvents', self._action_trigger_events)
        self.event_engine.register_action_handler('EndGame', self._action_end_game)
        self.event_engine.register_action_handler('EnableEvent', self._action_enable_event)
        self.event_engine.register_action_handler('DisableEvent', self._action_disable_event)
        self.event_engine.register_action_handler('CoinFlip', self._action_coin_flip)
        self.event_engine.register_action_handler('Random', self._action_random)
        self.event_engine.register_action_handler('Switch', self._action_switch)
    
    # ==================== Action Handlers ====================
    
    def _action_display_message(self, action: EventAction, context: EventActionContext) -> None:
        """Display a message to the player."""
        message = action.params.get('message', '')
        message = self._interpolate_text(message)
        context.display_message(message)
    
    def _action_display_choices(self, action: EventAction, context: EventActionContext) -> None:
        """Display choices to the player."""
        choices = action.params.get('choices', [])
        context.display_choices(choices)
    
    def _action_update_variable(self, action: EventAction, context: EventActionContext) -> None:
        """Update a single variable."""
        var_name = action.params.get('variable', '')
        value_expr = action.params.get('value', '0')
        
        if self.parser:
            value = self.parser.evaluate(str(value_expr))
            self.variable_store.set_var(var_name, float(value))
    
    def _action_update_variables(self, action: EventAction, context: EventActionContext) -> None:
        """Update multiple variables."""
        updates = action.params.get('updates', [])
        for update in updates:
            var_name = update.get('variable', '')
            value_expr = update.get('value', '0')
            
            if self.parser:
                value = self.parser.evaluate(str(value_expr))
                self.variable_store.set_var(var_name, float(value))
    
    def _action_give_item(self, action: EventAction, context: EventActionContext) -> None:
        """Give an item to the player."""
        item_id = action.params.get('item', '')
        count = action.params.get('count', 1)
        self.variable_store.add_item(item_id, count)
    
    def _action_remove_item(self, action: EventAction, context: EventActionContext) -> None:
        """Remove an item from the player."""
        item_id = action.params.get('item', '')
        count = action.params.get('count', 1)
        self.variable_store.remove_item(item_id, count)
    
    def _action_set_status(self, action: EventAction, context: EventActionContext) -> None:
        """Apply a status effect."""
        status_id = action.params.get('status', '')
        definition = self.status_registry.get(status_id)
        
        if definition:
            self._active_status[status_id] = ActiveStatus(definition)
            self.variable_store.add_status(status_id)
    
    def _action_remove_status(self, action: EventAction, context: EventActionContext) -> None:
        """Remove a status effect."""
        status_id = action.params.get('status', '')
        self._active_status.pop(status_id, None)
        self.variable_store.remove_status(status_id)
    
    def _action_trigger_events(self, action: EventAction, context: EventActionContext) -> None:
        """Trigger events by trigger ID."""
        trigger_id = action.params.get('trigger', '')
        probability = action.params.get('probability', 1.0)
        priority = action.params.get('priority', 0)
        
        if self.event_engine:
            self.event_engine.trigger(trigger_id, probability, priority)
    
    def _action_end_game(self, action: EventAction, context: EventActionContext) -> None:
        """End the game."""
        won = action.params.get('won', False)
        reason = action.params.get('reason', 'unknown')
        message = action.params.get('message', '')
        
        self._ended = True
        self._running = False
        self._end_state = EndGameState(won, reason, self._interpolate_text(message))
        context.stop_event()
    
    def _action_enable_event(self, action: EventAction, context: EventActionContext) -> None:
        """Enable an event."""
        event_id = action.params.get('event', '')
        if self.event_engine:
            self.event_engine.enable_event(event_id)
    
    def _action_disable_event(self, action: EventAction, context: EventActionContext) -> None:
        """Disable an event."""
        event_id = action.params.get('event', '')
        if self.event_engine:
            self.event_engine.disable_event(event_id)
    
    def _action_coin_flip(self, action: EventAction, context: EventActionContext) -> None:
        """Execute actions based on coin flip."""
        probability = action.params.get('probability', 0.5)
        
        if self._random() < probability:
            # Execute success actions
            success_actions = action.params.get('success', [])
            self._execute_nested_actions(success_actions, context)
        else:
            # Execute failure actions
            failure_actions = action.params.get('failure', [])
            self._execute_nested_actions(failure_actions, context)
    
    def _action_random(self, action: EventAction, context: EventActionContext) -> None:
        """Execute weighted random action."""
        options = action.params.get('options', [])
        
        total_weight = sum(opt.get('weight', 1) for opt in options)
        roll = self._random() * total_weight
        
        cumulative = 0
        for option in options:
            cumulative += option.get('weight', 1)
            if roll < cumulative:
                self._execute_nested_actions(option.get('actions', []), context)
                break
    
    def _action_switch(self, action: EventAction, context: EventActionContext) -> None:
        """Execute conditional switch."""
        cases = action.params.get('cases', [])
        default_actions = action.params.get('default', [])
        
        for case in cases:
            condition = case.get('condition', 'false')
            if self.parser and self.parser.evaluate(condition):
                self._execute_nested_actions(case.get('actions', []), context)
                return
        
        # No case matched, execute default
        self._execute_nested_actions(default_actions, context)
    
    def _execute_nested_actions(self, actions_data: list, context: EventActionContext) -> None:
        """Execute a list of nested actions."""
        for action_data in actions_data:
            action = EventAction(
                id=action_data.get('id', 'Unknown'),
                params={k: v for k, v in action_data.items() if k != 'id'}
            )
            handler = self.event_engine._action_handlers.get(action.id)
            if handler:
                handler(action, context)
    
    # ==================== Game Lifecycle ====================
    
    def start(self, new_seed: bool = True) -> None:
        """Start a new game."""
        # Reset state
        self.variable_store.reset()
        if self.event_engine:
            self.event_engine.reset()
        self._active_status.clear()
        self._ended = False
        self._end_state = None
        
        # Set random seed if requested
        if new_seed:
            self.set_random_seed(random.randint(0, 2**31))
        
        # Initialize game variables
        self._init_game_variables()
        
        # Start the game
        self._running = True
        
        # Trigger game start
        if self.event_engine:
            self.event_engine.trigger("GameStart", 1.0, 100)
    
    def _init_game_variables(self) -> None:
        """Initialize all game variables to starting values."""
        vs = self.variable_store
        
        # Set variable limits
        vs.set_var_limits('player.hope', 0, 100)
        vs.set_var_limits('advisor.happiness', 0, 100)
        vs.set_var_limits('month', 1, 12)
        vs.set_var_limits('year', 1, 100)
        
        # Initialize core variables
        vs.set_var('player.hope', self.DEFAULT_HOPE)
        vs.set_var('advisor.happiness', 50)
        vs.set_var('player.readPapers', 0)
        vs.set_var('player.qualifyLevel', 0)
        vs.set_var('player.experimentBoost', 0)
        
        # Time tracking
        vs.set_var('month', 9)  # Start in September
        vs.set_var('year', 1)
        vs.set_var('elapsedMonth', 0)
        
        # Game rules
        vs.set_var('rule.papersRequired', self.DEFAULT_PAPERS_REQUIRED)
        vs.set_var('rule.maxYear', 8)
    
    def tick(self) -> Optional[EventActionContext]:
        """
        Advance the game by one tick.
        
        Returns:
            EventActionContext if user interaction is needed, None otherwise.
        """
        if not self._running or self._ended:
            return None
        
        # Process pending triggers
        if self.event_engine and self.event_engine.has_pending_triggers():
            context = self.event_engine.process_next_trigger()
            if context and context.result == ActionResult.WAIT:
                return context
        
        return None
    
    def advance_month(self) -> None:
        """Advance the game by one month."""
        vs = self.variable_store
        
        month = int(vs.get_var('month'))
        year = int(vs.get_var('year'))
        
        month += 1
        if month > 12:
            month = 1
            year += 1
            vs.set_var('year', year)
        
        vs.set_var('month', month)
        vs.add_var('elapsedMonth', 1)
        
        # Tick status effects
        self._tick_status_effects()
        
        # Check win/lose conditions
        self._check_end_conditions()
        
        # Trigger month begin
        if self.event_engine and self._running:
            self.event_engine.trigger("MonthBegin", 1.0, 0)
    
    def _tick_status_effects(self) -> None:
        """Tick all active status effects."""
        expired = []
        
        for status_id, active in self._active_status.items():
            if not active.tick():
                expired.append(status_id)
        
        for status_id in expired:
            self._active_status.pop(status_id, None)
            self.variable_store.remove_status(status_id)
    
    def _check_end_conditions(self) -> None:
        """Check for win/lose conditions."""
        vs = self.variable_store
        
        # Lose: Hope reaches 0
        if vs.get_var('player.hope') <= 0:
            self._ended = True
            self._running = False
            self._end_state = EndGameState(False, "no_hope", "You've lost all hope...")
            return
        
        # Lose: Year limit exceeded
        max_year = vs.get_var('rule.maxYear')
        if vs.get_var('year') > max_year:
            self._ended = True
            self._running = False
            self._end_state = EndGameState(False, "overdue", "You've exceeded the time limit...")
            return
    
    def _interpolate_text(self, text: str) -> str:
        """Interpolate variables in text."""
        import re
        
        def replace_var(match):
            var_name = match.group(1)
            value = self.variable_store.get_var(var_name)
            if value == int(value):
                return str(int(value))
            return str(value)
        
        return re.sub(r'\{([a-zA-Z_.]+)\}', replace_var, text)
    
    # ==================== Accessors ====================
    
    @property
    def is_running(self) -> bool:
        """Check if the game is running."""
        return self._running
    
    @property
    def is_ended(self) -> bool:
        """Check if the game has ended."""
        return self._ended
    
    @property
    def end_state(self) -> Optional[EndGameState]:
        """Get the end game state."""
        return self._end_state
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current game statistics."""
        vs = self.variable_store
        return {
            'year': int(vs.get_var('year')),
            'month': int(vs.get_var('month')),
            'hope': int(vs.get_var('player.hope')),
            'advisor_happiness': int(vs.get_var('advisor.happiness')),
            'papers_published': vs.get_item_count('paper'),
            'papers_required': int(vs.get_var('rule.papersRequired')),
            'items': vs.get_all_items(),
            'status': list(vs.get_all_status()),
        }
