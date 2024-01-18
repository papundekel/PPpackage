#!/usr/bin/env python

from asyncio import run
from sys import argv

import PPpackage_submanager.database
from PPpackage_submanager.database import create_admin_token
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel


async def main():
    url = argv[1]

    engine = create_async_engine(str(url), connect_args={"check_same_thread": False})

    async with engine.begin() as connection:
        await connection.run_sync(SQLModel.metadata.create_all)

    token = await create_admin_token(engine)

    await engine.dispose()

    print(token)


run(main())
