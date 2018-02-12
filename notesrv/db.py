"""
Defines the database access object for notes.

BaseNoteDOA ca be extended to use the database of your choice.

Postgresql is used by default, but can be extended easily to support other  SQLAlchemy
"""


from abc import ABC, abstractmethod
from datetime import datetime as dt, timedelta
from typing import Union

from .exceptions import NoteExpired, NoteNotFound
from .utils import gen_uid
import asyncpg

__all__ = ["BaseNoteDOA", "PostgresNoteDOA"]


class BaseNoteDOA(ABC):
    """
    Asynchronous Database Object Access base class for Notes.
    Any instance of BaseNoteDOA can be used within the program.
    Child classes can implement other
    """

    @abstractmethod
    async def create(self):
        """
        Should create the database and not raise an exception is the table already exists
        """

    @abstractmethod
    async def prune_expired(self):
        """
        Should prune the database of all notes that are expired.
        Meant to be run periodically
        """

    @abstractmethod
    async def _delete_by_id(self, id: int):
        """
        Deletes a Note by ID. Ignore if the Note does not exist.
        :param id: ID
        :raises None
        """

    @abstractmethod
    async def _get_by_uid(self, uid: str):
        """
        Retrieve a note by UID. This should ONLY retrieve.

        :param uid: unique ID
        :raises None
        """

    @abstractmethod
    async def get_by_uid(self, uid: str):
        """
        Wrapper around _get_by_uid that should handle deleting based on expiration.

        :param: unique ID
        :raises NoteExpored, NoteNotFound
        """

    @abstractmethod
    async def _create_note(self, uid: str, title: str, note: str, created: dt, expires: Union[dt, None]) -> str:
        """
        Creates a note

        :param uid: unique string ID
        :param title: A readable title for the note (stored in plaintext)
        :param note: The contents of the note. If stored encrypted, do not store the key anywhere.
        :param created: Timestamp of when it was created.
        :param expires: Timestamp of note expiration, None if note is single-use
        :return: a string value of the UID created
        """

    @staticmethod
    def expiration_mode_to_time(expiration_mode: int) -> Union[dt, None]:
        """
        Return a timestamp (or None) based on the expiration mode
        :param expiration_mode:
        :return: timestamp or None
        """
        now = dt.utcnow()
        return {
            1: now + timedelta(minutes=5),
            2: now + timedelta(minutes=20),
            3: now + timedelta(hours=1),
            4: now + timedelta(hours=4),
            5: now + timedelta(hours=24),
        }.get(expiration_mode, None)

    async def create_note(self, title: str, note: str, mode: int):
        """
        Should be a wrapper for _create_note that generates missing parameters.

        :param title: A title for the note.
        :param note:
        :param mode: Should be 0-5
        :return:
        """
        return await self._create_note(gen_uid(), title, note, dt.utcnow(), self.expiration_mode_to_time(mode))


class PostgresNoteDOA(BaseNoteDOA):
    """
    Database access object for notes.
    Uses an asyncpg connection pool

    Bit of a DRY violation with spawning transactions,
    """

    def __init__(self, pool: asyncpg.pool.Pool):
        self.__pool = pool

        def transaction_wrapper(func):
            """
            A helper function that creates a transaction and then executes the func provided.
            :param func: A callable member of asyncpg.Connection that returns a coroutine
            :return:
            """
            async def wrapped(*args, **kwargs):
                async with pool.acquire() as conn:
                    async with conn.transaction():
                        return await func(conn, *args, **kwargs)
            return wrapped

        self._execute = transaction_wrapper(asyncpg.Connection.execute)
        self._executemany = transaction_wrapper(asyncpg.Connection.executemany)
        self._fetch = transaction_wrapper(asyncpg.Connection.fetch)
        self._fetchrow = transaction_wrapper(asyncpg.Connection.fetchrow)
        self._fetchval = transaction_wrapper(asyncpg.Connection.fetchval)

    @property
    def pool(self) -> asyncpg.pool.Pool:
        return self.__pool

    async def create(self):
        return await self._execute("""
            CREATE TABLE IF NOT EXISTS notes (
              id SERIAL PRIMARY KEY,
              uid TEXT NOT NULL,
              title TEXT NOT NULL,
              note TEXT NOT NULL,
              created TIMESTAMP NOT NULL,
              expires TIMESTAMP,
              UNIQUE(uid)
            )
        """)

    async def prune_expired(self):
        return await self._execute("""
            DELETE FROM notes WHERE expires < $1
        """, dt.utcnow())

    async def _delete_by_uid(self, uid: str):
        return await self._execute("DELETE FROM notes WHERE uid=$1", uid)

    async def _delete_by_id(self, id: int):
        return await self._execute("DELETE FROM notes WHERE id=$1", id)

    async def _get_by_uid(self, uid: str):
        return await self._fetchrow("SELECT * FROM notes WHERE uid=$1", uid)

    async def _create_note(self, uid: str, title: str, note: str, created: dt, expires: Union[dt, None]) -> str:
        await self._execute("""
            INSERT INTO notes (uid, title, note, created, expires) VALUES ($1, $2, $3, $4, $5)
        """, uid, title, note, created, expires)
        return uid

    async def get_by_uid(self, uid: str) -> asyncpg.Record:
        row = await self._get_by_uid(uid)
        if row is None:
            raise NoteNotFound

        uid = row["uid"]
        now = dt.utcnow()
        expires = row["expires"] is not None and row["expires"] < now
        delete = expires or row["expires"] is None

        if delete:
            await self._delete_by_uid(uid)

        if expires:
            raise NoteExpired

        return row
