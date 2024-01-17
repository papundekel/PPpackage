from collections.abc import Mapping

from pydantic_settings import BaseSettings, SettingsConfigDict

from .schemes import LocalSubmanagerConfig, RemoteSubmanagerConfig


class Settings(BaseSettings):
    submanagers: Mapping[str, RemoteSubmanagerConfig | LocalSubmanagerConfig]

    model_config = SettingsConfigDict(env_nested_delimiter="__", case_sensitive=True)
