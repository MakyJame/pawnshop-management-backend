from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.customer import (
    CustomerCreate,
    CustomerResponse,
    CustomerUpdate,
)
from app.services.customer_service import (
    CustomerNotFoundError,
    CustomerPhoneAlreadyExistsError,
    create_new_customer,
    delete_existing_customer,
    get_customer,
    get_customers,
    update_existing_customer,
)


router = APIRouter(
    prefix="/customers",
    tags=["Customers"],
)


@router.post(
    "",
    response_model=CustomerResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_customer_endpoint(
    customer_data: CustomerCreate,
    db: Session = Depends(get_db),
) -> CustomerResponse:
    try:
        return create_new_customer(
            db,
            customer_data,
        )
    except CustomerPhoneAlreadyExistsError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Customer phone already exists.",
        ) from error


@router.get(
    "",
    response_model=list[CustomerResponse],
)
def list_customers_endpoint(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> list[CustomerResponse]:
    return get_customers(
        db,
        offset=offset,
        limit=limit,
    )


@router.get(
    "/{customer_id}",
    response_model=CustomerResponse,
)
def get_customer_endpoint(
    customer_id: int,
    db: Session = Depends(get_db),
) -> CustomerResponse:
    try:
        return get_customer(
            db,
            customer_id,
        )
    except CustomerNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found.",
        ) from error


@router.patch(
    "/{customer_id}",
    response_model=CustomerResponse,
)
def update_customer_endpoint(
    customer_id: int,
    customer_data: CustomerUpdate,
    db: Session = Depends(get_db),
) -> CustomerResponse:
    try:
        return update_existing_customer(
            db,
            customer_id,
            customer_data,
        )
    except CustomerNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found.",
        ) from error
    except CustomerPhoneAlreadyExistsError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Customer phone already exists.",
        ) from error


@router.delete(
    "/{customer_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_customer_endpoint(
    customer_id: int,
    db: Session = Depends(get_db),
) -> Response:
    try:
        delete_existing_customer(
            db,
            customer_id,
        )
    except CustomerNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found.",
        ) from error

    return Response(
        status_code=status.HTTP_204_NO_CONTENT,
    )
