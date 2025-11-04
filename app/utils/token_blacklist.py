from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.token_blacklist import TokenBlacklist
from jose import jwt
from app.logger import get_logger

logger = get_logger(__name__)


class TokenBlacklistService:
    @staticmethod
    def blacklist_token(db: Session, token: str, expires_at: datetime) -> None:
        """Add a token to the blacklist"""
        try:
            # Decode token to get JTI (without verification since we're blacklisting it anyway)
            payload = jwt.get_unverified_claims(token)
            jti = payload.get("jti")

            if not jti:
                logger.warning("Token without JTI cannot be blacklisted")
                return

            # Check if token is already blacklisted
            existing = db.query(TokenBlacklist).filter(TokenBlacklist.jti == jti).first()
            if existing:
                logger.info(f"Token with JTI {jti} already blacklisted")
                return

            # Add to blacklist
            blacklisted_token = TokenBlacklist(
                jti=jti,
                token=token,
                expires_at=expires_at
            )
            db.add(blacklisted_token)
            db.commit()

            logger.info(f"Token with JTI {jti} blacklisted successfully")

        except Exception as e:
            logger.error(f"Error blacklisting token: {str(e)}")
            db.rollback()

    @staticmethod
    def is_token_blacklisted(db: Session, jti: str) -> bool:
        """Check if a token is blacklisted"""
        blacklisted_token = db.query(TokenBlacklist).filter(
            TokenBlacklist.jti == jti,
            TokenBlacklist.expires_at > datetime.now(timezone.utc)  # Only check non-expired tokens
        ).first()

        return blacklisted_token is not None

    @staticmethod
    def cleanup_expired_tokens(db: Session) -> int:
        """Remove expired tokens from blacklist to keep the table clean"""
        try:
            expired_count = db.query(TokenBlacklist).filter(
                TokenBlacklist.expires_at <= datetime.now(timezone.utc)
            ).delete()
            db.commit()

            if expired_count > 0:
                logger.info(f"Cleaned up {expired_count} expired tokens from blacklist")

            return expired_count

        except Exception as e:
            logger.error(f"Error cleaning up expired tokens: {str(e)}")
            db.rollback()
            return 0


token_blacklist_service = TokenBlacklistService()