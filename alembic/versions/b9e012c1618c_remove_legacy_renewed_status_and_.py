"""remove legacy renewed status and previous contract

Revision ID: b9e012c1618c
Revises: ad32f2959dbc
Create Date: 2026-11-03 08:39:29.664759

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b9e012c1618c'
down_revision: Union[str, Sequence[str], None] = 'ad32f2959dbc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Refuse migration if legacy data still exists.
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM pawn_contracts
                WHERE status::text = 'RENEWED'
                   OR previous_contract_id IS NOT NULL
            ) THEN
                RAISE EXCEPTION
                    'Cannot remove legacy renewal schema: '
                    'renewal data still exists';
            END IF;
        END
        $$;
        """
    )

    # 2. Remove the legacy foreign key.
    op.drop_constraint(
        "fk_pawn_contracts_previous_contract_id",
        "pawn_contracts",
        type_="foreignkey",
    )

    # 3. Remove the legacy column.
    op.drop_column(
        "pawn_contracts",
        "previous_contract_id",
    )

    # 4. Rename the existing enum.
    op.execute(
        """
        ALTER TYPE contract_status
        RENAME TO contract_status_old;
        """
    )

    # 5. Create the replacement enum.
    op.execute(
        """
        CREATE TYPE contract_status AS ENUM (
            'ACTIVE',
            'REDEEMED',
            'OVERDUE',
            'LIQUIDATED'
        );
        """
    )

    # 6. Convert the status column to the new enum.
    op.execute(
        """
        ALTER TABLE pawn_contracts
        ALTER COLUMN status
        TYPE contract_status
        USING status::text::contract_status;
        """
    )

    # 7. Remove the old enum.
    op.execute(
        """
        DROP TYPE contract_status_old;
        """
    )

def downgrade() -> None:
    # 1. Rename the current enum.
    op.execute(
        """
        ALTER TYPE contract_status
        RENAME TO contract_status_old;
        """
    )

    # 2. Recreate the legacy enum.
    op.execute(
        """
        CREATE TYPE contract_status AS ENUM (
            'ACTIVE',
            'REDEEMED',
            'OVERDUE',
            'LIQUIDATED',
            'RENEWED'
        );
        """
    )

    # 3. Convert the status column back.
    op.execute(
        """
        ALTER TABLE pawn_contracts
        ALTER COLUMN status
        TYPE contract_status
        USING status::text::contract_status;
        """
    )

    # 4. Remove the temporary enum.
    op.execute(
        """
        DROP TYPE contract_status_old;
        """
    )

    # 5. Restore the legacy column.
    op.add_column(
        "pawn_contracts",
        sa.Column(
            "previous_contract_id",
            sa.Integer(),
            nullable=True,
        ),
    )

    # 6. Restore the foreign key.
    op.create_foreign_key(
        "fk_pawn_contracts_previous_contract_id",
        "pawn_contracts",
        "pawn_contracts",
        ["previous_contract_id"],
        ["id"],
    )
