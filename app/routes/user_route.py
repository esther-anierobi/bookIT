from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from jose import jwt
from sqlalchemy.orm import Session
from uuid import UUID
from typing import Annotated, List
from datetime import datetime, timezone
from app.services.user_crud import user_crud
from app.schemas.user_schema import UserCreate, UserOut, UserUpdate, UserLogin, LoginResponse, \
    LogoutResponse, RefreshTokenRequest, RefreshTokenResponse
from app.database import get_db
from app.security.auth import oauth2_scheme, get_current_user, get_current_active_user, get_current_admin_user
from app.utils.user_app_service import user_app_service
from app.models.user_model import User
from app.logger import get_logger


user_router = APIRouter()
logger = get_logger(__name__)


# AUTH ENDPOINTS

@user_router.post("/auth/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    """Register a new user"""
    try:
        logger.info(f"Registering user: {user.email}")
        db_user = user_crud.create_user(db, user)
        logger.info(f"User registered successfully: {user.email}")
        return UserOut.model_validate(db_user)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error registering user {user.email}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error occurred while registering user"
        )


@user_router.post("/token", response_model=LoginResponse)
async def user_token(
        form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
        db: Session = Depends(get_db),
):
    logger.info(f"Token request for user: {form_data.username}")
    user_login = UserLogin(email=form_data.username, password=form_data.password)

    try:
        return user_app_service.login_user(db, user_login)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"fatal: Please provide your registered email {form_data.username}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error occurred during token generation"
        )


@user_router.post("/auth/login", response_model=LoginResponse, status_code=status.HTTP_200_OK)
def login_user(user_login: UserLogin, db: Session = Depends(get_db)):
    """Login user and return access and refresh tokens"""
    try:
        logger.info(f"Login attempt for user: {user_login.email}")
        return user_app_service.login_user(db, user_login)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during login for {user_login.email}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error occurred during login"
        )


@user_router.post("/auth/logout", response_model=LogoutResponse, status_code=status.HTTP_200_OK)
def logout_user(
        refresh_request: RefreshTokenRequest,
        current_user: User = Depends(get_current_user),
        token: str = Depends(oauth2_scheme),
        db: Session = Depends(get_db)
):
    """Logout user by blacklisting both access and refresh tokens"""
    try:

        # Use unverified claims for both tokens (since we just need expiration times)
        access_payload = jwt.get_unverified_claims(token)
        access_expires_at = datetime.fromtimestamp(access_payload.get("exp"), tz=timezone.utc)

        # Get refresh token expiration
        refresh_payload = jwt.get_unverified_claims(refresh_request.refresh_token)
        refresh_expires_at = datetime.fromtimestamp(refresh_payload.get("exp"), tz=timezone.utc)

        return user_app_service.logout_user(
            db, current_user, token, access_expires_at,
            refresh_request.refresh_token, refresh_expires_at
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during logout for user {current_user.email}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error occurred during logout"
        )


@user_router.post("/auth/refresh", response_model=RefreshTokenResponse, status_code=status.HTTP_200_OK)
def refresh_access_token(refresh_request: RefreshTokenRequest, db: Session = Depends(get_db)):
    """Refresh access token using valid refresh token"""
    try:
        logger.info("Refreshing access token")
        return user_app_service.refresh_access_token(db, refresh_request)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error refreshing token: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error occurred while refreshing token"
        )


# USER MANAGEMENT ENDPOINTS

@user_router.get("/me", response_model=UserOut, status_code=status.HTTP_200_OK)
def get_current_user_profile(current_user: User = Depends(get_current_active_user)):
    """Get current user profile"""
    return UserOut.model_validate(current_user)


@user_router.patch("/me", response_model=UserOut, status_code=status.HTTP_200_OK)
def update_current_user_profile(
        user_update: UserUpdate,
        current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_db)
):
    """Update current user profile"""
    try:
        logger.info(f"User updating profile: {current_user.email}")
        updated_user = user_crud.update_user(db, current_user.id, user_update)
        logger.info(f"User profile updated: {current_user.email}")
        return UserOut.model_validate(updated_user)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating profile for {current_user.email}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error occurred while updating profile"
        )


# ADMIN ENDPOINTS

@user_router.get("/users", response_model=List[UserOut], status_code=status.HTTP_200_OK)
def get_all_users(
        skip: int = 0,
        limit: int = 100,
        current_user: User = Depends(get_current_admin_user),
        db: Session = Depends(get_db)
):
    """Get all users (admin only)"""
    try:
        logger.info(f"Admin {current_user.email} fetching users list")
        users = user_crud.get_users(db, skip=skip, limit=limit)
        return [UserOut.model_validate(user) for user in users]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching users: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error occurred while fetching users"
        )


@user_router.get("/users/{user_id}", response_model=UserOut, status_code=status.HTTP_200_OK)
def get_user_by_id(
        user_id: UUID,
        current_user: User = Depends(get_current_admin_user),
        db: Session = Depends(get_db)
):
    """Get user by ID (admin only)"""
    try:
        logger.info(f"Admin {current_user.email} fetching user {user_id}")
        user = user_crud.get_user_id(db, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        return UserOut.model_validate(user)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching user {user_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error occurred while fetching user"
        )


@user_router.patch("/users/{user_id}", response_model=UserOut, status_code=status.HTTP_200_OK)
def update_user_by_id(
        user_id: UUID,
        user_update: UserUpdate,
        current_user: User = Depends(get_current_admin_user),
        db: Session = Depends(get_db)
):
    """Update user by ID (admin only)"""
    try:
        logger.info(f"Admin {current_user.email} updating user {user_id}")
        updated_user = user_crud.update_user(db, user_id, user_update)
        logger.info(f"User {user_id} updated by admin {current_user.email}")
        return UserOut.model_validate(updated_user)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user {user_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error occurred while updating user"
        )


@user_router.delete("/users/{user_id}", response_model=UserOut, status_code=status.HTTP_200_OK)
def delete_user_by_id(
        user_id: UUID,
        current_user: User = Depends(get_current_admin_user),
        db: Session = Depends(get_db)
):
    """Soft delete user by ID (admin only)"""
    try:
        logger.info(f"Admin {current_user.email} deleting user {user_id}")
        deleted_user = user_crud.delete_user(db, user_id)
        logger.info(f"User {user_id} deleted by admin {current_user.email}")
        return UserOut.model_validate(deleted_user)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting user {user_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error occurred while deleting user"
        )
