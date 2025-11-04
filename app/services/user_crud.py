from datetime import datetime, timezone
from fastapi import HTTPException, status
from typing import List
from uuid import UUID
from app.schemas.user_schema import UserCreate, UserUpdate
from app.models.user_model import User
from sqlalchemy.orm import Session
from app.security.auth import get_password_hash
from app.logger import get_logger

logger = get_logger(__name__)


class UserCRUD:
    @staticmethod
    def get_user_id(db: Session, user_id: UUID):
        return db.query(User).filter(User.id == str(user_id)).first()

    @staticmethod
    def get_user_by_email(db: Session, email: str):
        return db.query(User).filter(User.email == email).first()

    @staticmethod
    def get_users(db: Session, skip: int = 0, limit: int = 100) -> List[User]:
        return db.query(User).offset(skip).limit(limit).all()

    @staticmethod
    def create_user(db: Session, user: UserCreate) -> User:
        # Check if user with email exists
        existing_user = db.query(User).filter(User.email == user.email).first()
        if existing_user:
            if existing_user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User with the email already exist"
                )
            else:
                # Reactivate the existing inactive user instead of creating new one
                existing_user.name = user.name
                existing_user.password_hash = get_password_hash(user.password)
                existing_user.role = user.role.value
                existing_user.status = "active"
                existing_user.is_active = True
                existing_user.created_at = datetime.now(timezone.utc)  # Update timestamp
                db.commit()
                db.refresh(existing_user)
                return existing_user
        # Create new user if existing user found
        db_user = User(
            name=user.name,
            email=user.email,
            password_hash=get_password_hash(user.password),
            role=user.role.value,
            status="active",
            is_active=True
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user

    @staticmethod
    def update_user(db: Session, user_id: UUID, user_update: UserUpdate) -> User:
        db_user = db.query(User).filter(User.id == str(user_id)).first()
        if not db_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found: This user does not exist in the database"
                                )

        for key, value in user_update.model_dump(exclude_unset=True).items():
            if value is not None:
                if key == "password":
                    setattr(db_user, "password_hash", get_password_hash(value))
                else:
                    setattr(db_user, key, value)

        db.commit()
        db.refresh(db_user)
        return db_user

    @staticmethod
    def delete_user(db: Session, user_id: UUID) -> User:
        db_user = db.query(User).filter(User.id == str(user_id)).first()
        if not db_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found:This user does not exist in the database"
                                )
        # Soft delete by setting is_active to False
        db_user.is_active = False
        db.commit()
        db.refresh(db_user)
        return db_user


user_crud = UserCRUD()