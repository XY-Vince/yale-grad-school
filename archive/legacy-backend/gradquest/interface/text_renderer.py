"""
TextRenderer - Text rendering with variable interpolation.

Provides text display with variable interpolation and localization.
"""

from __future__ import annotations
from typing import Dict, Optional, Callable, Any
import re


class TextRenderer:
    """
    Renders text with variable interpolation and localization.
    
    Features:
    - Variable interpolation: {variable.name}
    - Localization key lookup
    - Number formatting
    """
    
    def __init__(self):
        self._lang: Dict[str, str] = {}
        self._var_getter: Optional[Callable[[str], Any]] = None
        self._item_getter: Optional[Callable[[str], int]] = None
    
    def set_lang(self, lang: Dict[str, str]) -> None:
        """Set localization dictionary."""
        self._lang = lang
    
    def set_variable_getter(self, getter: Callable[[str], Any]) -> None:
        """Set function to get variable values."""
        self._var_getter = getter
    
    def set_item_getter(self, getter: Callable[[str], int]) -> None:
        """Set function to get item counts."""
        self._item_getter = getter
    
    def get_text(self, key: str, default: Optional[str] = None) -> str:
        """
        Get localized text by key.
        
        Args:
            key: Localization key
            default: Default text if key not found
            
        Returns:
            Localized text
        """
        return self._lang.get(key, default or key)
    
    def render(self, text: str) -> str:
        """
        Render text with variable interpolation.
        
        Supports:
        - {variable.name} - Variable values
        - {item:itemName} - Item counts
        - {key:langKey} - Localization lookup
        
        Args:
            text: Text with interpolation placeholders
            
        Returns:
            Rendered text
        """
        # First, resolve localization keys
        text = self._resolve_lang_keys(text)
        
        # Then, interpolate variables
        text = self._interpolate_variables(text)
        
        return text
    
    def _resolve_lang_keys(self, text: str) -> str:
        """Resolve {key:langKey} patterns."""
        def replace_key(match):
            lang_key = match.group(1)
            return self._lang.get(lang_key, lang_key)
        
        return re.sub(r'\{key:([a-zA-Z0-9_.]+)\}', replace_key, text)
    
    def _interpolate_variables(self, text: str) -> str:
        """Interpolate {variable} patterns."""
        def replace_var(match):
            var_name = match.group(1)
            
            # Check for item prefix
            if var_name.startswith('item:'):
                item_id = var_name[5:]
                if self._item_getter:
                    return str(self._item_getter(item_id))
                return "0"
            
            # Regular variable
            if self._var_getter:
                value = self._var_getter(var_name)
                if value is None:
                    return var_name
                if isinstance(value, float) and value == int(value):
                    return str(int(value))
                return str(value)
            
            return var_name
        
        return re.sub(r'\{([a-zA-Z0-9_.:]+)\}', replace_var, text)
    
    def format_number(self, value: float, decimals: int = 0) -> str:
        """Format a number for display."""
        if decimals == 0:
            return str(int(value))
        return f"{value:.{decimals}f}"
    
    def format_duration(self, months: float) -> str:
        """Format a duration in months for display."""
        if months == float('inf'):
            return "Permanent"
        
        years = int(months // 12)
        remaining_months = int(months % 12)
        
        parts = []
        if years > 0:
            parts.append(f"{years} year{'s' if years != 1 else ''}")
        if remaining_months > 0:
            parts.append(f"{remaining_months} month{'s' if remaining_months != 1 else ''}")
        
        return ", ".join(parts) if parts else "0 months"
