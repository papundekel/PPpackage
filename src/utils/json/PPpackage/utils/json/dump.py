from json import dumps as json_dumps
from typing import Any

from .utils import wrap_instance


def dump_python(output: Any) -> Any:
    output_wrapped = wrap_instance(output)

    output_python = output_wrapped.model_dump()

    return output_python


def dump_json(output: Any) -> str:
    output_python = dump_python(output)

    output_json = json_dumps(output_python, sort_keys=True, separators=(",", ":"))

    return output_json
