from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from uuid import UUID
from app.models.review_model import Review
from app.models.booking_model import Booking
from app.schemas.review_schema import ReviewCreate, ReviewUpdate
from app.logger import get_logger

logger = get_logger(__name__)


class ReviewCRUD:
    @staticmethod
    def create_review(db: Session, review: ReviewCreate, user_id: UUID) -> Review:
        """Create a new review with validation"""
        # Convert UUIDs to strings if needed
        booking_id_str = str(review.booking_id)
        user_id_str = str(user_id)

        # Verify booking exists and belongs to the user
        booking = db.query(Booking).filter(
            Booking.id == booking_id_str,
            Booking.user_id == user_id_str
        ).first()

        if not booking:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Booking not found or does not belong to you"
            )

        # Verify booking is completed
        if booking.status != "completed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Can only review completed bookings"
            )

        # Check if review already exists for this booking
        existing_review = db.query(Review).filter(Review.booking_id == booking_id_str).first()
        if existing_review:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A review already exists for this booking"
            )

        try:
            db_review = Review(
                booking_id=booking_id_str,
                rating=review.rating,
                comment=review.comment
            )
            db.add(db_review)
            db.commit()
            db.refresh(db_review)
            logger.info(f"Review created: {db_review.id} for booking {booking_id_str}")
            return db_review

        except Exception as e:
            db.rollback()
            logger.error(f"Error creating review: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error occurred while creating review"
            )

    @staticmethod
    def get_review_by_id(db: Session, review_id: UUID) -> Optional[Review]:
        """Get review by ID"""
        review_id_str = str(review_id)
        return db.query(Review).filter(Review.id == review_id_str).first()

    @staticmethod
    def get_reviews(
            db: Session,
            skip: int = 0,
            limit: int = 100,
            user_id: Optional[UUID] = None,
            service_id: Optional[UUID] = None,
            booking_id: Optional[UUID] = None,
            min_rating: Optional[int] = None,
            max_rating: Optional[int] = None
    ) -> List[Review]:
        """Get reviews with optional filtering"""
        query = db.query(Review)

        # Only join bookings table if we need to filter by user_id or service_id
        needs_booking_join = user_id is not None or service_id is not None
        if needs_booking_join:
            query = query.join(Booking, Review.booking_id == Booking.id)

        # Filter by booking
        if booking_id is not None:
            booking_id_str = str(booking_id)
            query = query.filter(Review.booking_id == booking_id_str)

        # Filter by user (through booking relationship)
        if user_id is not None:
            user_id_str = str(user_id)
            query = query.filter(Booking.user_id == user_id_str)

        # Filter by service (through booking relationship)
        if service_id is not None:
            service_id_str = str(service_id)
            query = query.filter(Booking.service_id == service_id_str)

        # Filter by rating range
        if min_rating is not None:
            query = query.filter(Review.rating >= min_rating)
        if max_rating is not None:
            query = query.filter(Review.rating <= max_rating)

        return query.order_by(Review.created_at.desc()).offset(skip).limit(limit).all()

    @staticmethod
    def get_service_reviews(db: Session, service_id: UUID, skip: int = 0, limit: int = 100) -> List[Review]:
        """Get all reviews for a specific service"""
        return ReviewCRUD.get_reviews(db=db, service_id=service_id, skip=skip, limit=limit)

    @staticmethod
    def get_user_reviews(db: Session, user_id: UUID, skip: int = 0, limit: int = 100) -> List[Review]:
        """Get all reviews by a specific user"""
        return ReviewCRUD.get_reviews(db=db, user_id=user_id, skip=skip, limit=limit)

    @staticmethod
    def update_review(db: Session, review_id: UUID, review_update: ReviewUpdate, user_id: Optional[UUID] = None,
                      is_admin: bool = False) -> Review:
        """Update review with proper authorization"""
        review_id_str = str(review_id)

        db_review = db.query(Review).filter(Review.id == review_id_str).first()
        if not db_review:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Review not found"
            )

        # Authorization check: only the review author or admin can update
        if not is_admin and user_id is not None:
            user_id_str = str(user_id)
            booking = db.query(Booking).filter(Booking.id == db_review.booking_id).first()
            if not booking or booking.user_id != user_id_str:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not authorized to update this review"
                )

        try:
            # Update only provided fields
            for key, value in review_update.model_dump(exclude_unset=True).items():
                if value is not None:
                    setattr(db_review, key, value)

            db.commit()
            db.refresh(db_review)
            logger.info(f"Review updated: {review_id_str}")
            return db_review

        except Exception as e:
            db.rollback()
            logger.error(f"Error updating review {review_id_str}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error occurred while updating review"
            )

    @staticmethod
    def delete_review(db: Session, review_id: UUID, user_id: Optional[UUID] = None, is_admin: bool = False) -> Review:
        """Delete review with proper authorization"""
        review_id_str = str(review_id)

        db_review = db.query(Review).filter(Review.id == review_id_str).first()
        if not db_review:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Review not found"
            )

        # Authorization check: only the review author or admin can delete
        if not is_admin and user_id is not None:
            user_id_str = str(user_id)
            booking = db.query(Booking).filter(Booking.id == db_review.booking_id).first()
            if not booking or booking.user_id != user_id_str:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not authorized to delete this review"
                )

        try:
            db.delete(db_review)
            db.commit()
            logger.info(f"Review deleted: {review_id_str}")
            return db_review

        except Exception as e:
            db.rollback()
            logger.error(f"Error deleting review {review_id_str}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error occurred while deleting review"
            )

    @staticmethod
    def get_review_by_booking(db: Session, booking_id: UUID) -> Optional[Review]:
        """Get review for a specific booking"""
        booking_id_str = str(booking_id)
        return db.query(Review).filter(Review.booking_id == booking_id_str).first()

    @staticmethod
    def get_service_review_stats(db: Session, service_id: UUID) -> dict:
        """Get review statistics for a service"""
        service_id_str = str(service_id)

        stats = db.query(
            func.count(Review.id).label('total_reviews'),
            func.avg(Review.rating).label('average_rating'),
            func.min(Review.rating).label('min_rating'),
            func.max(Review.rating).label('max_rating')
        ).join(Booking, Review.booking_id == Booking.id).filter(Booking.service_id == service_id_str).first()

        return {
            'total_reviews': stats.total_reviews or 0,
            'average_rating': float(stats.average_rating) if stats.average_rating else 0.0,
            'min_rating': stats.min_rating or 0,
            'max_rating': stats.max_rating or 0
        }


review_crud = ReviewCRUD()
