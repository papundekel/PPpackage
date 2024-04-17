from typing import IO
from typing import cast as type_cast

from podman import PodmanClient
from podman.api.client import APIClient
from pydantic import AnyUrl


def run(
    url: AnyUrl,
    command: list[str],
    image: str | None = None,
    stdin: IO | bytes | None = None,
    **kwargs,
) -> int:
    with PodmanClient(base_url=str(url)) as client:
        container = client.containers.create(
            image if image is not None else "",
            command,
            **kwargs,
            stdin_open=stdin is not None,
        )

        container.start()

        if stdin is not None:
            type_cast(APIClient, container.client).post(
                f"/containers/{container.id}/attach",
                params={"stdin": "true", "stdout": "false", "stderr": "false"},
                data=stdin,
                headers={"Content-Length": "0"},
                stream=True,
            )

        return_code = container.wait()

        container.remove()

        return return_code
