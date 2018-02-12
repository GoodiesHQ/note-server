"""
Various utility functions used throughout the note server
"""

from random import SystemRandom
from string import ascii_letters, digits
random = SystemRandom()

__all__ = ["UID_LENGTH", "UID_CHARSET", "gen_uid"]

UID_LENGTH = 21
UID_CHARSET = ascii_letters + digits


def gen_uid() -> str:
    """
    Generate a random unique ID
    :return: str (UID)
    """
    return ''.join(random.choice(UID_CHARSET) for _ in range(UID_LENGTH))