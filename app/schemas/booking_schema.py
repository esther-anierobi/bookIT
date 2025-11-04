from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional
from uuid import UUID
from datetime import datetime, timezone
from enum import Enum


class BookingStatus(str, Enum):
    pending = "pending"
    confirmed = "confirmed"
    cancelled = "cancelled"
    completed = "completed"


class BookingBase(BaseModel):
    service_id: UUID = Field(..., description="ID of the service being booked")
    start_time: datetime = Field(..., description="Booking start time")
    end_time: datetime = Field(..., description="Booking end time")

    @field_validator('start_time')
    @classmethod
    def start_time_must_be_in_future(cls, v):
        # Make both datetimes timezone-aware for comparison
        now = datetime.now(timezone.utc)
        # If v is timezone-naive, assume it's UTC
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        if v <= now:
            raise ValueError('start_time must be in the future')
        return v

    @model_validator(mode='after')  # Use model_validator instead of field_validator for cross-field validation
    def end_time_must_be_after_start_time(self):
        if self.end_time <= self.start_time:
            raise ValueError('end_time must be after start_time')
        return self


class BookingCreate(BookingBase):
    pass


class BookingUpdate(BaseModel):
    start_time: Optional[datetime] = Field(None, description="New booking start time")
    end_time: Optional[datetime] = Field(None, description="New booking end time")
    status: Optional[BookingStatus] = Field(None, description="Booking status")

    @model_validator(mode='after')
    def end_time_must_be_after_start_time(self):
        if self.end_time and self.start_time and self.end_time <= self.start_time:
            raise ValueError('end_time must be after start_time')
        return self


class BookingResponse(BaseModel):
    id: UUID
    user_id: UUID
    service_id: UUID
    start_time: datetime
    end_time: datetime
    status: BookingStatus = BookingStatus.pending
    created_at: datetime

    class Config:
        from_attributes = True


class BookingWithDetails(BookingResponse):
    service: Optional[dict] = None
    user: Optional[dict] = None

    class Config:
        from_attributes = True
