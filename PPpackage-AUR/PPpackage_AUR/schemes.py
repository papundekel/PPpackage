from pydantic.dataclasses import dataclass


@dataclass(frozen=True)
class ProductInfo:
    version: str
    product_id: str
