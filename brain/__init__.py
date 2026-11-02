"""
E.D.I.T.H. Brain Module
Modular interface for AI reasoning engines (Mock, Ollama, GGUF, APIs)
"""
from .base import BaseBrain
from .mock_brain import MockBrain

__all__ = ["BaseBrain", "MockBrain"]
