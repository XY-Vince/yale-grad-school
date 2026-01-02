"""
ExpressionParser - Safe expression evaluation for game logic.

Provides a secure parser that evaluates game expressions without using eval(),
supporting arithmetic, logical operators, and game-specific functions.
"""

from __future__ import annotations
from typing import Dict, Any, List, Optional, Callable, Union
from dataclasses import dataclass
from enum import Enum, auto
import re
import random


class TokenType(Enum):
    """Token types for the expression lexer."""
    NUMBER = auto()
    STRING = auto()
    IDENTIFIER = auto()
    OPERATOR = auto()
    LPAREN = auto()
    RPAREN = auto()
    COMMA = auto()
    EOF = auto()


@dataclass
class Token:
    """A single token from the expression."""
    type: TokenType
    value: Any
    position: int


class ExpressionParser:
    """
    Safe expression evaluator for game logic.
    
    Supported operators:
    - Arithmetic: +, -, *, /, %
    - Comparison: <, >, <=, >=, ===, !==
    - Logical: &&, ||, !
    
    Supported functions:
    - itemCount('item_name') - Get item count
    - hasStatus('status_name') - Check if status is active
    - randi(max) - Random integer [0, max)
    - min(a, b) - Minimum of two values
    - max(a, b) - Maximum of two values
    - floor(x) - Floor of x
    - clip(x, min, max) - Clamp x between min and max
    - eventOccurred('event_id') - Check if event has occurred
    - getAttributeValue('attr_name') - Get attribute value
    """
    
    # Regex patterns for tokenization
    TOKEN_PATTERNS = [
        (r'\s+', None),  # Skip whitespace
        (r'\d+\.?\d*', TokenType.NUMBER),
        (r"'[^']*'", TokenType.STRING),
        (r'"[^"]*"', TokenType.STRING),
        (r'[a-zA-Z_][a-zA-Z0-9_\.]*', TokenType.IDENTIFIER),
        (r'===|!==|<=|>=|&&|\|\||[+\-*/%<>!]', TokenType.OPERATOR),
        (r'\(', TokenType.LPAREN),
        (r'\)', TokenType.RPAREN),
        (r',', TokenType.COMMA),
    ]
    
    # Operator precedence (higher = tighter binding)
    PRECEDENCE = {
        '||': 1,
        '&&': 2,
        '===': 3, '!==': 3,
        '<': 4, '>': 4, '<=': 4, '>=': 4,
        '+': 5, '-': 5,
        '*': 6, '/': 6, '%': 6,
        '!': 7,
    }
    
    def __init__(self, context: Optional[Dict[str, Any]] = None):
        """
        Initialize the parser with a context for variable resolution.
        
        Args:
            context: Dictionary with:
                - variable_store: VariableStore instance
                - event_engine: EventEngine instance (optional)
                - random_func: Custom random function (optional)
        """
        self.context = context or {}
        self._tokens: List[Token] = []
        self._pos = 0
    
    def evaluate(self, expression: str) -> Union[float, bool]:
        """
        Evaluate an expression string and return the result.
        
        Args:
            expression: The expression to evaluate
            
        Returns:
            The result (float or bool)
        """
        self._tokenize(expression)
        self._pos = 0
        
        if not self._tokens:
            return 0.0
        
        result = self._parse_expression(0)
        return result
    
    def _tokenize(self, expression: str) -> None:
        """Tokenize the input expression."""
        self._tokens = []
        pos = 0
        
        while pos < len(expression):
            match = None
            for pattern, token_type in self.TOKEN_PATTERNS:
                regex = re.compile(pattern)
                match = regex.match(expression, pos)
                if match:
                    if token_type is not None:
                        value = match.group()
                        if token_type == TokenType.NUMBER:
                            value = float(value)
                        elif token_type == TokenType.STRING:
                            value = value[1:-1]  # Remove quotes
                        self._tokens.append(Token(token_type, value, pos))
                    pos = match.end()
                    break
            
            if not match:
                raise ValueError(f"Unexpected character at position {pos}: {expression[pos]}")
        
        self._tokens.append(Token(TokenType.EOF, None, pos))
    
    def _current(self) -> Token:
        """Get current token."""
        return self._tokens[self._pos] if self._pos < len(self._tokens) else self._tokens[-1]
    
    def _advance(self) -> Token:
        """Advance to next token and return the current one."""
        token = self._current()
        self._pos += 1
        return token
    
    def _parse_expression(self, min_precedence: int) -> Union[float, bool]:
        """Parse expression using precedence climbing."""
        left = self._parse_unary()
        
        while True:
            token = self._current()
            if token.type != TokenType.OPERATOR:
                break
            
            precedence = self.PRECEDENCE.get(token.value, 0)
            if precedence < min_precedence:
                break
            
            self._advance()
            right = self._parse_expression(precedence + 1)
            left = self._apply_binary_op(token.value, left, right)
        
        return left
    
    def _parse_unary(self) -> Union[float, bool]:
        """Parse unary expressions (!, -)."""
        token = self._current()
        
        if token.type == TokenType.OPERATOR and token.value == '!':
            self._advance()
            operand = self._parse_unary()
            return not bool(operand)
        
        if token.type == TokenType.OPERATOR and token.value == '-':
            self._advance()
            operand = self._parse_unary()
            return -float(operand)
        
        return self._parse_primary()
    
    def _parse_primary(self) -> Union[float, bool]:
        """Parse primary expressions (numbers, strings, identifiers, function calls)."""
        token = self._current()
        
        if token.type == TokenType.NUMBER:
            self._advance()
            return token.value
        
        if token.type == TokenType.STRING:
            self._advance()
            return token.value
        
        if token.type == TokenType.IDENTIFIER:
            self._advance()
            
            # Check for function call
            if self._current().type == TokenType.LPAREN:
                return self._parse_function_call(token.value)
            
            # Check for boolean literals
            if token.value == 'true':
                return True
            if token.value == 'false':
                return False
            
            # Variable reference
            return self._resolve_variable(token.value)
        
        if token.type == TokenType.LPAREN:
            self._advance()
            result = self._parse_expression(0)
            if self._current().type != TokenType.RPAREN:
                raise ValueError("Expected closing parenthesis")
            self._advance()
            return result
        
        raise ValueError(f"Unexpected token: {token}")
    
    def _parse_function_call(self, name: str) -> Union[float, bool]:
        """Parse a function call."""
        self._advance()  # consume (
        
        args = []
        while self._current().type != TokenType.RPAREN:
            args.append(self._parse_expression(0))
            if self._current().type == TokenType.COMMA:
                self._advance()
        
        self._advance()  # consume )
        
        return self._call_function(name, args)
    
    def _apply_binary_op(self, op: str, left: Any, right: Any) -> Union[float, bool]:
        """Apply a binary operator."""
        if op == '+':
            return float(left) + float(right)
        elif op == '-':
            return float(left) - float(right)
        elif op == '*':
            return float(left) * float(right)
        elif op == '/':
            return float(left) / float(right) if right != 0 else 0
        elif op == '%':
            return float(left) % float(right) if right != 0 else 0
        elif op == '<':
            return float(left) < float(right)
        elif op == '>':
            return float(left) > float(right)
        elif op == '<=':
            return float(left) <= float(right)
        elif op == '>=':
            return float(left) >= float(right)
        elif op == '===':
            return left == right
        elif op == '!==':
            return left != right
        elif op == '&&':
            return bool(left) and bool(right)
        elif op == '||':
            return bool(left) or bool(right)
        else:
            raise ValueError(f"Unknown operator: {op}")
    
    def _resolve_variable(self, name: str) -> float:
        """Resolve a variable name to its value."""
        variable_store = self.context.get('variable_store')
        if variable_store:
            return variable_store.get_var(name, 0.0)
        return 0.0
    
    def _call_function(self, name: str, args: List[Any]) -> Union[float, bool]:
        """Call a built-in game function."""
        variable_store = self.context.get('variable_store')
        event_engine = self.context.get('event_engine')
        random_func = self.context.get('random_func', random.random)
        
        if name == 'itemCount':
            if variable_store and len(args) >= 1:
                return variable_store.get_item_count(str(args[0]))
            return 0
        
        elif name == 'hasStatus':
            if variable_store and len(args) >= 1:
                return variable_store.has_status(str(args[0]))
            return False
        
        elif name == 'randi':
            max_val = int(args[0]) if args else 10
            return int(random_func() * max_val)
        
        elif name == 'min':
            if len(args) >= 2:
                return min(float(args[0]), float(args[1]))
            return float(args[0]) if args else 0
        
        elif name == 'max':
            if len(args) >= 2:
                return max(float(args[0]), float(args[1]))
            return float(args[0]) if args else 0
        
        elif name == 'floor':
            return float(int(args[0])) if args else 0
        
        elif name == 'clip':
            if len(args) >= 3:
                value, low, high = float(args[0]), float(args[1]), float(args[2])
                return max(low, min(high, value))
            return float(args[0]) if args else 0
        
        elif name == 'eventOccurred':
            if event_engine and len(args) >= 1:
                return event_engine.has_event_occurred(str(args[0]))
            return False
        
        elif name == 'getAttributeValue':
            # For now, attributes are stored as variables
            if variable_store and len(args) >= 1:
                return variable_store.get_var(str(args[0]), 0.0)
            return 0.0
        
        else:
            raise ValueError(f"Unknown function: {name}")


def create_parser(variable_store=None, event_engine=None, random_seed: Optional[int] = None) -> ExpressionParser:
    """
    Create an ExpressionParser with the given context.
    
    Args:
        variable_store: VariableStore instance for variable resolution
        event_engine: EventEngine instance for event queries
        random_seed: Optional seed for reproducible random numbers
    
    Returns:
        Configured ExpressionParser instance
    """
    if random_seed is not None:
        rng = random.Random(random_seed)
        random_func = rng.random
    else:
        random_func = random.random
    
    context = {
        'variable_store': variable_store,
        'event_engine': event_engine,
        'random_func': random_func,
    }
    
    return ExpressionParser(context)
