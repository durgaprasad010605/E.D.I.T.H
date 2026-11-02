"""
Abstract Base Class for E.D.I.T.H. Brain Modules
Enables seamless upgrading from MockBrain -> Ollama -> Cloud or Hybrid.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class BaseBrain(ABC):
    """Abstract interface that all reasoning engines must implement."""

    @abstractmethod
    def get_name(self) -> str:
        """Return the display name of this brain provider."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the backend model/service is ready and loaded."""
        pass

    @abstractmethod
    def generate_response(self, user_input: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Process the user's input and generate an in-character response.
        :param user_input: Raw text string from user (typed or STT transcribed).
        :param context: Optional dictionary containing system telemetry, user history, or active tasks.
        :return: Generated response string.
        """
        pass
