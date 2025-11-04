from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime
from sqlalchemy.dialects.postgresql import UUID
import uuid
from app.database import Base


class TokenBlacklist(Base):
    __tablename__ = "token_blacklist"

    id = Column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    jti = Column(String, unique=True, nullable=False, index=True)  # JWT ID
    token = Column(String, nullable=False)  # Full token for additional verification
    expires_at = Column(DateTime, nullable=False)  # Token expiration time
    blacklisted_at = Column(DateTime, default=datetime.now(timezone.utc))  # When token was blacklisted