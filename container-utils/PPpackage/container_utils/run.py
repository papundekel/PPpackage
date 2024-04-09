from typing import IO
from typing import cast as type_cast

from podman import PodmanClient
from podman.api.client import APIClient


def run(url: str, stdin: IO | None = None, *args, **kwargs) -> int:
    with PodmanClient(base_url=url) as client:
        container = client.containers.create(
            *args, **kwargs, stdin_open=stdin is not None
        )

        container.start()

        if stdin is not None:
            api_client = type_cast(APIClient, container.client)

            api_client.post(
                f"/containers/{container.id}/attach",
                params={"stdin": "true", "stdout": "false", "stderr": "false"},
                data=stdin,
                headers={"Content-Length": "0"},
                stream=True,
            )

        return_code = container.wait()

        container.remove()

        return return_code
