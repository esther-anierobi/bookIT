from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List, Optional
from app.services.service_crud import service_crud
from app.schemas.service_schema import ServiceCreate, ServiceUpdate, ServiceResponse
from app.database import get_db
from app.security.auth import get_current_admin_user
from app.models.user_model import User
from app.logger import get_logger

service_router = APIRouter()
logger = get_logger(__name__)

# PUBLIC ENDPOINTS - Anyone can browse services


@service_router.get(
    "/services", response_model=List[ServiceResponse], status_code=status.HTTP_200_OK
)
def get_services(
    skip: int = Query(0, ge=0, description="Number of services to skip"),
    limit: int = Query(100, ge=1, le=100, description="Number of services to retrieve"),
    q: Optional[str] = Query(None, description="Search query for title or description"),
    price_min: Optional[float] = Query(None, ge=0, description="Minimum price filter"),
    price_max: Optional[float] = Query(None, ge=0, description="Maximum price filter"),
    db: Session = Depends(get_db),
):
    """Get all active services with optional filtering (public endpoint)"""
    try:
        logger.info(f"Fetching services: skip={skip}, limit={limit}, q={q}")
        services = service_crud.get_active_services(
            db=db, skip=skip, limit=limit, q=q, price_min=price_min, price_max=price_max
        )
        return [ServiceResponse.model_validate(service) for service in services]

    except Exception as e:
        logger.error(f"Error fetching services: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error occurred while fetching services",
        )


@service_router.get(
    "/services/{service_id}",
    response_model=ServiceResponse,
    status_code=status.HTTP_200_OK,
)
def get_service(service_id: UUID, db: Session = Depends(get_db)):
    """Get service by ID (public endpoint)"""
    try:
        logger.info(f"Fetching service: {service_id}")
        service = service_crud.get_service_by_id(db, service_id)
        if not service:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Service not found"
            )

        # Only return active services for public endpoint
        if not service.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Service not found"
            )

        return ServiceResponse.model_validate(service)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching service {service_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error occurred while fetching service",
        )


# ADMIN ENDPOINTS - Service management


@service_router.post(
    "/services", response_model=ServiceResponse, status_code=status.HTTP_201_CREATED
)
def create_service(
    service: ServiceCreate,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """Create a new service (admin only)"""
    try:
        logger.info(f"Admin {current_user.email} creating service: {service.title}")
        db_service = service_crud.create_service(db, service, current_user.id)
        logger.info(f"Service created: {db_service.id}")
        return ServiceResponse.model_validate(db_service)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error occurred while creating service",
        )


@service_router.patch(
    "/services/{service_id}",
    response_model=ServiceResponse,
    status_code=status.HTTP_200_OK,
)
def update_service(
    service_id: UUID,
    service_update: ServiceUpdate,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """Update service by ID (admin only)"""
    try:
        logger.info(f"Admin {current_user.email} updating service: {service_id}")
        updated_service = service_crud.update_service(db, service_id, service_update)
        logger.info(f"Service updated: {service_id}")
        return ServiceResponse.model_validate(updated_service)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating service {service_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error occurred while updating service",
        )


@service_router.delete(
    "/services/{service_id}",
    response_model=ServiceResponse,
    status_code=status.HTTP_200_OK,
)
def delete_service(
    service_id: UUID,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """Soft delete service by ID (admin only)"""
    try:
        logger.info(f"Admin {current_user.email} deleting service: {service_id}")
        deleted_service = service_crud.delete_service(db, service_id)
        logger.info(f"Service deleted: {service_id}")
        return ServiceResponse.model_validate(deleted_service)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting service {service_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error occurred while deleting service",
        )


# ADMIN MANAGEMENT ENDPOINTS


@service_router.get(
    "/admin/services",
    response_model=List[ServiceResponse],
    status_code=status.HTTP_200_OK,
)
def get_all_services_admin(
    skip: int = Query(0, ge=0, description="Number of services to skip"),
    limit: int = Query(100, ge=1, le=100, description="Number of services to retrieve"),
    q: Optional[str] = Query(None, description="Search query for title or description"),
    price_min: Optional[float] = Query(None, ge=0, description="Minimum price filter"),
    price_max: Optional[float] = Query(None, ge=0, description="Maximum price filter"),
    active: Optional[bool] = Query(None, description="Filter by active status"),
    owner_id: Optional[UUID] = Query(None, description="Filter by owner ID"),
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """Get all services including inactive ones (admin only)"""
    try:
        logger.info(f"Admin {current_user.email} fetching all services")
        services = service_crud.get_services(
            db=db,
            skip=skip,
            limit=limit,
            q=q,
            price_min=price_min,
            price_max=price_max,
            active=active,
            owner_id=owner_id,
        )
        return [ServiceResponse.model_validate(service) for service in services]

    except Exception as e:
        logger.error(f"Error fetching all services: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error occurred while fetching services",
        )


@service_router.get(
    "/admin/services/{service_id}",
    response_model=ServiceResponse,
    status_code=status.HTTP_200_OK,
)
def get_service_admin(
    service_id: UUID,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """Get service by ID including inactive ones (admin only)"""
    try:
        logger.info(f"Admin {current_user.email} fetching service: {service_id}")
        service = service_crud.get_service_by_id(db, service_id)
        if not service:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Service not found"
            )

        return ServiceResponse.model_validate(service)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching service {service_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error occurred while fetching service",
        )
