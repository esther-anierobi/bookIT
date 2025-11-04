from datetime import timedelta, datetime, timezone
from sqlalchemy.orm import Session
from app.models.user_model import User
from app.schemas.user_schema import (
    UserOut,
    UserLogin,
    LoginResponse,
    LogoutResponse,
    RefreshTokenRequest,
    RefreshTokenResponse,
)
from fastapi import HTTPException, status
from app.security.auth import (
    authenticate_user,
    create_access_token,
    create_refresh_token,
    verify_refresh_token,
)
from app.utils.token_blacklist import token_blacklist_service
from app.logger import get_logger

logger = get_logger(__name__)


class UserService:
    @staticmethod
    def login_user(db: Session, user_login: UserLogin) -> LoginResponse:
        user = authenticate_user(db, user_login.email, user_login.password)
        if not user:
            logger.warning(f"Failed login attempt for email: {user_login.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials (Email or Password)",
            )

        # Reactivate user status on successful login (in case they were logged out)
        if user.status != "active":
            user.status = "active"
            db.commit()
            db.refresh(user)
            logger.info(f"User status reactivated for: {user_login.email}")

        # Create access and refresh tokens
        access_token_expires = timedelta(minutes=30)
        refresh_token_expires = timedelta(days=7)

        access_token, access_expires_at = create_access_token(
            data={"sub": str(user.id)}, expires_delta=access_token_expires
        )
        refresh_token, refresh_expires_at = create_refresh_token(
            data={"sub": str(user.id)}, expires_delta=refresh_token_expires
        )

        logger.info(f"User logged in: {user_login.email}")
        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            user=UserOut.model_validate(user),
        )

    @staticmethod
    def logout_user(
        db: Session,
        user: User,
        access_token: str,
        access_expires_at,
        refresh_token: str = None,
        refresh_expires_at=None,
    ) -> LogoutResponse:
        """
        Logout user by:
        1. Setting user status to 'inactive' (for logout tracking)
        2. Adding both access and refresh tokens to blacklist
        """
        try:
            # Update user status to inactive (for logout state)
            user.status = "inactive"
            db.commit()
            db.refresh(user)

            # Add access token to blacklist
            token_blacklist_service.blacklist_token(db, access_token, access_expires_at)

            # Add refresh token to blacklist if provided
            if refresh_token and refresh_expires_at:
                token_blacklist_service.blacklist_token(
                    db, refresh_token, refresh_expires_at
                )

            logger.info(f"User logged out: {user.email}")
            return LogoutResponse(message="Successfully logged out")

        except Exception as e:
            logger.error(f"Error during logout for user {user.email}: {str(e)}")
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error occurred during logout",
            )

    @staticmethod
    def refresh_access_token(
        db: Session, refresh_request: RefreshTokenRequest
    ) -> RefreshTokenResponse:
        """Generate new access and refresh tokens using valid refresh token"""
        try:
            # Verify refresh token and get user
            user = verify_refresh_token(refresh_request.refresh_token, db)

            # Check if user is still active
            if not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="User account is inactive",
                )

            # Blacklist the old refresh token
            from jose import jwt

            old_payload = jwt.get_unverified_claims(refresh_request.refresh_token)
            old_expires_at = datetime.fromtimestamp(
                old_payload.get("exp"), tz=timezone.utc
            )
            token_blacklist_service.blacklist_token(
                db, refresh_request.refresh_token, old_expires_at
            )

            # Create new access and refresh tokens
            access_token_expires = timedelta(minutes=30)
            refresh_token_expires = timedelta(days=7)

            access_token, _ = create_access_token(
                data={"sub": str(user.id)}, expires_delta=access_token_expires
            )
            refresh_token, _ = create_refresh_token(
                data={"sub": str(user.id)}, expires_delta=refresh_token_expires
            )

            logger.info(f"Tokens refreshed for user: {user.email}")
            return RefreshTokenResponse(
                access_token=access_token,
                refresh_token=refresh_token,
                token_type="bearer",
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error refreshing token: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error occurred while refreshing token",
            )


user_app_service = UserService()
