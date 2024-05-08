from pathlib import Path
from typing import Any
from typing import cast as type_cast

from podman import PodmanClient
from podman.api.client import APIClient

from .schemes import ContainerizerConfig


class Containerizer:
    def __init__(self, config: ContainerizerConfig):
        self.config = config

    def run(
        self,
        command: list[str],
        image: str | None = None,
        stdin: bytes | None = None,
        mounts: list[Any] | None = None,
        **kwargs,
    ) -> int:
        with PodmanClient(base_url=str(self.config.url)) as client:
            container = client.containers.create(
                image if image is not None else "",
                command,
                **kwargs,
                mounts=mounts,
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

    def translate(self, container_path: Path):
        for path_translation in self.config.path_translations:
            if container_path.absolute().is_relative_to(path_translation.container):
                return (
                    path_translation.containerizer
                    / container_path.absolute().relative_to(
                        path_translation.container.absolute()
                    )
                ).absolute()

        raise ValueError(f"Path {container_path} is not in any of the translations")
