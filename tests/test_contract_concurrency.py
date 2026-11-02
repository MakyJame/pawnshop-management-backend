import time

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.exc import OperationalError

from app.models.customer import Customer
from app.models.pawn_contract import PawnContract
from app.repositories.pawn_contract_repository import (
    get_contract_by_id_for_update,
)

from tests.conftest import TestingSessionLocal

from concurrent.futures import ThreadPoolExecutor
from threading import Event

from sqlalchemy import func, select, text, delete

from app.models.payment import Payment, PaymentType
from app.schemas.payment import PaymentCreate
from app.schemas.pawn_contract import PawnContractUpdate
from app.services.payment_service import create_new_payment
from app.services.pawn_contract_service import (
    PawnContractHasPaymentsError,
    update_existing_pawn_contract,
)
import app.services.pawn_contract_service as contract_service

from uuid import uuid4

def test_contract_row_lock_blocks_second_transaction():
    session_a = TestingSessionLocal()
    session_b = TestingSessionLocal()

    contract_id = None

    try:
        # --------------------------------------------------
        # 1. Prepare committed test data
        # --------------------------------------------------
        customer = Customer(
            name="Concurrency Test Customer",
            phone="0900000999",
        )

        session_a.add(customer)
        session_a.flush()

        contract = PawnContract(
            customer_id=customer.id,
            principal_amount=Decimal("10000000"),
            monthly_interest_amount=Decimal("300000"),
            start_date=date(2026, 11, 1),
            due_date=date(2026, 12, 1),
        )

        session_a.add(contract)
        session_a.commit()

        contract_id = contract.id

        # --------------------------------------------------
        # 2. Transaction A acquires the row lock
        # --------------------------------------------------
        contract_a = get_contract_by_id_for_update(
            session_a,
            contract_id,
        )

        assert contract_a is not None

        # --------------------------------------------------
        # 3. Transaction B attempts to acquire the same lock
        # --------------------------------------------------
        session_b.execute(
            text("SET LOCAL lock_timeout = '1000ms'")
        )

        with pytest.raises(OperationalError) as exc_info:
            get_contract_by_id_for_update(
                session_b,
                contract_id,
            )

        # PostgreSQL lock_not_available
        assert exc_info.value.orig.sqlstate == "55P03"

        # --------------------------------------------------
        # 4. Transaction A releases the lock
        # --------------------------------------------------
        session_a.rollback()

        # Transaction B must recover from its failed query
        session_b.rollback()

        # --------------------------------------------------
        # 5. Transaction B retries and acquires the lock
        # --------------------------------------------------
        contract_b = get_contract_by_id_for_update(
            session_b,
            contract_id,
        )

        assert contract_b is not None
        assert contract_b.id == contract_id

    finally:
        session_b.rollback()
        session_a.rollback()

        session_b.close()
        session_a.close()

def test_payment_blocks_concurrent_contract_patch():
    payment_lock_acquired = Event()
    release_payment_lock = Event()
    patch_connection_ready = Event()

    backend_pids = {}

    # --------------------------------------------------
    # 1. Create committed test data
    # --------------------------------------------------
    with TestingSessionLocal() as setup_session:
        customer = Customer(
            name="Payment Concurrency Customer",
            phone="0900000888",
        )

        setup_session.add(customer)
        setup_session.flush()

        contract = PawnContract(
            customer_id=customer.id,
            principal_amount=Decimal("10000000"),
            monthly_interest_amount=Decimal("300000"),
            start_date=date(2026, 11, 1),
            due_date=date(2026, 12, 1),
        )

        setup_session.add(contract)
        setup_session.flush()

        contract_id = contract.id
        setup_session.commit()

    # --------------------------------------------------
    # 2. Payment worker
    # --------------------------------------------------
    def payment_worker():
        with TestingSessionLocal() as session:
            try:
                session.execute(
                    text("SET LOCAL lock_timeout = '5000ms'")
                )

                backend_pids["payment"] = session.scalar(
                    text("SELECT pg_backend_pid()")
                )

                locked_contract = get_contract_by_id_for_update(
                    session,
                    contract_id,
                )

                assert locked_contract is not None

                payment_lock_acquired.set()

                assert release_payment_lock.wait(timeout=10)

                payment_data = PaymentCreate(
                    contract_id=contract_id,
                    amount=Decimal("500000"),
                    payment_type=PaymentType.INTEREST,
                    payment_date=date(2026, 11, 2),
                )

                return create_new_payment(
                    session,
                    payment_data,
                )

            finally:
                session.rollback()

    # --------------------------------------------------
    # 3. PATCH worker
    # --------------------------------------------------
    def patch_worker():
        with TestingSessionLocal() as session:
            session.execute(
                text("SET LOCAL lock_timeout = '5000ms'")
            )

            backend_pids["patch"] = session.scalar(
                text("SELECT pg_backend_pid()")
            )

            patch_connection_ready.set()

            patch_data = PawnContractUpdate(
                principal_amount=Decimal("12000000"),
            )

            try:
                update_existing_pawn_contract(
                    session,
                    contract_id,
                    patch_data,
                )
            except PawnContractHasPaymentsError:
                return "PATCH_REJECTED"

            return "PATCH_ACCEPTED"

    # --------------------------------------------------
    # 4. Run concurrent transactions
    # --------------------------------------------------
    with ThreadPoolExecutor(max_workers=2) as executor:
        payment_future = executor.submit(payment_worker)
        patch_future = None

        try:
            assert payment_lock_acquired.wait(timeout=5)

            patch_future = executor.submit(patch_worker)

            assert patch_connection_ready.wait(timeout=5)

            payment_pid = backend_pids["payment"]
            patch_pid = backend_pids["patch"]

            blocking_confirmed = False
            deadline = time.monotonic() + 3

            while time.monotonic() < deadline:
                with TestingSessionLocal() as monitor_session:
                    blocking_pids = monitor_session.scalar(
                        text("SELECT pg_blocking_pids(:patch_pid)"),
                        {"patch_pid": patch_pid},
                    )

                if payment_pid in blocking_pids:
                    blocking_confirmed = True
                    break

                if patch_future.done():
                    break

                time.sleep(0.05)

            assert blocking_confirmed, (
                "PATCH was not blocked by Payment transaction"
            )

        finally:
            # Always release the Payment worker,
            # even if a test assertion fails.
            release_payment_lock.set()

        payment_future.result(timeout=10)
        patch_result = patch_future.result(timeout=10)

    # --------------------------------------------------
    # 5. Verify business outcome
    # --------------------------------------------------
    assert patch_result == "PATCH_REJECTED"

    with TestingSessionLocal() as verify_session:
        contract = verify_session.get(
            PawnContract,
            contract_id,
        )

        assert contract is not None

        assert contract.principal_amount == Decimal("10000000")

        payment_count = verify_session.scalar(
            select(func.count(Payment.id)).where(
                Payment.contract_id == contract_id
            )
        )

        assert payment_count == 1

def test_patch_blocks_concurrent_payment(monkeypatch):
    patch_lock_acquired = Event()
    release_patch_lock = Event()
    payment_connection_ready = Event()

    backend_pids = {}

    # --------------------------------------------------
    # 1. Create committed test data
    # --------------------------------------------------
    with TestingSessionLocal() as setup_session:
        customer = Customer(
            name="Patch Concurrency Customer",
            phone=f"09{uuid4().hex[:10]}",
        )

        setup_session.add(customer)
        setup_session.flush()

        contract = PawnContract(
            customer_id=customer.id,
            principal_amount=Decimal("10000000"),
            monthly_interest_amount=Decimal("300000"),
            start_date=date(2026, 11, 1),
            due_date=date(2026, 12, 1),
        )

        setup_session.add(contract)
        setup_session.flush()

        contract_id = contract.id

        setup_session.commit()

    # --------------------------------------------------
    # 2. Wrap the real repository locking function
    # --------------------------------------------------
    original_get_for_update = (
        contract_service.get_contract_by_id_for_update
    )

    def controlled_get_for_update(session, requested_contract_id):
        locked_contract = original_get_for_update(
            session,
            requested_contract_id,
        )

        if locked_contract is not None:
            patch_lock_acquired.set()

            if not release_patch_lock.wait(timeout=10):
                raise TimeoutError(
                    "Timed out waiting to release PATCH lock"
                )

        return locked_contract

    monkeypatch.setattr(
        contract_service,
        "get_contract_by_id_for_update",
        controlled_get_for_update,
    )

    # --------------------------------------------------
    # 3. PATCH worker
    # --------------------------------------------------
    def patch_worker():
        with TestingSessionLocal() as session:
            session.execute(
                text("SET LOCAL lock_timeout = '5000ms'")
            )

            backend_pids["patch"] = session.scalar(
                text("SELECT pg_backend_pid()")
            )

            patch_data = PawnContractUpdate(
                principal_amount=Decimal("12000000"),
            )

            return contract_service.update_existing_pawn_contract(
                session,
                contract_id,
                patch_data,
            )

    # --------------------------------------------------
    # 4. Payment worker
    # --------------------------------------------------
    def payment_worker():
        with TestingSessionLocal() as session:
            session.execute(
                text("SET LOCAL lock_timeout = '5000ms'")
            )

            backend_pids["payment"] = session.scalar(
                text("SELECT pg_backend_pid()")
            )

            payment_connection_ready.set()

            payment_data = PaymentCreate(
                contract_id=contract_id,
                amount=Decimal("500000"),
                payment_type=PaymentType.INTEREST,
                payment_date=date(2026, 11, 2),
            )

            return create_new_payment(
                session,
                payment_data,
            )

    # --------------------------------------------------
    # 5. Execute concurrent services
    # --------------------------------------------------
    with ThreadPoolExecutor(max_workers=2) as executor:
        patch_future = executor.submit(patch_worker)
        payment_future = None

        try:
            assert patch_lock_acquired.wait(timeout=5), (
                "PATCH did not acquire the contract lock"
            )

            payment_future = executor.submit(payment_worker)

            assert payment_connection_ready.wait(timeout=5), (
                "Payment connection was not ready"
            )

            patch_pid = backend_pids["patch"]
            payment_pid = backend_pids["payment"]

            blocking_confirmed = False
            deadline = time.monotonic() + 3

            while time.monotonic() < deadline:
                with TestingSessionLocal() as monitor_session:
                    blocking_pids = monitor_session.scalar(
                        text(
                            "SELECT pg_blocking_pids(:payment_pid)"
                        ),
                        {"payment_pid": payment_pid},
                    )

                if patch_pid in blocking_pids:
                    blocking_confirmed = True
                    break

                if payment_future.done():
                    break

                time.sleep(0.05)

            assert blocking_confirmed, (
                "Payment was not blocked by PATCH transaction"
            )

        finally:
            release_patch_lock.set()

        patch_result = patch_future.result(timeout=10)
        payment_result = payment_future.result(timeout=10)

    # --------------------------------------------------
    # 6. Verify business outcome
    # --------------------------------------------------
    assert patch_result is not None
    assert payment_result is not None

    with TestingSessionLocal() as verify_session:
        updated_contract = verify_session.get(
            PawnContract,
            contract_id,
        )

        assert updated_contract is not None

        assert updated_contract.principal_amount == Decimal(
            "12000000"
        )

        payment_count = verify_session.scalar(
            select(func.count(Payment.id)).where(
                Payment.contract_id == contract_id
            )
        )

        assert payment_count == 1

@pytest.fixture
def committed_contract():
    with TestingSessionLocal() as session:
        customer = Customer(
            name="Concurrency Test Customer",
            phone=f"09{uuid4().hex[:10]}",
        )

        session.add(customer)
        session.flush()

        contract = PawnContract(
            customer_id=customer.id,
            principal_amount=Decimal("10000000"),
            monthly_interest_amount=Decimal("300000"),
            start_date=date(2026, 11, 1),
            due_date=date(2026, 12, 1),
        )

        session.add(contract)
        session.flush()

        customer_id = customer.id
        contract_id = contract.id

        session.commit()

    try:
        yield contract_id
    finally:
        with TestingSessionLocal() as cleanup_session:
            cleanup_session.execute(
                delete(Payment).where(
                    Payment.contract_id == contract_id
                )
            )

            cleanup_session.execute(
                delete(PawnContract).where(
                    PawnContract.id == contract_id
                )
            )

            cleanup_session.execute(
                delete(Customer).where(
                    Customer.id == customer_id
                )
            )

            cleanup_session.commit()
