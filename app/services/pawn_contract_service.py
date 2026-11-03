from sqlalchemy.orm import Session

from datetime import date, timedelta
from dateutil.relativedelta import relativedelta

from app.models.pawn_contract import ContractStatus, PawnContract
from app.models.pawn_asset import PawnAsset

from app.models.customer import Customer

from app.schemas.customer import CustomerCreate

from app.repositories.customer_repository import (
    get_customer_by_id,
    get_customer_by_phone,
    get_customer_by_identity,
    add_customer_without_commit,
)
from app.repositories.pawn_contract_repository import (
    create_contract,
    generate_contract_code,
    get_contract_by_id,
    get_contract_by_id_for_update,
    list_contracts,
    update_contract,
    list_active_contracts_past_due,
    search_contracts_by_license_plate,
)

from app.repositories.pawn_asset_repository import (
    get_active_asset_by_license_plate,
)
from app.repositories.payment_repository import (
    has_payments_for_contract,
)
from app.schemas.pawn_contract import (
    PawnContractCreate,
    PawnContractUpdate,
    PawnContractResponse,
    PawnContractWithAssetsCreate,
    PawnContractWithCustomerAndAssetsCreate,
    PawnContractDetailsResponse,
    PawnContractSearchResponse,
)

from app.schemas.pawn_asset import PawnAssetCreate

from app.services.payment_service import (
    get_payment_summary,
)

from app.services.interest_calculation import calculate_monthly_interest

class PawnContractNotFoundError(Exception):
    pass


class PawnContractCodeAlreadyExistsError(Exception):
    pass


class PawnContractCustomerNotFoundError(Exception):
    pass


class InvalidPawnContractStatusError(Exception):
    pass

class LicensePlateAlreadyPawnedError(Exception):
    pass

class LiquidationContractNotOverdueError(Exception):
    pass


class LiquidationGracePeriodNotExpiredError(Exception):
    pass

class PawnContractNotEditableError(Exception):
    pass

class PawnContractHasPaymentsError(Exception):
    pass

class CustomerInformationConflictError(Exception):
    pass

def get_pawn_contract(
    db: Session,
    contract_id: int,
) -> PawnContract:
    contract = get_contract_by_id(db, contract_id)

    if contract is None:
        raise PawnContractNotFoundError

    return contract

def get_pawn_contract_details(
    db: Session,
    contract_id: int,
) -> PawnContractDetailsResponse:

    contract = get_pawn_contract(db, contract_id)

    payment_summary = get_payment_summary(db, contract_id)

    return PawnContractDetailsResponse(
        contract=contract,
        customer=contract.customer,
        assets=contract.assets,
        payments=contract.payments,
        payment_summary=payment_summary,
    )

def get_pawn_contracts(
    db: Session,
    offset: int = 0,
    limit: int = 20,
) -> list[PawnContract]:
    return list_contracts(
        db,
        offset=offset,
        limit=limit,
    )

def search_pawn_contracts_by_license_plate(
    db: Session,
    license_plate: str,
    offset: int = 0,
    limit: int = 20,
) -> list[PawnContractSearchResponse]:

    normalized_plate = license_plate.strip()

    if not normalized_plate:
        raise ValueError("License plate must not be empty")

    rows = search_contracts_by_license_plate(
        db,
        license_plate=normalized_plate,
        offset=offset,
        limit=limit,
    )

    return [
        PawnContractSearchResponse.model_validate(row)
        for row in rows
    ]

def create_new_pawn_contract(
    db: Session,
    contract_data: PawnContractCreate,
) -> PawnContract:
    customer = get_customer_by_id(
        db,
        contract_data.customer_id,
    )   

    if customer is None:
        raise PawnContractCustomerNotFoundError

    due_date = calculate_due_date(
        contract_data.start_date,
    )
    
    try:
        monthly_interest_amount = calculate_monthly_interest(
            contract_data.principal_amount
        )

        contract = create_contract(
            db,
            contract_data,
            due_date,
            monthly_interest_amount=monthly_interest_amount,
        )

        db.commit()
        db.refresh(contract)
        
        return contract
    except Exception:
        db.rollback()
        raise


def update_existing_pawn_contract(
    db: Session,
    contract_id: int,
    contract_data: PawnContractUpdate,
) -> PawnContract:
    try:
        # 1. Acquire a PostgreSQL row-level lock
        contract = get_contract_by_id_for_update(
            db,
            contract_id,
        )
        # 2. Check whether the contract exists
        if contract is None:
            raise PawnContractNotFoundError
        # 3. Only ACTIVE contracts can be edited
        if contract.status != ContractStatus.ACTIVE:
            raise PawnContractNotEditableError

        # 4. Contracts with payments cannot be edited
        if has_payments_for_contract(db, contract.id):
            raise PawnContractHasPaymentsError

        # 5. Validate customer_id if provided
        if "customer_id" in contract_data.model_fields_set:
            customer = get_customer_by_id(
                db,
                contract_data.customer_id,
            )

            if customer is None:
                raise PawnContractCustomerNotFoundError
        # 6. Calculate derived values
        new_monthly_interest = None
        new_due_date = None

        if "principal_amount" in contract_data.model_fields_set:
            new_monthly_interest = calculate_monthly_interest(
                contract_data.principal_amount
            )

        if "start_date" in contract_data.model_fields_set:
            new_due_date = calculate_due_date(
                contract_data.start_date
            )

        # 7. Update the contract
        updated_contract = update_contract(
            db,
            contract,
            contract_data,
        )
        # 8. Update calculated interest
        if new_monthly_interest is not None:
            updated_contract.monthly_interest_amount = new_monthly_interest

        # 9. Update due date
        if new_due_date is not None:
            updated_contract.due_date = new_due_date

        # 10. Regenerate contract code if start_date changes
        if "start_date" in contract_data.model_fields_set:
            updated_contract.contract_code = generate_contract_code(
                updated_contract.id,
                updated_contract.start_date,
            )

        # 11. Commit and release the row lock
        db.commit()
        db.refresh(updated_contract)

        return updated_contract

    except Exception:
        db.rollback()
        raise

def create_pawn_contract_with_assets(
    db: Session,
    contract_data: PawnContractWithAssetsCreate,
) -> PawnContract:
    customer = get_customer_by_id(
        db,
        contract_data.customer_id,
    )

    if customer is None:
        raise PawnContractCustomerNotFoundError

    for asset_data in contract_data.assets:
        if asset_data.license_plate is None:
            continue

        existing_asset = get_active_asset_by_license_plate(
            db,
            asset_data.license_plate,
        )

        if existing_asset is not None:
            raise LicensePlateAlreadyPawnedError

    due_date = calculate_due_date(
            contract_data.start_date,
    )

    try:
        monthly_interest_amount = calculate_monthly_interest(
            contract_data.principal_amount
        )

        contract_fields = contract_data.model_dump(
            exclude={
                "assets",
                "monthly_interest_amount",
            },
        )

        contract = PawnContract(
            **contract_fields,
            monthly_interest_amount=monthly_interest_amount,
            due_date=due_date,
        )

        db.add(contract)
        db.flush()
        
        contract.contract_code = generate_contract_code(
            contract.id,
            contract.start_date,
        )
        
        db.flush()

        for asset_data in contract_data.assets:
            asset = PawnAsset(
                contract_id=contract.id,
                **asset_data.model_dump(),
            )

            db.add(asset)

        db.commit()
        db.refresh(contract)

        return contract

    except Exception:
        db.rollback()
        raise



def mark_overdue_contracts(
    db: Session,
    as_of_date: date,
) -> list[PawnContract]:
    contracts = list_active_contracts_past_due(
        db,
        as_of_date,
    )

    try:
        for contract in contracts:
            contract.status = ContractStatus.OVERDUE

        db.commit()

        for contract in contracts:
            db.refresh(contract)

        return contracts

    except Exception:
        db.rollback()
        raise

def calculate_days_overdue(
    due_date: date,
    as_of_date: date,
) -> int:
    if due_date < as_of_date:
        return (as_of_date - due_date).days
    return 0

def calculate_overdue_bucket(
    days_overdue: int,
) -> str:
    if days_overdue < 0:
        raise ValueError(
            "days_overdue cannot be negative"
        )

    if days_overdue == 0:
        return "not_overdue"

    if days_overdue <= 30:
        return "overdue_1_30"

    if days_overdue <= 60:
        return "overdue_31_60"

    if days_overdue <= 90:
        return "overdue_61_90"

    return "over_90_plus"

def build_pawn_contract_response(
    contract: PawnContract,
    as_of_date: date,
) -> PawnContractResponse:
    days_overdue = calculate_days_overdue(
        contract.due_date,
        as_of_date,
    )

    overdue_bucket = calculate_overdue_bucket(
        days_overdue,
    )

    return PawnContractResponse(
        id=contract.id,
        contract_code=contract.contract_code,
        customer_id=contract.customer_id,
        principal_amount=contract.principal_amount,
        monthly_interest_amount=contract.monthly_interest_amount,
        start_date=contract.start_date,
        due_date=contract.due_date,
        status=contract.status,
        days_overdue=days_overdue,
        overdue_bucket=overdue_bucket,
    )

def liquidate_contract(
    db: Session,
    contract_id: int,
    as_of_date: date,
) -> PawnContract: 
    contract = get_pawn_contract(
        db,
        contract_id,
    )

    if contract.status != ContractStatus.OVERDUE:
        raise LiquidationContractNotOverdueError

    liquidation_eligible_date = (
        contract.due_date
        + timedelta(days=3)
    )

    if as_of_date <= liquidation_eligible_date:
        raise LiquidationGracePeriodNotExpiredError

    try:
        contract.status = ContractStatus.LIQUIDATED

        db.commit()
        db.refresh(contract)

        return contract

    except Exception:
        db.rollback()
        raise

def calculate_due_date(
    start_date: date,
) -> date:
    return start_date + relativedelta(months=1)

def find_or_create_customer(
    db: Session,
    customer_data: CustomerCreate,
) -> Customer:

    customer_by_phone = get_customer_by_phone(
        db,
        customer_data.phone,
    )

    customer_by_identity = None

    if customer_data.identity is not None:
        customer_by_identity = get_customer_by_identity(
            db,
            customer_data.identity,
        )

    # CASE 1: Phone và identity thuộc hai Customer khác nhau
    if (
        customer_by_phone is not None
        and customer_by_identity is not None
        and customer_by_phone.id != customer_by_identity.id
    ):
        raise CustomerInformationConflictError(
            "Phone and identity belong to different customers."
        )

    # CASE 2: Tìm thấy Customer cũ
    existing_customer = (
        customer_by_identity or customer_by_phone
    )

    if existing_customer is not None:

        # Không tự động thay đổi tên
        if existing_customer.name != customer_data.name:
            raise CustomerInformationConflictError(
                "Customer name does not match existing records."
            )

        # Không tự động thay đổi số điện thoại
        if existing_customer.phone != customer_data.phone:
            raise CustomerInformationConflictError(
                "Customer phone does not match existing records."
            )

        # Không tự động thay đổi identity
        if (
            customer_data.identity is not None
            and existing_customer.identity != customer_data.identity
        ):
            raise CustomerInformationConflictError(
                "Customer identity does not match existing records."
            )

        return existing_customer

    # CASE 3: Không tìm thấy Customer
    return add_customer_without_commit(
        db,
        customer_data,
    )

def create_pawn_contract_with_customer_and_assets(
    db: Session,
    data: PawnContractWithCustomerAndAssetsCreate,
) -> PawnContract:

    try:
        # 1. Kiểm tra các biển số xe đang được cầm
        license_plates = [
            asset.license_plate
            for asset in data.assets
            if asset.license_plate is not None
        ]

        # Không cho phép trùng biển số trong cùng request
        if len(license_plates) != len(set(license_plates)):
            raise LicensePlateAlreadyPawnedError

        for license_plate in license_plates:
            existing_asset = get_active_asset_by_license_plate(
                db,
                license_plate,
            )

            if existing_asset is not None:
                raise LicensePlateAlreadyPawnedError

        # 2. Tìm khách hàng cũ hoặc tìm/tạo khách hàng từ thông tin cá nhân
        if data.customer_id is not None:
            customer = get_customer_by_id(
                db,
                data.customer_id,
            )

            if customer is None:
                raise PawnContractCustomerNotFoundError

        else:
            customer = find_or_create_customer(
                db,
                data.customer,
            )

        # 3. Tạo PawnContract

        monthly_interest_amount = calculate_monthly_interest(
                data.contract.principal_amount
        )

        contract_fields = data.contract.model_dump(
            exclude={"monthly_interest_amount"},
        )

        contract_data = PawnContractCreate(
            customer_id=customer.id,
            **contract_fields,
        )

        contract = create_contract(
            db,
            contract_data,
            calculate_due_date(contract_data.start_date),
            monthly_interest_amount=monthly_interest_amount,
        )

        # 4. Tạo PawnAssets
        for asset_data in data.assets:
            asset = PawnAsset(
                contract_id=contract.id,
                **asset_data.model_dump(),
            )

            db.add(asset)

        # 5. Commit tất cả cùng lúc
        db.commit()
        db.refresh(contract)

        return contract

    except Exception:
        db.rollback()
        raise
