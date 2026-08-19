from pydantic import BaseModel


class ErrorResponse(BaseModel):
    """Every failing endpoint answers with this shape."""

    detail: str


class HealthResponse(BaseModel):
    status: str
    database: str
    domain: str
