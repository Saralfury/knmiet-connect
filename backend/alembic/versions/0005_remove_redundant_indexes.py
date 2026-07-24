"""remove indexes duplicated by unique constraints

Revision ID: 0005_remove_redundant_indexes
Revises: 0004_domain_constraints
Create Date: 2026-07-06
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0005_remove_redundant_indexes"
down_revision: str | None = "0004_domain_constraints"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


REDUNDANT_INDEXES = (
    ("users", "ix_users_email", ["email"]),
    ("students", "ix_students_roll_no", ["roll_no"]),
    ("courses", "ix_courses_course_code", ["course_code"]),
    ("departments", "ix_departments_code", ["code"]),
    ("teachers", "ix_teachers_employee_code", ["employee_code"]),
)


def upgrade() -> None:
    for table, name, _ in REDUNDANT_INDEXES:
        op.drop_index(name, table_name=table)


def downgrade() -> None:
    for table, name, columns in REDUNDANT_INDEXES:
        op.create_index(name, table, columns, unique=False)
