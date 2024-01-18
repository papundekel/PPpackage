#!/usr/bin/env python

from asyncio import run
from pathlib import Path
from sys import argv

from httpx import AsyncClient as HTTPClient
from PPpackage_submanager.schemes import UserCreated


async def main():
    url = argv[1]
    admin_token_path = Path(argv[2])

    with admin_token_path.open("r") as admin_token_file:
        admin_token = admin_token_file.read().strip()

    async with HTTPClient() as client:
        response = await client.post(
            f"{url}/user",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        response.raise_for_status()

        user_created = UserCreated.model_validate(response.json())

        print(user_created.token)


run(main())
