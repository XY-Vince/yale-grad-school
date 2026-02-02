"""
CLI - Command-line interface for GradQuest.

Provides a terminal-based interface for playing the game.
"""

from __future__ import annotations
from typing import Dict, List, Optional, TYPE_CHECKING
import os
import sys

from gradquest.interface.text_renderer import TextRenderer

if TYPE_CHECKING:
    from gradquest.core.game_engine import GameEngine


class CLI:
    """
    Command-line interface for GradQuest.
    
    Features:
    - Stats display (year, month, hope)
    - Message rendering
    - Choice selection
    - Item/status display
    """
    
    # Month names
    MONTHS = [
        "", "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    ]
    
    # Hope bar characters
    HOPE_FULL = "█"
    HOPE_EMPTY = "░"
    HOPE_WIDTH = 20
    
    def __init__(self, engine: GameEngine):
        self.engine = engine
        self.renderer = TextRenderer()
        
        # Set up renderer with engine
        self.renderer.set_variable_getter(
            lambda name: engine.variable_store.get_var(name)
        )
        self.renderer.set_item_getter(
            lambda name: engine.variable_store.get_item_count(name)
        )
    
    def clear_screen(self) -> None:
        """Clear the terminal screen."""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def print_header(self) -> None:
        """Print the game header."""
        print("=" * 60)
        print("                    🎓 GRADQUEST 🎓")
        print("              A PhD Life Simulator")
        print("=" * 60)
    
    def print_stats(self) -> None:
        """Print current game statistics."""
        stats = self.engine.get_stats()
        
        year = stats['year']
        month = stats['month']
        hope = stats['hope']
        
        month_name = self.MONTHS[month] if 1 <= month <= 12 else "???"
        
        # Hope bar
        filled = int((hope / 100) * self.HOPE_WIDTH)
        empty = self.HOPE_WIDTH - filled
        hope_bar = self.HOPE_FULL * filled + self.HOPE_EMPTY * empty
        
        # Hope color (would need colorama for actual colors)
        if hope <= 20:
            hope_indicator = "⚠️ CRITICAL"
        elif hope <= 40:
            hope_indicator = "😰 Low"
        elif hope <= 60:
            hope_indicator = "😐 OK"
        elif hope <= 80:
            hope_indicator = "🙂 Good"
        else:
            hope_indicator = "😊 Great"
        
        print("-" * 60)
        print(f"  📅 Year {year}, {month_name}")
        print(f"  💪 Morale: [{hope_bar}] {hope}% {hope_indicator}")
        print(f"  📰 Papers: {stats['papers_published']}/{stats['papers_required']} required")
        print("-" * 60)
    
    def print_items(self) -> None:
        """Print current items."""
        items = self.engine.variable_store.get_all_items()
        
        if items:
            print("\n📦 Inventory:")
            for item_id, count in items.items():
                item_name = self._format_item_name(item_id)
                print(f"   • {item_name} x{count}")
    
    def print_status_effects(self) -> None:
        """Print active status effects."""
        status = self.engine.variable_store.get_all_status()
        
        if status:
            print("\n⚡ Status Effects:")
            for status_id in status:
                status_name = self._format_status_name(status_id)
                print(f"   • {status_name}")
    
    def _format_item_name(self, item_id: str) -> str:
        """Format an item ID as a display name."""
        # Convert snake_case to Title Case
        return item_id.replace('_', ' ').title()
    
    def _format_status_name(self, status_id: str) -> str:
        """Format a status ID as a display name."""
        return status_id.replace('_', ' ').title()
    
    def display_message(self, message: str) -> None:
        """Display a message to the player."""
        rendered = self.renderer.render(message)
        
        print("\n" + "=" * 60)
        # Word wrap
        words = rendered.split()
        line = ""
        for word in words:
            if len(line) + len(word) + 1 > 56:
                print("  " + line)
                line = word
            else:
                line = line + " " + word if line else word
        if line:
            print("  " + line)
        print("=" * 60)
    
    def display_choices(self, choices: List[Dict]) -> int:
        """
        Display choices and get player selection.
        
        Args:
            choices: List of choice dictionaries with 'text' key
            
        Returns:
            Index of selected choice (0-based)
        """
        print("\nWhat do you want to do?\n")
        
        for i, choice in enumerate(choices, 1):
            text = choice.get('text', choice.get('message', f'Option {i}'))
            rendered = self.renderer.render(text)
            print(f"  [{i}] {rendered}")
        
        print()
        
        while True:
            try:
                user_input = input("Enter your choice: ").strip()
                choice_num = int(user_input)
                
                if 1 <= choice_num <= len(choices):
                    return choice_num - 1
                else:
                    print(f"Please enter a number between 1 and {len(choices)}")
            except ValueError:
                print("Please enter a valid number")
            except (EOFError, KeyboardInterrupt):
                print("\nExiting...")
                sys.exit(0)
    
    def get_confirmation(self, prompt: str = "Press Enter to continue...") -> None:
        """Wait for user confirmation."""
        try:
            input(prompt)
        except (EOFError, KeyboardInterrupt):
            pass
    
    def display_end_game(self) -> None:
        """Display the end game screen."""
        end_state = self.engine.end_state
        
        self.clear_screen()
        print("\n" + "=" * 60)
        
        if end_state.won:
            print("       🎉🎓 CONGRATULATIONS! 🎓🎉")
            print("         You've completed your PhD!")
        else:
            print("          💔 GAME OVER 💔")
        
        print("=" * 60)
        
        if end_state.message:
            print(f"\n{end_state.message}")
        
        # Print final stats
        stats = self.engine.get_stats()
        print(f"\n📊 Final Statistics:")
        print(f"   • Years in program: {stats['year']}")
        print(f"   • Papers published: {stats['papers_published']}")
        print(f"   • Final hope: {stats['hope']}%")
        
        print("\n" + "=" * 60)
    
    def show_menu(self) -> str:
        """
        Show the main action menu and get player choice.
        
        Returns:
            Action key selected by player
        """
        actions = self._get_available_actions()
        
        print("\n📋 Actions:")
        for i, (key, name) in enumerate(actions, 1):
            print(f"  [{i}] {name}")
        
        print()
        
        while True:
            try:
                user_input = input("Choose action: ").strip()
                choice_num = int(user_input)
                
                if 1 <= choice_num <= len(actions):
                    return actions[choice_num - 1][0]
                else:
                    print(f"Please enter a number between 1 and {len(actions)}")
            except ValueError:
                print("Please enter a valid number")
            except (EOFError, KeyboardInterrupt):
                return "quit"
    
    def _get_available_actions(self) -> List[tuple]:
        """Get list of available actions based on game state."""
        vs = self.engine.variable_store
        actions = []
        
        # Research actions
        if vs.get_item_count('idea') == 0:
            actions.append(('read', '📚 Read Papers'))
        
        if vs.get_item_count('idea') > 0:
            actions.append(('work_idea', '💡 Work on Idea'))
        
        if vs.get_item_count('preliminary_result') > 0:
            actions.append(('work_preliminary', '🔬 Work on Preliminary Result'))
        
        if vs.get_item_count('major_result') > 0 and not vs.has_status('brokenEquipment'):
            actions.append(('work_figures', '📊 Work on Figures'))
        
        if vs.get_item_count('major_result') > 0 and vs.get_item_count('figure') >= 3:
            actions.append(('write_paper', '📝 Write Paper'))
        
        if vs.get_item_count('rejected_paper') > 0:
            actions.append(('revise', '✏️ Revise Rejected Paper'))
        
        # V1.2: Thesis action when player has enough papers
        papers_required = int(vs.get_var('rule.papersRequired'))
        if vs.get_item_count('paper') >= papers_required:
            actions.append(('thesis', '🎓 Work on Thesis'))
        
        # Other actions
        actions.append(('slack', '😴 Slack Off'))
        
        # Qual prep: available until September year 2 (when exam happens)
        year = vs.get_var('year')
        month = vs.get_var('month')
        quals_not_yet = (year == 1) or (year == 2 and month < 9)
        if quals_not_yet:
            current_level = int(vs.get_var('player.qualifyLevel'))
            actions.append(('quals', f'📖 Prepare for Quals ({current_level}/3)'))
        
        actions.append(('advance', '⏩ Advance to Next Month'))
        actions.append(('quit', '🚪 Quit Game'))
        
        return actions
    
    def run(self) -> None:
        """Run the main game loop."""
        self.clear_screen()
        self.print_header()
        
        # Start game
        self.engine.start()
        
        while self.engine.is_running:
            # Process pending events
            while True:
                context = self.engine.tick()
                
                if context is None:
                    break
                
                # Handle user interaction
                if context.pending_message:
                    self.display_message(context.pending_message)
                    self.get_confirmation()
                
                if context.pending_choices:
                    choice = self.display_choices(context.pending_choices)
                    self.engine.event_engine.continue_event(context, choice)
            
            # Check if game ended
            if self.engine.is_ended:
                break
            
            # Show current state
            self.clear_screen()
            self.print_header()
            self.print_stats()
            self.print_items()
            self.print_status_effects()
            
            # Get player action
            action = self.show_menu()
            
            self._process_action(action)
        
        # Game over
        self.display_end_game()
    
    def _process_action(self, action: str) -> None:
        """Process a player action."""
        if action == 'quit':
            print("\nThanks for playing!")
            sys.exit(0)
        
        elif action == 'advance':
            self.engine.advance_month()
        
        elif action == 'read':
            self._action_read_papers()
        
        elif action == 'work_idea':
            self._action_work_on('idea', 'preliminary_result', 0.45)
        
        elif action == 'work_preliminary':
            self._action_work_on('preliminary_result', 'major_result', 0.35)
        
        elif action == 'work_figures':
            self._action_work_figures()
        
        elif action == 'write_paper':
            self._action_write_paper()
        
        elif action == 'revise':
            self._action_revise_paper()
        
        elif action == 'slack':
            self._action_slack_off()
        
        elif action == 'quals':
            self._action_prepare_quals()
        
        elif action == 'thesis':
            self._action_work_on_thesis()
        
        # Advance time after action (except thesis which handles its own flow)
        if action not in ('advance', 'quit', 'thesis'):
            self.engine.advance_month()
    
    def _action_read_papers(self) -> None:
        """Player reads papers."""
        vs = self.engine.variable_store
        
        vs.add_var('player.readPapers', 1)
        
        # Chance to get idea (40%)
        if self.engine._random() < 0.4:
            vs.add_item('idea', 1)
            self.display_message("💡 After reading several papers, you have a new research idea!")
        else:
            self.display_message("📚 You read some papers. No ideas yet, but you're learning...")
        
        # Lower chance for exhaustion (5%)
        if self.engine._random() < 0.05:
            vs.add_status('exhaustion')
            self.display_message("😫 All that reading has left you exhausted...")
        
        self.get_confirmation()
    
    def _action_work_on(self, consume: str, produce: str, success_chance: float) -> None:
        """Generic work action that converts items."""
        vs = self.engine.variable_store
        
        # Apply experiment boost
        boost = vs.get_var('player.experimentBoost', 0)
        chance = min(1.0, success_chance + boost)
        
        if self.engine._random() < chance:
            vs.remove_item(consume, 1)
            vs.add_item(produce, 1)
            produce_name = produce.replace('_', ' ').title()
            self.display_message(f"🎉 Success! You've made a {produce_name}!")
        else:
            self.display_message("😔 You worked hard but didn't make progress this month...")
        
        self.get_confirmation()
    
    def _action_work_figures(self) -> None:
        """Work on figures."""
        vs = self.engine.variable_store
        
        # Figure creation (60%)
        if self.engine._random() < 0.6:
            vs.add_item('figure', 1)
            figure_count = vs.get_item_count('figure')
            self.display_message(f"📊 You created a figure! ({figure_count}/3 needed for paper)")
        else:
            self.display_message("😔 The figures didn't come out right. Try again next month...")
        
        # Random equipment breakdown (5%)
        if self.engine._random() < 0.05:
            vs.add_status('brokenEquipment')
            self.display_message("⚠️ Oh no! Your equipment just broke down!")
        
        self.get_confirmation()
    
    def _action_write_paper(self) -> None:
        """Write and submit a paper."""
        vs = self.engine.variable_store
        
        # Consume resources
        vs.remove_item('major_result', 1)
        vs.remove_item('figure', 3)
        
        self.display_message("📝 You've submitted your paper for review...")
        self.get_confirmation()
        
        # Review process (60% accept, 40% reject)
        if self.engine._random() < 0.6:
            vs.add_item('paper', 1)
            paper_count = vs.get_item_count('paper')
            papers_needed = int(vs.get_var('rule.papersRequired'))
            
            self.display_message(
                f"🎉 ACCEPTED! Your paper has been published! "
                f"({paper_count}/{papers_needed} complete)"
            )
            
            # Check win condition
            if paper_count >= papers_needed:
                if self.engine.event_engine:
                    self.engine.event_engine.trigger("ThesisReady", 1.0, 100)
        else:
            vs.add_item('rejected_paper', 1)
            self.display_message(
                "😢 REJECTED. The reviewers were not convinced... "
                "You can revise and resubmit."
            )
        
        self.get_confirmation()
    
    def _action_revise_paper(self) -> None:
        """Revise and resubmit a rejected paper."""
        vs = self.engine.variable_store
        
        vs.remove_item('rejected_paper', 1)
        
        self.display_message("✏️ You've revised your paper and resubmitted...")
        self.get_confirmation()
        
        # Higher chance on revision
        if self.engine._random() < 0.7:
            vs.add_item('paper', 1)
            paper_count = vs.get_item_count('paper')
            papers_needed = int(vs.get_var('rule.papersRequired'))
            
            self.display_message(
                f"🎉 ACCEPTED on revision! ({paper_count}/{papers_needed} complete)"
            )
            
            if paper_count >= papers_needed:
                if self.engine.event_engine:
                    self.engine.event_engine.trigger("ThesisReady", 1.0, 100)
        else:
            vs.add_item('rejected_paper', 1)
            self.display_message("😢 Rejected again... Keep trying!")
        
        self.get_confirmation()
    
    def _action_slack_off(self) -> None:
        """Player slacks off."""
        vs = self.engine.variable_store
        
        # Recover morale
        hope_gain = 5 + int(self.engine._random() * 10)
        vs.add_var('player.hope', hope_gain)
        
        self.display_message(f"😌 You took some time to relax. (+{hope_gain} morale)")
        
        # Chance to recover from exhaustion (35%)
        if vs.has_status('exhaustion') and self.engine._random() < 0.35:
            vs.remove_status('exhaustion')
            self.display_message("💆 You're feeling refreshed! Exhaustion has faded.")
        
        # Chance to recover advisor relationship (25%)
        if vs.has_status('unhappyAdvisor') and self.engine._random() < 0.25:
            vs.remove_status('unhappyAdvisor')
            self.display_message("🤝 Your advisor seems to have cooled down.")
        
        # Smaller chance to anger advisor (10%)
        if not vs.has_status('unhappyAdvisor') and self.engine._random() < 0.1:
            vs.add_status('unhappyAdvisor')
            self.display_message("😠 Your advisor noticed you weren't working...")
        
        self.get_confirmation()
    
    def _action_prepare_quals(self) -> None:
        """Prepare for qualifying exam."""
        vs = self.engine.variable_store
        # V1.4: Randomize qual prep - adds 0-2 points per session
        points_gained = int(self.engine._random() * 3)  # 0, 1, or 2
        vs.add_var('player.qualifyLevel', points_gained)
        level = int(vs.get_var('player.qualifyLevel'))
        
        if points_gained == 0:
            self.display_message(f"📖 You studied but didn't retain much. (Preparation: {level}/3)")
        elif points_gained == 1:
            self.display_message(f"📖 Decent study session! (Preparation: {level}/3)")
        else:
            self.display_message(f"📖 Great progress! (Preparation: {level}/3)")
        self.get_confirmation()
    
    def _action_work_on_thesis(self) -> None:
        """Work on thesis and defend - V1.2 addition."""
        vs = self.engine.variable_store
        
        papers = vs.get_item_count('paper')
        papers_required = int(vs.get_var('rule.papersRequired'))
        
        self.display_message(
            f"📚 You have {papers} papers published ({papers_required} required).\n"
            "It's time to write your thesis and defend!"
        )
        self.get_confirmation()
        
        # Choice: defend or stay
        choices = [
            {"text": "Write the thesis and defend"},
            {"text": "Stay for another year of research"}
        ]
        
        choice = self.display_choices(choices)
        
        if choice == 0:  # Defend
            self.display_message("📖 After months of writing, you're ready to defend...")
            self.get_confirmation()
            
            # 90% success rate for defense
            if self.engine._random() < 0.9:
                self.display_message(
                    "🎓🎉 CONGRATULATIONS, DOCTOR! 🎉🎓\n\n"
                    "You've successfully defended your thesis and earned your PhD!"
                )
                self.get_confirmation()
                
                # End the game - win!
                from gradquest.core.game_engine import EndGameState
                self.engine._ended = True
                self.engine._running = False
                self.engine._end_state = EndGameState(True, "graduation", "You are now Dr. You!")
            else:
                self.display_message(
                    "😅 The defense was rough, but you passed with major revisions!"
                )
                self.get_confirmation()
                
                # Still win, just with a different message
                from gradquest.core.game_engine import EndGameState
                self.engine._ended = True
                self.engine._running = False
                self.engine._end_state = EndGameState(True, "graduation", "It wasn't easy, but you made it!")
        else:  # Stay
            self.display_message(
                "You decide to stay and do more research. Your advisor is pleased."
            )
            vs.add_var('player.hope', 20)
            self.get_confirmation()
            self.engine.advance_month()

