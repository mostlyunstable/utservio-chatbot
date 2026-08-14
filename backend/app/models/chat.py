from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=100)
    message: str = Field(..., min_length=1, max_length=1000)


class ChatResponse(BaseModel):
    message: str
    session_id: str
    type: str = "text"
    options: list[str] | None = None
    data: dict | None = None
    metadata: dict


class MessageModel(BaseModel):
    role: str
    content: str


class HistoryResponse(BaseModel):
    session_id: str
    messages: list[MessageModel]


class ServiceModel(BaseModel):
    id: int
    name: str
    category: str | None = None
    description: str | None = None
    price_amount: str | None = None
    price_currency: str | None = None
    pricing_type: str | None = None
    price_unit: str | None = None
    source_url: str | None = None
    source_domain: str | None = None
    extraction_method: str | None = None

    class Config:
        from_attributes = True
