from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List, Optional
from app.services.review_crud import review_crud
from app.schemas.review_schema import ReviewCreate, ReviewUpdate, ReviewResponse
from app.database import get_db
from app.security.auth import get_current_active_user, get_current_admin_user
from app.models.user_model import User
from app.logger import get_logger

review_router = APIRouter()
logger = get_logger(__name__)

# USER ENDPOINTS - Users can manage their own reviews


@review_router.post(
    "/reviews", response_model=ReviewResponse, status_code=status.HTTP_201_CREATED
)
def create_review(
    review: ReviewCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Create a new review (must be for a completed booking by the same user)"""
    try:
        logger.info(
            f"User {current_user.email} creating review for booking {review.booking_id}"
        )
        db_review = review.create_review(db, review, current_user.id)
        logger.info(f"Review created: {db_review.id}")
        return ReviewResponse.model_validate(db_review)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating review: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error occurred while creating review",
        )


@review_router.get(
    "/reviews/{review_id}",
    response_model=ReviewResponse,
    status_code=status.HTTP_200_OK,
)
def get_review(
    review_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get review by ID"""
    try:
        logger.info(f"Fetching review: {review_id}")
        review = review_crud.get_review_by_id(db, review_id)
        if not review:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Review not found"
            )

        return ReviewResponse.model_validate(review)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching review {review_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error occurred while fetching review",
        )


@review_router.patch(
    "/reviews/{review_id}",
    response_model=ReviewResponse,
    status_code=status.HTTP_200_OK,
)
def update_review(
    review_id: UUID,
    review_update: ReviewUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Update review (owner only)"""
    try:
        logger.info(f"User {current_user.email} updating review: {review_id}")
        is_admin = current_user.role == "admin"
        user_id = None if is_admin else current_user.id

        updated_review = review_crud.update_review(
            db, review_id, review_update, user_id, is_admin
        )
        logger.info(f"Review updated: {review_id}")
        return ReviewResponse.model_validate(updated_review)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating review {review_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error occurred while updating review",
        )


@review_router.delete(
    "/reviews/{review_id}",
    response_model=ReviewResponse,
    status_code=status.HTTP_200_OK,
)
def delete_review(
    review_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Delete review (owner or admin)"""
    try:
        logger.info(f"User {current_user.email} deleting review: {review_id}")
        is_admin = current_user.role == "admin"
        user_id = None if is_admin else current_user.id

        deleted_review = review_crud.delete_review(db, review_id, user_id, is_admin)
        logger.info(f"Review deleted: {review_id}")
        return ReviewResponse.model_validate(deleted_review)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting review {review_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error occurred while deleting review",
        )


# PUBLIC ENDPOINTS - Anyone can view service reviews


@review_router.get(
    "/services/{service_id}/reviews",
    response_model=List[ReviewResponse],
    status_code=status.HTTP_200_OK,
)
def get_service_reviews(
    service_id: UUID,
    skip: int = Query(0, ge=0, description="Number of reviews to skip"),
    limit: int = Query(100, ge=1, le=100, description="Number of reviews to retrieve"),
    min_rating: Optional[int] = Query(
        None, ge=1, le=5, description="Minimum rating filter"
    ),
    max_rating: Optional[int] = Query(
        None, ge=1, le=5, description="Maximum rating filter"
    ),
    db: Session = Depends(get_db),
):
    """Get all reviews for a specific service (public endpoint)"""
    try:
        logger.info(f"Fetching reviews for service: {service_id}")
        reviews = review_crud.get_service_reviews(
            db, service_id, skip=skip, limit=limit
        )

        # Apply rating filters if provided
        if min_rating is not None:
            reviews = [review for review in reviews if review.rating >= min_rating]
        if max_rating is not None:
            reviews = [review for review in reviews if review.rating <= max_rating]

        return [ReviewResponse.model_validate(review) for review in reviews]

    except Exception as e:
        logger.error(f"Error fetching service reviews: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error occurred while fetching service reviews",
        )


@review_router.get(
    "/services/{service_id}/reviews/stats", status_code=status.HTTP_200_OK
)
def get_service_review_stats(service_id: UUID, db: Session = Depends(get_db)):
    """Get review statistics for a service (public endpoint)"""
    try:
        logger.info(f"Fetching review stats for service: {service_id}")
        stats = review_crud.get_service_review_stats(db, service_id)
        return stats

    except Exception as e:
        logger.error(f"Error fetching service review stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error occurred while fetching review statistics",
        )


# USER REVIEW MANAGEMENT


@review_router.get(
    "/users/me/reviews",
    response_model=List[ReviewResponse],
    status_code=status.HTTP_200_OK,
)
def get_user_reviews(
    skip: int = Query(0, ge=0, description="Number of reviews to skip"),
    limit: int = Query(100, ge=1, le=100, description="Number of reviews to retrieve"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get current user's reviews"""
    try:
        logger.info(f"User {current_user.email} fetching their reviews")
        reviews = review_crud.get_user_reviews(
            db, current_user.id, skip=skip, limit=limit
        )
        return [ReviewResponse.model_validate(review) for review in reviews]

    except Exception as e:
        logger.error(f"Error fetching user reviews: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error occurred while fetching user reviews",
        )


# ADMIN ENDPOINTS


@review_router.get(
    "/admin/reviews",
    response_model=List[ReviewResponse],
    status_code=status.HTTP_200_OK,
)
def get_all_reviews(
    skip: int = Query(0, ge=0, description="Number of reviews to skip"),
    limit: int = Query(100, ge=1, le=100, description="Number of reviews to retrieve"),
    user_id: Optional[UUID] = Query(None, description="Filter by user ID"),
    service_id: Optional[UUID] = Query(None, description="Filter by service ID"),
    min_rating: Optional[int] = Query(
        None, ge=1, le=5, description="Minimum rating filter"
    ),
    max_rating: Optional[int] = Query(
        None, ge=1, le=5, description="Maximum rating filter"
    ),
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """Get all reviews with filtering (admin only)"""
    try:
        logger.info(f"Admin {current_user.email} fetching all reviews")
        reviews = review_crud.get_reviews(
            db=db,
            skip=skip,
            limit=limit,
            user_id=user_id,
            service_id=service_id,
            min_rating=min_rating,
            max_rating=max_rating,
        )
        return [ReviewResponse.model_validate(review) for review in reviews]

    except Exception as e:
        logger.error(f"Error fetching all reviews: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error occurred while fetching reviews",
        )


@review_router.get(
    "/admin/users/{user_id}/reviews",
    response_model=List[ReviewResponse],
    status_code=status.HTTP_200_OK,
)
def get_user_reviews_admin(
    user_id: UUID,
    skip: int = Query(0, ge=0, description="Number of reviews to skip"),
    limit: int = Query(100, ge=1, le=100, description="Number of reviews to retrieve"),
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """Get reviews by specific user (admin only)"""
    try:
        logger.info(f"Admin {current_user.email} fetching reviews for user {user_id}")
        reviews = review_crud.get_user_reviews(db, user_id, skip=skip, limit=limit)
        return [ReviewResponse.model_validate(review) for review in reviews]

    except Exception as e:
        logger.error(f"Error fetching user reviews for admin: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error occurred while fetching user reviews",
        )


# BOOKING-RELATED ENDPOINTS


@review_router.get(
    "/bookings/{booking_id}/review",
    response_model=ReviewResponse,
    status_code=status.HTTP_200_OK,
)
def get_booking_review(
    booking_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get review for a specific booking"""
    try:
        logger.info(f"Fetching review for booking: {booking_id}")
        review = review_crud.get_review_by_booking(db, booking_id)
        if not review:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Review not found for this booking",
            )

        return ReviewResponse.model_validate(review)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching booking review: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error occurred while fetching booking review",
        )
