"""
Unit tests for GradQuest core engine.

Run with: pytest tests/
"""

import pytest
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from gradquest.core.variable_store import VariableStore


class TestVariableStore:
    """Tests for VariableStore functionality."""
    
    def test_basic_set_get(self):
        """Test basic variable set and get."""
        vs = VariableStore()
        vs.set_var('test.value', 42)
        assert vs.get_var('test.value') == 42
    
    def test_add_var(self):
        """Test adding to existing variable."""
        vs = VariableStore()
        vs.set_var('player.hope', 50)
        vs.add_var('player.hope', 10)
        assert vs.get_var('player.hope') == 60
    
    def test_default_value(self):
        """Test default value for non-existent variable."""
        vs = VariableStore()
        assert vs.get_var('nonexistent', 99) == 99
    
    def test_items(self):
        """Test item count management."""
        vs = VariableStore()
        vs.add_item('idea', 3)
        assert vs.get_item_count('idea') == 3
        vs.remove_item('idea', 1)
        assert vs.get_item_count('idea') == 2
    
    def test_items_no_negative(self):
        """Test that removing more items than available doesn't crash."""
        vs = VariableStore()
        vs.add_item('paper', 1)
        vs.remove_item('paper', 5)
        # Should at least not crash, count behavior may vary
        count = vs.get_item_count('paper')
        assert count >= 0
    
    def test_status_effects(self):
        """Test status effect management."""
        vs = VariableStore()
        vs.add_status('exhaustion')
        assert vs.has_status('exhaustion') == True
        vs.remove_status('exhaustion')
        assert vs.has_status('exhaustion') == False
    
    def test_get_all_items(self):
        """Test getting all items."""
        vs = VariableStore()
        vs.add_item('idea', 2)
        vs.add_item('paper', 1)
        items = vs.get_all_items()
        assert items.get('idea') == 2
        assert items.get('paper') == 1
    
    def test_get_all_status(self):
        """Test getting all statuses."""
        vs = VariableStore()
        vs.add_status('exhaustion')
        vs.add_status('firstYear')
        statuses = vs.get_all_status()
        assert 'exhaustion' in statuses
        assert 'firstYear' in statuses


class TestIntegration:
    """Integration tests for game engine."""
    
    def test_game_engine_loads(self):
        """Test that game engine loads correctly."""
        from gradquest.core.game_engine import GameEngine
        
        data_path = Path(__file__).parent.parent / 'data' / 'rulesets' / 'default'
        engine = GameEngine(data_path)
        engine.load_game_data()
        
        # Should have loaded events
        assert len(engine.event_engine.get_all_events()) > 0
    
    def test_game_can_start(self):
        """Test that a game can be started."""
        from gradquest.core.game_engine import GameEngine
        
        data_path = Path(__file__).parent.parent / 'data' / 'rulesets' / 'default'
        engine = GameEngine(data_path)
        engine.load_game_data()
        engine.start()
        
        # Game should be running
        assert engine._running == True
        assert engine.variable_store.get_var('year') == 1
        assert engine.variable_store.get_var('month') == 9
    
    def test_advance_month(self):
        """Test advancing the month."""
        from gradquest.core.game_engine import GameEngine
        
        data_path = Path(__file__).parent.parent / 'data' / 'rulesets' / 'default'
        engine = GameEngine(data_path)
        engine.load_game_data()
        engine.start()
        
        initial_month = engine.variable_store.get_var('month')
        engine.advance_month()
        
        # Month should have advanced
        new_month = engine.variable_store.get_var('month')
        assert new_month == initial_month + 1 or (initial_month == 12 and new_month == 1)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
