"""
Define some generic exceptions to use throughout the API
"""

__all__ = ["NoteException", "NoteExpired", "NoteNotFound"]


class NoteException(Exception):
    """Base exception for Note framework"""


class NoteExpired(Exception):
    """The Note was found, but its expiration time has passed"""


class NoteNotFound(Exception):
    """The Note was not found in the database"""
