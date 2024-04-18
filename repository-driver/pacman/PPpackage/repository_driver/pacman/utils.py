def strip_version(name: str) -> str:
    return name.rsplit("<", 1)[0].rsplit(">", 1)[0].rsplit("=", 1)[0]
