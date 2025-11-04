from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from datetime import datetime, timezone


class ServiceBase(BaseModel):
    title: str = Field(..., example="House Cleaning")
    description: Optional[str] = Field(None, example="Comprehensive house cleaning service")
    price: float = Field(..., example=99.99)
    duration_minutes: int = Field(..., example=120)


class ServiceCreate(ServiceBase):
    pass


class ServiceUpdate(BaseModel):
    title: Optional[str] = Field(None, example="House Cleaning")
    description: Optional[str] = Field(None, example="Comprehensive house cleaning service")
    price: Optional[float] = Field(None, example=99.99)


class ServiceResponse(ServiceBase):
    id: UUID
    is_active: bool
    created_at: datetime
    owner_id: UUID

    class Config:
        from_attributes = True
