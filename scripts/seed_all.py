from app.db.session import SessionLocal

from scripts.seed_customers import seed_customers

from scripts.seed_pawn_contracts_with_assets import (
    seed_pawn_contracts_with_assets,
)

def seed_all() -> None:
    db = SessionLocal()

    try:
        seed_customers(db)
        seed_pawn_contracts_with_assets(db)

        print("Seed all data successfully.")

    finally:
        db.close()

if __name__ == "__main__":
    seed_all()
