"""
Conditions - Event condition evaluation.

Provides condition evaluation functions for event processing.
"""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from gradquest.core.expression_parser import ExpressionParser


def evaluate_condition(expression: str, parser: ExpressionParser) -> bool:
    """
    Evaluate a condition expression.
    
    Args:
        expression: The condition expression to evaluate
        parser: ExpressionParser instance with game context
        
    Returns:
        True if condition is met, False otherwise
    """
    try:
        result = parser.evaluate(expression)
        return bool(result)
    except Exception:
        # On evaluation error, condition fails
        return False


def evaluate_probability(probability: float, random_func) -> bool:
    """
    Evaluate a probability check.
    
    Args:
        probability: Probability value between 0 and 1
        random_func: Function that returns random float in [0, 1)
        
    Returns:
        True if probability check passes
    """
    if probability >= 1.0:
        return True
    if probability <= 0.0:
        return False
    return random_func() < probability
