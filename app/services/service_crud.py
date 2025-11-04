from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Optional
from uuid import UUID
from app.models.service_model import Service
from app.schemas.service_schema import ServiceCreate, ServiceUpdate
from app.logger import get_logger

logger = get_logger(__name__)


class ServiceCRUD:
    @staticmethod
    def create_service(db: Session, service: ServiceCreate, owner_id: UUID) -> Service:
        """Create a new service"""
        try:
            db_service = Service(
                title=service.title,
                description=service.description,
                price=service.price,
                duration_minutes=service.duration_minutes,
                owner_id=owner_id
            )
            db.add(db_service)
            db.commit()
            db.refresh(db_service)
            logger.info(f"Service created: {service.title} by owner {owner_id}")
            return db_service

        except Exception as e:
            db.rollback()
            logger.error(f"Error creating service: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error occurred while creating service"
            )

    @staticmethod
    def get_service_by_id(db: Session, service_id: UUID) -> Optional[Service]:
        """Get service by ID"""
        return db.query(Service).filter(Service.id == str(service_id)).first()

    @staticmethod
    def get_services(
            db: Session,
            skip: int = 0,
            limit: int = 100,
            q: Optional[str] = None,
            price_min: Optional[float] = None,
            price_max: Optional[float] = None,
            active: Optional[bool] = None,
            owner_id: Optional[UUID] = None
    ) -> List[Service]:
        """Get services with optional filtering"""
        query = db.query(Service)

        # Filter by search query (title or description)
        if q:
            query = query.filter(
                or_(
                    Service.title.ilike(f"%{q}%"),
                    Service.description.ilike(f"%{q}%")
                )
            )

        # Filter by price range
        if price_min is not None:
            query = query.filter(Service.price >= price_min)
        if price_max is not None:
            query = query.filter(Service.price <= price_max)

        # Filter by active status
        if active is not None:
            query = query.filter(Service.is_active == active)

        # Filter by owner (for admin or owner views)
        if owner_id:
            query = query.filter(Service.owner_id == owner_id)

        return query.offset(skip).limit(limit).all()

    @staticmethod
    def get_active_services(
            db: Session,
            skip: int = 0,
            limit: int = 100,
            q: Optional[str] = None,
            price_min: Optional[float] = None,
            price_max: Optional[float] = None
    ) -> List[Service]:
        """Get only active services (public endpoint)"""
        return ServiceCRUD.get_services(
            db=db, skip=skip, limit=limit, q=q,
            price_min=price_min, price_max=price_max, active=True
        )

    @staticmethod
    def update_service(db: Session, service_id: UUID, service_update: ServiceUpdate,
                       owner_id: Optional[UUID] = None) -> Service:
        """Update service by ID"""
        db_service = db.query(Service).filter(Service.id == str(service_id)).first()
        if not db_service:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Service not found"
            )

        # Check ownership (if owner_id provided, ensure user owns the service)
        if owner_id and db_service.owner_id != str(owner_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this service"
            )

        try:
            # Update only provided fields
            for key, value in service_update.model_dump(exclude_unset=True).items():
                if value is not None:
                    setattr(db_service, key, value)

            db.commit()
            db.refresh(db_service)
            logger.info(f"Service updated: {service_id}")
            return db_service

        except Exception as e:
            db.rollback()
            logger.error(f"Error updating service {service_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error occurred while updating service"
            )

    @staticmethod
    def delete_service(db: Session, service_id: UUID, owner_id: Optional[UUID] = None) -> Service:
        # Soft delete service by setting is_active to False
        db_service = db.query(Service).filter(Service.id == str(service_id)).first()
        if not db_service:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Service not found"
            )

        # Check ownership (if owner_id provided, ensure user owns the service)
        if owner_id and db_service.owner_id != owner_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this service"
            )

        try:
            db_service.is_active = False
            db.commit()
            db.refresh(db_service)
            logger.info(f"Service deleted : {service_id}")
            return db_service

        except Exception as e:
            db.rollback()
            logger.error(f"Error deleting service {service_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error occurred while deleting service"
            )

    @staticmethod
    def get_services_by_owner(db: Session, owner_id: UUID, skip: int = 0, limit: int = 100) -> List[Service]:
        """Get all services owned by a specific user"""
        return db.query(Service).filter(Service.owner_id == str(owner_id)).offset(skip).limit(limit).all()


service_crud = ServiceCRUD()
