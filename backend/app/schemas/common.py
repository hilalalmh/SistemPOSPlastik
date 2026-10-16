from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, PlainSerializer

MoneyStr = Annotated[
    Decimal,
    PlainSerializer(lambda v: f"{Decimal(v):f}", return_type=str, when_used="json"),
]
QtyStr = Annotated[
    Decimal,
    PlainSerializer(lambda v: f"{Decimal(v):f}", return_type=str, when_used="json"),
]


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Page[T](BaseModel):
    data: list[T]
    page: int
    page_size: int
    total: int
