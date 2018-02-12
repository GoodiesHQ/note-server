#!/usr/bin/env python3
"""
Main module for the Note server.

Main modules handles initial connection to database connection and creation of the Sanic application.

Web API is mounted onto /api and expects the Sanic app to contain `app.config.doa` where:
    - `app` is a Sanic applicaiton
    - `app.config.doa` is an instance of notesrv.db.BaseNoteDOA

BaseNoteDOA can easily be extended to support other database types. This is a single-table
database and has very simple interactions.
"""

from configparser import ConfigParser
from datetime import timedelta
import asyncio
import os
import sys

from sanic import Sanic
from sanic.exceptions import NotFound
from sanic.request import Request
from sanic.response import html as response_html, redirect
import asyncpg

from notesrv.api import bp
from notesrv.db import PostgresNoteDOA, BaseNoteDOA

UID_LENGTH = 21

app = Sanic("note")
app.static("/", "./dist")
app.blueprint(bp)


async def create_asyncpg_doa(database, username, password, host: str="127.0.0.1", port: int=5432):
    """
    Simple wrapper to create an asyncpg connection pool.
    """
    pool = await asyncpg.create_pool(
        ''.join(
            ("postgres://",
             username,
             (":" + password) if password else "",
             "@",
             host,
             ":{}".format(port),
             "/{}".format(database),
             )
        )
    )

    return PostgresNoteDOA(pool)


@app.listener("before_server_start")
async def init(app, loop):
    cfg = app.config.config["database"]

    if cfg["mode"] == "postgresql":
        app.config.doa = await create_asyncpg_doa(
            cfg["database"],
            cfg["username"],
            cfg["password"],
            cfg["host"],
            int(cfg["port"]),
        )

    # Insert other database connection types here and follow the amove template for creating app.config.doa

    if not hasattr(app.config, "doa"):
        print("'{}' is an invalid database mode.", cfg["mode"])
        sys.exit(1)

    async def prune_every(seconds: int, doa: BaseNoteDOA):
        await doa.prune_expired()
        await asyncio.sleep(seconds)
        asyncio.ensure_future(prune_every(seconds, doa), loop=loop)

    asyncio.ensure_future(prune_every(timedelta(minutes=6).total_seconds(), app.config.doa), loop=loop)
    await app.config.doa.create()


@app.exception(NotFound)
async def handle_NotFound(request: Request, exception: Exception):
    return redirect("/")


@app.route("/")
async def index(request: Request):
    return response_html(open("./dist/index.html", "r").read())


def main():
    if not os.path.isfile("config.ini"):
        config = ConfigParser()
        config["database"] = dict(
            mode="postgresql",
            database="",
            username="",
            password="",
            host="localhost",
            port=5432,
        )
        with open("config.ini", "w+") as fout:
            config.write(fout)

        print("Please edit your config.ini")
        sys.exit(0)

    config = ConfigParser()
    config.read("config.ini")
    app.config.config = config


if __name__ == "__main__":
    main()
    app.run(host="0.0.0.0", port=8000)
