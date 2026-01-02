"""
GradQuest - Main entry point.

A PhD life simulator game.
"""

from __future__ import annotations
import argparse
import sys
from pathlib import Path


def main():
    """Main entry point for GradQuest."""
    parser = argparse.ArgumentParser(
        description="GradQuest - A PhD Life Simulator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python -m gradquest.main           # Start the game
    python -m gradquest.main --seed 42 # Start with specific seed
    python -m gradquest.main --ruleset custom  # Use custom ruleset
        """
    )
    
    parser.add_argument(
        '--seed', '-s',
        type=int,
        default=None,
        help='Random seed for reproducible gameplay'
    )
    
    parser.add_argument(
        '--ruleset', '-r',
        type=str,
        default='default',
        help='Ruleset to use (default: default)'
    )
    
    parser.add_argument(
        '--data-path', '-d',
        type=str,
        default=None,
        help='Path to data directory'
    )
    
    parser.add_argument(
        '--version', '-v',
        action='store_true',
        help='Show version and exit'
    )
    
    args = parser.parse_args()
    
    if args.version:
        from gradquest import __version__
        print(f"GradQuest v{__version__}")
        sys.exit(0)
    
    # Determine data path
    if args.data_path:
        data_path = Path(args.data_path)
    else:
        # Look for data directory relative to package
        package_dir = Path(__file__).parent.parent
        data_path = package_dir / 'data' / 'rulesets' / args.ruleset
    
    if not data_path.exists():
        print(f"Error: Ruleset not found: {data_path}")
        sys.exit(1)
    
    # Import and run game
    try:
        from gradquest.core.game_engine import GameEngine
        from gradquest.interface.cli import CLI
        
        # Initialize game engine
        engine = GameEngine(data_path)
        
        # Set seed if provided
        if args.seed is not None:
            engine.set_random_seed(args.seed)
        
        # Load game data
        engine.load_game_data()
        
        # Create and run CLI
        cli = CLI(engine)
        cli.run()
        
    except KeyboardInterrupt:
        print("\n\nThanks for playing GradQuest!")
        sys.exit(0)
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
