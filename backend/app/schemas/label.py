from uuid import UUID

from pydantic import BaseModel, Field


class LabelItemIn(BaseModel):
    variant_id: UUID
    copies: int = Field(default=1, ge=1, le=1000)


class LabelPreviewRequest(BaseModel):
    items: list[LabelItemIn] = Field(default_factory=list)
    template: str = "default-40x30"
