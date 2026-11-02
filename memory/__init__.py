"""
E.D.I.T.H. Memory Module
Local SQLite persistence for chats, logs, and settings.
"""
from .database import DatabaseManager

__all__ = ["DatabaseManager"]
