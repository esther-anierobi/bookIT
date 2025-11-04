from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import List, Optional
from uuid import UUID
from datetime import datetime, timezone
from app.models.booking_model import Booking
from app.models.service_model import Service
from app.schemas.booking_schema import BookingCreate, BookingUpdate
from app.logger import get_logger

logger = get_logger(__name__)


class BookingCRUD:
    @staticmethod
    def create_booking(db: Session, booking: BookingCreate, user_id: UUID) -> Booking:
        """Create a new booking with time conflict validation"""
        # Convert UUIDs to strings for database query
        service_id_str = str(booking.service_id)
        user_id_str = str(user_id)

        # Verify service exists and is active
        service = (
            db.query(Service)
            .filter(Service.id == service_id_str, Service.is_active == True)
            .first()
        )
        if not service:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Service not found or is inactive",
            )

        # Check for time conflicts with existing bookings for the same service
        if BookingCRUD._has_time_conflict(
                db, service_id_str, booking.start_time, booking.end_time
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Time slot is already booked for this service",
            )

        try:
            db_booking = Booking(
                user_id=user_id_str,
                service_id=service_id_str,
                start_time=booking.start_time,
                end_time=booking.end_time,
                status="pending",
            )
            db.add(db_booking)
            db.commit()
            db.refresh(db_booking)
            logger.info(f"Booking created: {db_booking.id} by user {user_id}")
            return db_booking

        except Exception as e:
            db.rollback()
            logger.error(f"Error creating booking: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error occurred while creating booking",
            )

    @staticmethod
    def _has_time_conflict(
            db: Session,
            service_id: str,
            start_time: datetime,
            end_time: datetime,
            exclude_booking_id: Optional[str] = None,
    ) -> bool:
        """Check if there's a time conflict for a service booking"""
        query = db.query(Booking).filter(
            and_(
                Booking.service_id == service_id,
                Booking.status.in_(["pending", "confirmed"]),
                or_(
                    # New booking starts during existing booking
                    and_(
                        Booking.start_time <= start_time, start_time < Booking.end_time
                    ),
                    # New booking ends during existing booking
                    and_(Booking.start_time < end_time, end_time <= Booking.end_time),
                    # New booking encompasses existing booking
                    and_(
                        start_time <= Booking.start_time, Booking.end_time <= end_time
                    ),
                ),
            )
        )

        # Exclude current booking if updating
        if exclude_booking_id:
            query = query.filter(Booking.id != exclude_booking_id)

        return query.first() is not None

    @staticmethod
    def get_booking_by_id(db: Session, booking_id: UUID) -> Optional[Booking]:
        """Get booking by ID"""
        booking_id_str = str(booking_id)
        return db.query(Booking).filter(Booking.id == booking_id_str).first()

    @staticmethod
    def get_bookings(
            db: Session,
            skip: int = 0,
            limit: int = 100,
            user_id: Optional[UUID] = None,
            service_id: Optional[UUID] = None,
            status: Optional[str] = None,
            from_date: Optional[datetime] = None,
            to_date: Optional[datetime] = None,
    ) -> List[Booking]:
        """Get bookings with optional filtering"""
        query = db.query(Booking)

        # Filter by user (for user's own bookings)
        if user_id:
            user_id_str = str(user_id)
            query = query.filter(Booking.user_id == user_id_str)

        # Filter by service
        if service_id:
            service_id_str = str(service_id)
            query = query.filter(Booking.service_id == service_id_str)

        # Filter by status
        if status:
            query = query.filter(Booking.status == status)

        # Filter by date range
        if from_date:
            query = query.filter(Booking.start_time >= from_date)
        if to_date:
            query = query.filter(Booking.start_time <= to_date)

        return query.order_by(Booking.start_time.desc()).offset(skip).limit(limit).all()

    @staticmethod
    def get_user_bookings(
            db: Session, user_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[Booking]:
        """Get all bookings for a specific user"""
        user_id_str = str(user_id)
        return BookingCRUD.get_bookings(db=db, user_id=user_id_str, skip=skip, limit=limit)

    @staticmethod
    def update_booking(
            db: Session,
            booking_id: UUID,
            booking_update: BookingUpdate,
            user_id: Optional[UUID] = None,
            is_admin: bool = False,
    ) -> Booking:
        """Update booking with proper authorization and validation"""
        booking_id_str = str(booking_id)
        user_id_str = str(user_id)

        db_booking = db.query(Booking).filter(Booking.id == booking_id_str).first()
        if not db_booking:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found"
            )

        # Authorization check
        if not is_admin and user_id_str and db_booking.user_id != user_id_str:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this booking",
            )

        # Business logic validation
        update_data = booking_update.model_dump(exclude_unset=True)

        # Check if user is trying to reschedule
        if ("start_time" in update_data or "end_time" in update_data) and not is_admin:
            if db_booking.status not in [
                "pending",
                "confirmed",
            ]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Can only reschedule pending or confirmed bookings",
                )

        # Check if user is trying to cancel
        if (
                "status" in update_data
                and update_data["status"] == "cancelled"
                and not is_admin
        ):
            if db_booking.status not in [
                "pending",
                "confirmed",
            ]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Can only cancel pending or confirmed bookings",
                )

        try:
            # Check for time conflicts if updating time
            if "start_time" in update_data or "end_time" in update_data:
                new_start = update_data.get("start_time", db_booking.start_time)
                new_end = update_data.get("end_time", db_booking.end_time)

                if BookingCRUD._has_time_conflict(
                        db, db_booking.service_id, new_start, new_end, booking_id_str
                ):
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Time slot is already booked for this service",
                    )

            # Update booking
            for key, value in update_data.items():
                if value is not None:
                    setattr(db_booking, key, value)

            db.commit()
            db.refresh(db_booking)
            logger.info(f"Booking updated: {booking_id}")
            return db_booking

        except HTTPException:
            raise
        except Exception as e:
            db.rollback()
            logger.error(f"Error updating booking {booking_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error occurred while updating booking",
            )

    @staticmethod
    def delete_booking(
            db: Session,
            booking_id: UUID,
            user_id: Optional[UUID] = None,
            is_admin: bool = False,
    ) -> Booking:
        """Delete booking with proper authorization"""
        booking_id_str = str(booking_id)
        user_id_str = str(user_id)

        db_booking = db.query(Booking).filter(Booking.id == booking_id_str).first()
        if not db_booking:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found"
            )

        # Authorization check
        if not is_admin and user_id_str and db_booking.user_id != user_id_str:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this booking",
            )

        # Business logic: Users can only delete before start time, admins can delete anytime
        now = datetime.now(timezone.utc)
        start_time = db_booking.start_time
        # If start_time is timezone-naive, assume it's UTC
        if start_time.tzinfo is None:
            start_time = start_time.replace(tzinfo=timezone.utc)

        if not is_admin and start_time <= now:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete booking that has already started",
            )

        try:
            db.delete(db_booking)
            db.commit()
            logger.info(f"Booking deleted: {booking_id}")
            return db_booking

        except Exception as e:
            db.rollback()
            logger.error(f"Error deleting booking {booking_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error occurred while deleting booking",
            )


    @staticmethod
    def get_service_bookings(
            db: Session, service_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[Booking]:
        """Get all bookings for a specific service"""
        service_id_str = str(service_id)
        return BookingCRUD.get_bookings(
            db=db, service_id=service_id_str, skip=skip, limit=limit
        )


booking_crud = BookingCRUD()
