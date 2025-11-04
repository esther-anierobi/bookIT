from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime,Boolean
from sqlalchemy.dialects.postgresql import UUID
import uuid
from app.database import Base
from sqlalchemy.orm import relationship


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    name = Column(String, nullable=False, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    status = Column(String, default="active")
    role = Column(String, default="user")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))

    # Relationships
    services = relationship("Service", back_populates="owner")
    bookings = relationship("Booking", back_populates="user")
