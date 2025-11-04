from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List, Optional
from datetime import datetime
from app.services.booking_crud import booking_crud
from app.schemas.booking_schema import BookingCreate, BookingUpdate, BookingResponse, BookingStatus
from app.database import get_db
from app.security.auth import get_current_active_user, get_current_admin_user
from app.models.user_model import User
from app.logger import get_logger

booking_router = APIRouter()
logger = get_logger(__name__)

# USER ENDPOINTS - Users can manage their own bookings


@booking_router.post(
    "/bookings", response_model=BookingResponse, status_code=status.HTTP_201_CREATED
)
def create_booking(
    booking: BookingCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Create a new booking (user creates)"""
    try:
        logger.info(
            f"User {current_user.email} creating booking for service {booking.service_id}"
        )
        db_booking = booking_crud.create_booking(db, booking, current_user.id)
        logger.info(f"Booking created: {db_booking.id}")
        return BookingResponse.model_validate(db_booking)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating booking: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error occurred while creating booking",
        )


@booking_router.get(
    "/bookings", response_model=List[BookingResponse], status_code=status.HTTP_200_OK
)
def get_user_bookings(
    skip: int = Query(0, ge=0, description="Number of bookings to skip"),
    limit: int = Query(100, ge=1, le=100, description="Number of bookings to retrieve"),
    booking_status: Optional[BookingStatus] = Query(
        None, description="Filter by booking status"
    ),
    service_id: Optional[UUID] = Query(None, description="Filter by service ID"),
    from_date: Optional[datetime] = Query(
        None, description="Filter bookings from this date"
    ),
    to_date: Optional[datetime] = Query(
        None, description="Filter bookings to this date"
    ),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get user's own bookings with optional filtering"""
    try:
        logger.info(f"User {current_user.email} fetching bookings")
        bookings = booking_crud.get_bookings(
            db=db,
            skip=skip,
            limit=limit,
            user_id=current_user.id,
            status=booking_status,
            service_id=service_id,
            from_date=from_date,
            to_date=to_date,
        )
        return [BookingResponse.model_validate(booking) for booking in bookings]

    except Exception as e:
        logger.error(f"Error fetching user bookings: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error occurred while fetching bookings",
        )


@booking_router.get(
    "/bookings/{booking_id}",
    response_model=BookingResponse,
    status_code=status.HTTP_200_OK,
)
def get_booking(
    booking_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get booking by ID (owner or admin)"""
    try:
        logger.info(f"Fetching booking: {booking_id}")
        booking = booking_crud.get_booking_by_id(db, booking_id)
        if not booking:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found"
            )

        # Check if user owns the booking (admins can access any booking)
        if current_user.role != "admin" and booking.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this booking",
            )

        return BookingResponse.model_validate(booking)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching booking {booking_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error occurred while fetching booking",
        )


@booking_router.patch(
    "/bookings/{booking_id}",
    response_model=BookingResponse,
    status_code=status.HTTP_200_OK,
)
def update_booking(
    booking_id: UUID,
    booking_update: BookingUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Update booking (owner can reschedule/cancel; admin can update status)"""
    try:
        logger.info(f"User {current_user.email} updating booking: {booking_id}")
        is_admin = current_user.role == "admin"
        user_id = None if is_admin else current_user.id

        updated_booking = booking_crud.update_booking(
            db, booking_id, booking_update, user_id, is_admin
        )
        logger.info(f"Booking updated: {booking_id}")
        return BookingResponse.model_validate(updated_booking)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating booking {booking_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error occurred while updating booking",
        )


@booking_router.delete(
    "/bookings/{booking_id}",
    response_model=BookingResponse,
    status_code=status.HTTP_200_OK,
)
def delete_booking(
    booking_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Delete booking (owner before start_time; admin anytime)"""
    try:
        logger.info(f"User {current_user.email} deleting booking: {booking_id}")
        is_admin = current_user.role == "admin"
        user_id = None if is_admin else current_user.id

        deleted_booking = booking_crud.delete_booking(db, booking_id, user_id, is_admin)
        logger.info(f"Booking deleted: {booking_id}")
        return BookingResponse.model_validate(deleted_booking)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting booking {booking_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error occurred while deleting booking",
        )


# ADMIN ENDPOINTS - Admin can view and manage all bookings


@booking_router.get(
    "/admin/bookings",
    response_model=List[BookingResponse],
    status_code=status.HTTP_200_OK,
)
def get_all_bookings(
    skip: int = Query(0, ge=0, description="Number of bookings to skip"),
    limit: int = Query(100, ge=1, le=100, description="Number of bookings to retrieve"),
    user_id: Optional[UUID] = Query(None, description="Filter by user ID"),
    service_id: Optional[UUID] = Query(None, description="Filter by service ID"),
    status: Optional[BookingStatus] = Query(
        None, description="Filter by booking status"
    ),
    from_date: Optional[datetime] = Query(
        None, description="Filter bookings from this date"
    ),
    to_date: Optional[datetime] = Query(
        None, description="Filter bookings to this date"
    ),
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """Get all bookings with filtering (admin only)"""
    try:
        logger.info(f"Admin {current_user.email} fetching all bookings")
        bookings = booking_crud.get_bookings(
            db=db,
            skip=skip,
            limit=limit,
            user_id=user_id,
            service_id=service_id,
            status=status,
            from_date=from_date,
            to_date=to_date,
        )
        return [BookingResponse.model_validate(booking) for booking in bookings]

    except Exception as e:
        logger.error(f"Error fetching all bookings: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error occurred while fetching bookings",
        )


@booking_router.patch(
    "/admin/bookings/{booking_id}/status",
    response_model=BookingResponse,
    status_code=status.HTTP_200_OK,
)
def update_booking_status(
    booking_id: UUID,
    status: BookingStatus,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """Update booking status (admin only)"""
    try:
        logger.info(
            f"Admin {current_user.email} updating booking {booking_id} status to {status}"
        )
        booking_update = BookingUpdate(status=status)
        updated_booking = booking_crud.update_booking(
            db, booking_id, booking_update, None, True  # is_admin=True
        )
        logger.info(f"Booking status updated: {booking_id} -> {status}")
        return BookingResponse.model_validate(updated_booking)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating booking status {booking_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error occurred while updating booking status",
        )


# SERVICE-RELATED ENDPOINTS


@booking_router.get(
    "/services/{service_id}/bookings",
    response_model=List[BookingResponse],
    status_code=status.HTTP_200_OK,
)
def get_service_bookings(
    service_id: UUID,
    skip: int = Query(0, ge=0, description="Number of bookings to skip"),
    limit: int = Query(100, ge=1, le=100, description="Number of bookings to retrieve"),
    status: Optional[BookingStatus] = Query(
        None, description="Filter by booking status"
    ),
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """Get all bookings for a specific service (admin only)"""
    try:
        logger.info(
            f"Admin {current_user.email} fetching bookings for service {service_id}"
        )
        bookings = booking_crud.get_service_bookings(db, service_id, skip, limit)

        # Apply status filter if provided
        if status:
            bookings = [booking for booking in bookings if booking.status == status]

        return [BookingResponse.model_validate(booking) for booking in bookings]

    except Exception as e:
        logger.error(f"Error fetching service bookings: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error occurred while fetching service bookings",
        )
