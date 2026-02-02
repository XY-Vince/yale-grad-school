"""
LLM Interface - Abstract interface for LLM API integration.

Provides an abstract base class for future LLM integration, enabling
dynamic content generation, enhanced narratives, and AI-driven game elements.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import os


@dataclass
class LLMConfig:
    """Configuration for LLM API connection."""
    provider: str = "mock"  # mock, openai, anthropic, local
    api_key: Optional[str] = None
    model: str = "gpt-4"
    temperature: float = 0.7
    max_tokens: int = 500
    base_url: Optional[str] = None
    
    @classmethod
    def from_env(cls) -> LLMConfig:
        """Create config from environment variables."""
        return cls(
            provider=os.getenv("GRADQUEST_LLM_PROVIDER", "mock"),
            api_key=os.getenv("GRADQUEST_LLM_API_KEY"),
            model=os.getenv("GRADQUEST_LLM_MODEL", "gpt-4"),
            temperature=float(os.getenv("GRADQUEST_LLM_TEMPERATURE", "0.7")),
            max_tokens=int(os.getenv("GRADQUEST_LLM_MAX_TOKENS", "500")),
            base_url=os.getenv("GRADQUEST_LLM_BASE_URL"),
        )


@dataclass
class GameContext:
    """Context information passed to LLM for generation."""
    year: int
    month: int
    hope: int
    papers_published: int
    papers_required: int
    items: Dict[str, int]
    status_effects: List[str]
    recent_events: List[str]
    player_history: List[str]


@dataclass
class LLMResponse:
    """Response from LLM generation."""
    text: str
    tokens_used: int = 0
    model: str = ""
    success: bool = True
    error: Optional[str] = None


class LLMInterface(ABC):
    """
    Abstract base class for LLM integration.
    
    Implement this interface to add LLM-powered features:
    - Dynamic event descriptions
    - Personalized advisor dialogue
    - Research paper topic generation
    - Procedural random events
    
    Usage:
        llm = OpenAILLM(config)
        response = llm.generate_response("Describe a failed experiment", context)
    """
    
    def __init__(self, config: LLMConfig):
        self.config = config
    
    @abstractmethod
    def generate_response(
        self, 
        prompt: str, 
        context: Optional[GameContext] = None
    ) -> LLMResponse:
        """
        Generate a text response based on a prompt.
        
        Args:
            prompt: The prompt to generate a response for
            context: Optional game context for personalization
            
        Returns:
            LLMResponse with generated text
        """
        pass
    
    @abstractmethod
    def generate_choices(
        self,
        scenario: str,
        num_choices: int = 3,
        context: Optional[GameContext] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate dynamic choices for a scenario.
        
        Args:
            scenario: Description of the current scenario
            num_choices: Number of choices to generate
            context: Optional game context
            
        Returns:
            List of choice dictionaries with 'text' and 'effects' keys
        """
        pass
    
    @abstractmethod
    def generate_event_description(
        self,
        event_type: str,
        context: Optional[GameContext] = None
    ) -> str:
        """
        Generate a description for a game event.
        
        Args:
            event_type: Type of event (e.g., 'paper_accepted', 'advisor_meeting')
            context: Optional game context
            
        Returns:
            Generated event description
        """
        pass
    
    @abstractmethod
    def generate_research_topic(
        self,
        field: str = "computational biology",
        context: Optional[GameContext] = None
    ) -> Dict[str, str]:
        """
        Generate a research topic for the player.
        
        Args:
            field: Research field
            context: Optional game context
            
        Returns:
            Dict with 'title', 'description', 'difficulty' keys
        """
        pass
    
    def is_available(self) -> bool:
        """Check if LLM is available and configured."""
        return self.config.api_key is not None or self.config.provider == "mock"


class MockLLM(LLMInterface):
    """
    Mock LLM implementation for offline play.
    
    Returns predefined responses without API calls.
    Useful for testing and when LLM is not configured.
    """
    
    # Predefined responses for various scenarios
    EVENT_DESCRIPTIONS = {
        'paper_accepted': [
            "The reviewers praised your thorough methodology!",
            "Your careful analysis impressed the editorial board.",
            "The paper's novel approach caught the reviewers' attention.",
        ],
        'paper_rejected': [
            "Reviewer 2 was particularly harsh this time...",
            "The reviewers requested major revisions to the methodology.",
            "The paper was deemed 'not a good fit' for this venue.",
        ],
        'advisor_meeting': [
            "Your advisor wants to discuss your research progress.",
            "Time for the weekly meeting with your advisor.",
            "Your advisor has some feedback on your latest work.",
        ],
        'equipment_broken': [
            "The lab equipment has seen better days...",
            "Something went wrong with the experimental setup.",
            "Technical difficulties have halted your experiments.",
        ],
    }
    
    CHOICE_TEMPLATES = [
        {"text": "Work harder on the problem", "effects": {"hope": -5, "progress": 10}},
        {"text": "Take a different approach", "effects": {"hope": 0, "progress": 5}},
        {"text": "Ask for help from a colleague", "effects": {"hope": 5, "progress": 5}},
    ]
    
    RESEARCH_TOPICS = [
        {"title": "Novel Algorithm for Protein Folding", "description": "Using ML to predict protein structures", "difficulty": "hard"},
        {"title": "Data Pipeline Optimization", "description": "Improving bioinformatics workflows", "difficulty": "medium"},
        {"title": "Literature Review Meta-Analysis", "description": "Synthesizing recent findings", "difficulty": "easy"},
    ]
    
    def __init__(self, config: Optional[LLMConfig] = None):
        super().__init__(config or LLMConfig())
        self._response_index = 0
    
    def generate_response(
        self, 
        prompt: str, 
        context: Optional[GameContext] = None
    ) -> LLMResponse:
        """Generate a mock response."""
        # Simple response based on prompt keywords
        if "experiment" in prompt.lower():
            text = "The experiment yielded unexpected results that warrant further investigation."
        elif "paper" in prompt.lower():
            text = "The paper discusses novel approaches to solving complex research challenges."
        elif "advisor" in prompt.lower():
            text = "Your advisor provides guidance on navigating the PhD journey."
        else:
            text = "You contemplate the mysteries of academic life..."
        
        return LLMResponse(text=text, success=True)
    
    def generate_choices(
        self,
        scenario: str,
        num_choices: int = 3,
        context: Optional[GameContext] = None
    ) -> List[Dict[str, Any]]:
        """Generate mock choices."""
        import random
        choices = random.sample(self.CHOICE_TEMPLATES, min(num_choices, len(self.CHOICE_TEMPLATES)))
        return [{"text": c["text"], "effects": c["effects"]} for c in choices]
    
    def generate_event_description(
        self,
        event_type: str,
        context: Optional[GameContext] = None
    ) -> str:
        """Generate a mock event description."""
        import random
        descriptions = self.EVENT_DESCRIPTIONS.get(event_type, ["Something interesting happened..."])
        return random.choice(descriptions)
    
    def generate_research_topic(
        self,
        field: str = "computational biology",
        context: Optional[GameContext] = None
    ) -> Dict[str, str]:
        """Generate a mock research topic."""
        import random
        return random.choice(self.RESEARCH_TOPICS)
    
    def is_available(self) -> bool:
        """Mock LLM is always available."""
        return True


def create_llm(config: Optional[LLMConfig] = None) -> LLMInterface:
    """
    Factory function to create an LLM instance.
    
    Args:
        config: LLM configuration. If None, loads from environment.
        
    Returns:
        LLMInterface implementation
    """
    if config is None:
        config = LLMConfig.from_env()
    
    if config.provider == "mock":
        return MockLLM(config)
    
    # Future: Add other providers
    # elif config.provider == "openai":
    #     return OpenAILLM(config)
    # elif config.provider == "anthropic":
    #     return AnthropicLLM(config)
    
    # Default to mock if provider not recognized
    return MockLLM(config)
