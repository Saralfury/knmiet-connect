"""add academic domain check constraints

Revision ID: 0004_domain_constraints
Revises: 0003_phase2_security
Create Date: 2026-07-06
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0004_domain_constraints"
down_revision: str | None = "0003_phase2_security"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


CONSTRAINTS = (
    ("students", "ck_students_semester", "semester BETWEEN 1 AND 8"),
    ("courses", "ck_courses_semester", "semester BETWEEN 1 AND 8"),
    ("courses", "ck_courses_total_lectures", "total_lectures >= 0"),
    ("student_course_enrollment", "ck_enrollment_semester", "semester BETWEEN 1 AND 8"),
    ("timetable", "ck_timetable_day", "day_of_week BETWEEN 0 AND 6"),
    ("timetable", "ck_timetable_time_order", "start_time < end_time"),
    ("marks", "ck_marks_sessional1", "sessional1 BETWEEN 0 AND 100"),
    ("marks", "ck_marks_sessional2", "sessional2 BETWEEN 0 AND 100"),
    ("marks", "ck_marks_put", "put_marks BETWEEN 0 AND 100"),
    ("marks", "ck_marks_total", "total_marks BETWEEN 0 AND 300"),
)


def upgrade() -> None:
    for table, name, expression in CONSTRAINTS:
        op.create_check_constraint(name, table, expression)


def downgrade() -> None:
    for table, name, _ in reversed(CONSTRAINTS):
        op.drop_constraint(name, table, type_="check")
