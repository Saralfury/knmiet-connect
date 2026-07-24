"""initial schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-06-09
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    user_role = postgresql.ENUM("student", "teacher", "hod",
                                "director", "admin", name="user_role", create_type=False)
    attendance_status = postgresql.ENUM(
        "present", "absent", "corrected", name="attendance_status",  create_type=False)
    user_role.create(op.get_bind(), checkfirst=True)
    attendance_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "departments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("code", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("code"),
    )
    op.create_index("ix_departments_code", "departments", ["code"])

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", user_role, nullable=False),
        sa.Column("is_active", sa.Boolean(),
                  nullable=False, server_default=sa.true()),
        sa.Column("failed_login_count", sa.Integer(),
                  nullable=False, server_default="0"),
        sa.Column("locked_until", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_role", "users", ["role"])

    op.create_table(
        "students",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey(
            "users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("roll_no", sa.String(50), nullable=False),
        sa.Column("phone", sa.String(30)),
        sa.Column("department_id", postgresql.UUID(as_uuid=True), sa.ForeignKey(
            "departments.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("semester", sa.Integer(), nullable=False),
        sa.Column("section", sa.String(10), nullable=False),
        sa.Column("is_active", sa.Boolean(),
                  nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id"),
        sa.UniqueConstraint("roll_no"),
    )
    op.create_index("ix_students_roll_no", "students", ["roll_no"])

    op.create_table(
        "teachers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey(
            "users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("employee_code", sa.String(50), nullable=False),
        sa.Column("department_id", postgresql.UUID(as_uuid=True), sa.ForeignKey(
            "departments.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("is_active", sa.Boolean(),
                  nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id"),
        sa.UniqueConstraint("employee_code"),
    )
    op.create_index("ix_teachers_employee_code", "teachers", ["employee_code"])

    op.create_table(
        "hod_assignments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("teacher_id", postgresql.UUID(as_uuid=True), sa.ForeignKey(
            "teachers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("department_id", postgresql.UUID(as_uuid=True), sa.ForeignKey(
            "departments.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("assigned_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("teacher_id", "department_id",
                            name="uix_hod_teacher_department"),
    )

    op.create_table(
        "courses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("course_code", sa.String(40), nullable=False),
        sa.Column("course_name", sa.String(160), nullable=False),
        sa.Column("department_id", postgresql.UUID(as_uuid=True), sa.ForeignKey(
            "departments.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("semester", sa.Integer(), nullable=False),
        sa.Column("total_lectures", sa.Integer(),
                  nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(),
                  nullable=False, server_default=sa.true()),
        sa.UniqueConstraint("course_code"),
    )
    op.create_index("ix_courses_course_code", "courses", ["course_code"])

    op.create_table(
        "teacher_course_mapping",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("teacher_id", postgresql.UUID(as_uuid=True), sa.ForeignKey(
            "teachers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("course_id", postgresql.UUID(as_uuid=True), sa.ForeignKey(
            "courses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("assigned_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("teacher_id", "course_id",
                            name="uix_teacher_course"),
    )

    op.create_table(
        "student_course_enrollment",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), sa.ForeignKey(
            "students.id", ondelete="CASCADE"), nullable=False),
        sa.Column("course_id", postgresql.UUID(as_uuid=True), sa.ForeignKey(
            "courses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("semester", sa.Integer(), nullable=False),
        sa.Column("enrolled_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("student_id", "course_id",
                            name="uix_student_course"),
    )
    op.create_index("ix_student_course_enrollment_student_id",
                    "student_course_enrollment", ["student_id"])
    op.create_index("ix_student_course_enrollment_course_id",
                    "student_course_enrollment", ["course_id"])

    op.create_table(
        "timetable",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("course_id", postgresql.UUID(as_uuid=True), sa.ForeignKey(
            "courses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("day_of_week", sa.Integer(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.Column("room", sa.String(50), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey(
            "users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("valid_from", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_timetable_course_id", "timetable", ["course_id"])

    op.create_table(
        "class_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("course_id", postgresql.UUID(as_uuid=True), sa.ForeignKey(
            "courses.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("teacher_id", postgresql.UUID(as_uuid=True), sa.ForeignKey(
            "teachers.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("totp_secret_encrypted", sa.LargeBinary(), nullable=False),
        sa.Column("start_time", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True)),
        sa.Column("is_active", sa.Boolean(),
                  nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_class_sessions_course_id",
                    "class_sessions", ["course_id"])
    op.create_index("ix_class_sessions_is_active",
                    "class_sessions", ["is_active"])
    op.create_index("ix_class_sessions_start_time",
                    "class_sessions", ["start_time"])

    op.create_table(
        "device_registrations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), sa.ForeignKey(
            "students.id", ondelete="CASCADE"), nullable=False),
        sa.Column("device_token_hash", sa.String(64), nullable=False),
        sa.Column("registered_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True)),
        sa.Column("is_active", sa.Boolean(),
                  nullable=False, server_default=sa.true()),
        sa.UniqueConstraint("student_id", name="uix_student_device"),
    )
    op.create_index("ix_device_registrations_device_token_hash",
                    "device_registrations", ["device_token_hash"])

    op.create_table(
        "attendance_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), sa.ForeignKey(
            "students.id", ondelete="CASCADE"), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey(
            "class_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("attendance_status", attendance_status,
                  nullable=False, server_default="present"),
        sa.Column("scan_timestamp", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("device_id", postgresql.UUID(as_uuid=True), sa.ForeignKey(
            "device_registrations.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("student_id", "session_id",
                            name="uix_student_session"),
    )
    op.create_index("ix_attendance_logs_student_id",
                    "attendance_logs", ["student_id"])
    op.create_index("ix_attendance_logs_session_id",
                    "attendance_logs", ["session_id"])

    op.create_table(
        "marks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), sa.ForeignKey(
            "students.id", ondelete="CASCADE"), nullable=False),
        sa.Column("course_id", postgresql.UUID(as_uuid=True), sa.ForeignKey(
            "courses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sessional1", sa.Integer(),
                  nullable=False, server_default="0"),
        sa.Column("sessional2", sa.Integer(),
                  nullable=False, server_default="0"),
        sa.Column("put_marks", sa.Integer(),
                  nullable=False, server_default="0"),
        sa.Column("total_marks", sa.Integer(),
                  nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("student_id", "course_id",
                            name="uix_student_course_marks"),
    )
    op.create_index("ix_marks_student_id", "marks", ["student_id"])
    op.create_index("ix_marks_course_id", "marks", ["course_id"])

    op.create_table(
        "refresh_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey(
            "users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("revoked", sa.Boolean(), nullable=False,
                  server_default=sa.false()),
    )
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])
    op.create_index("ix_refresh_tokens_token_hash",
                    "refresh_tokens", ["token_hash"])

    op.create_table(
        "auth_audit",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("action", sa.String(80), nullable=False),
        sa.Column("ip_address", sa.String(80)),
        sa.Column("timestamp", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_auth_audit_timestamp", "auth_audit", ["timestamp"])

    op.create_table(
        "attendance_audit",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("attendance_id", postgresql.UUID(as_uuid=True)),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True)),
        sa.Column("old_value", postgresql.JSONB()),
        sa.Column("new_value", postgresql.JSONB()),
        sa.Column("reason", sa.Text()),
        sa.Column("timestamp", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_attendance_audit_attendance_id",
                    "attendance_audit", ["attendance_id"])
    op.create_index("ix_attendance_audit_timestamp",
                    "attendance_audit", ["timestamp"])

    op.create_table(
        "marks_audit",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("marks_id", postgresql.UUID(as_uuid=True)),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True)),
        sa.Column("old_value", postgresql.JSONB()),
        sa.Column("new_value", postgresql.JSONB()),
        sa.Column("reason", sa.Text()),
        sa.Column("timestamp", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_marks_audit_marks_id", "marks_audit", ["marks_id"])
    op.create_index("ix_marks_audit_timestamp", "marks_audit", ["timestamp"])

    op.create_table(
        "timetable_audit",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("timetable_id", postgresql.UUID(as_uuid=True)),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True)),
        sa.Column("old_value", postgresql.JSONB()),
        sa.Column("new_value", postgresql.JSONB()),
        sa.Column("timestamp", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_timetable_audit_timetable_id",
                    "timetable_audit", ["timetable_id"])
    op.create_index("ix_timetable_audit_timestamp",
                    "timetable_audit", ["timestamp"])

    op.create_table(
        "security_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("event_type", sa.String(80), nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True)),
        sa.Column("severity", sa.String(20),
                  nullable=False, server_default="medium"),
        sa.Column("metadata_json", postgresql.JSONB()),
        sa.Column("timestamp", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_security_events_event_type",
                    "security_events", ["event_type"])
    op.create_index("ix_security_events_timestamp",
                    "security_events", ["timestamp"])

    op.execute("""
    CREATE OR REPLACE FUNCTION audit_attendance_changes()
    RETURNS TRIGGER AS $$
    BEGIN
        IF OLD.attendance_status IS DISTINCT FROM NEW.attendance_status THEN
            INSERT INTO attendance_audit(attendance_id, old_value, new_value)
            VALUES (
                OLD.id,
                jsonb_build_object('attendance_status', OLD.attendance_status),
                jsonb_build_object('attendance_status', NEW.attendance_status)
            );
        END IF;
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    """)
    op.execute("""
    CREATE TRIGGER trigger_attendance_audit
    AFTER UPDATE ON attendance_logs
    FOR EACH ROW EXECUTE FUNCTION audit_attendance_changes();
    """)
    op.execute("""
    CREATE OR REPLACE FUNCTION audit_marks_changes()
    RETURNS TRIGGER AS $$
    BEGIN
        INSERT INTO marks_audit(marks_id, old_value, new_value)
        VALUES (OLD.id, to_jsonb(OLD), to_jsonb(NEW));
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    """)
    op.execute("""
    CREATE TRIGGER trigger_marks_audit
    AFTER UPDATE ON marks
    FOR EACH ROW EXECUTE FUNCTION audit_marks_changes();
    """)
    op.execute("""
    CREATE OR REPLACE FUNCTION audit_timetable_changes()
    RETURNS TRIGGER AS $$
    BEGIN
        INSERT INTO timetable_audit(timetable_id, old_value, new_value)
        VALUES (OLD.id, to_jsonb(OLD), to_jsonb(NEW));
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    """)
    op.execute("""
    CREATE TRIGGER trigger_timetable_audit
    AFTER UPDATE ON timetable
    FOR EACH ROW EXECUTE FUNCTION audit_timetable_changes();
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trigger_timetable_audit ON timetable")
    op.execute("DROP FUNCTION IF EXISTS audit_timetable_changes")
    op.execute("DROP TRIGGER IF EXISTS trigger_marks_audit ON marks")
    op.execute("DROP FUNCTION IF EXISTS audit_marks_changes")
    op.execute(
        "DROP TRIGGER IF EXISTS trigger_attendance_audit ON attendance_logs")
    op.execute("DROP FUNCTION IF EXISTS audit_attendance_changes")

    for table in [
        "security_events",
        "timetable_audit",
        "marks_audit",
        "attendance_audit",
        "auth_audit",
        "refresh_tokens",
        "marks",
        "attendance_logs",
        "device_registrations",
        "class_sessions",
        "timetable",
        "student_course_enrollment",
        "teacher_course_mapping",
        "courses",
        "hod_assignments",
        "teachers",
        "students",
        "users",
        "departments",
    ]:
        op.drop_table(table)

    postgresql.ENUM(name="attendance_status").drop(
        op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="user_role").drop(op.get_bind(), checkfirst=True)
