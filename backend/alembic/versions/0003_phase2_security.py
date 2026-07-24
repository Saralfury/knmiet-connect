"""phase 2 token families and audit context

Revision ID: 0003_phase2_security
Revises: 0002_encrypt_totp_secrets
Create Date: 2026-07-06
"""

import os
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_phase2_security"
down_revision: str | None = "0002_encrypt_totp_secrets"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("refresh_tokens", sa.Column("jti", sa.String(64), nullable=True))
    op.add_column(
        "refresh_tokens",
        sa.Column("family_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "refresh_tokens",
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute("UPDATE refresh_tokens SET jti = id::text, family_id = id")
    op.alter_column("refresh_tokens", "jti", nullable=False)
    op.alter_column("refresh_tokens", "family_id", nullable=False)
    op.create_unique_constraint("uq_refresh_tokens_jti", "refresh_tokens", ["jti"])
    op.create_index("ix_refresh_tokens_family_id", "refresh_tokens", ["family_id"])

    op.add_column("timetable_audit", sa.Column("reason", sa.Text(), nullable=True))
    _replace_audit_functions()
    _protect_audit_tables()


def _replace_audit_functions() -> None:
    statements = (
        """
        CREATE OR REPLACE FUNCTION audit_attendance_changes()
        RETURNS TRIGGER AS $$
        DECLARE
            audit_actor UUID := NULLIF(current_setting('app.actor_id', true), '')::UUID;
            audit_reason TEXT := NULLIF(current_setting('app.audit_reason', true), '');
        BEGIN
            IF audit_actor IS NULL OR audit_reason IS NULL THEN
                RAISE EXCEPTION 'audit actor and reason are required';
            END IF;
            IF OLD.attendance_status IS DISTINCT FROM NEW.attendance_status THEN
                INSERT INTO attendance_audit(attendance_id, actor_id, old_value, new_value, reason)
                VALUES (
                    OLD.id,
                    audit_actor,
                    jsonb_build_object('attendance_status', OLD.attendance_status),
                    jsonb_build_object('attendance_status', NEW.attendance_status),
                    audit_reason
                );
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """,
        """
        CREATE OR REPLACE FUNCTION audit_marks_changes()
        RETURNS TRIGGER AS $$
        DECLARE
            audit_actor UUID := NULLIF(current_setting('app.actor_id', true), '')::UUID;
            audit_reason TEXT := NULLIF(current_setting('app.audit_reason', true), '');
        BEGIN
            IF audit_actor IS NULL OR audit_reason IS NULL THEN
                RAISE EXCEPTION 'audit actor and reason are required';
            END IF;
            INSERT INTO marks_audit(marks_id, actor_id, old_value, new_value, reason)
            VALUES (OLD.id, audit_actor, to_jsonb(OLD), to_jsonb(NEW), audit_reason);
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """,
        """
        CREATE OR REPLACE FUNCTION audit_timetable_changes()
        RETURNS TRIGGER AS $$
        DECLARE
            audit_actor UUID := NULLIF(current_setting('app.actor_id', true), '')::UUID;
            audit_reason TEXT := NULLIF(current_setting('app.audit_reason', true), '');
        BEGIN
            IF audit_actor IS NULL OR audit_reason IS NULL THEN
                RAISE EXCEPTION 'audit actor and reason are required';
            END IF;
            INSERT INTO timetable_audit(timetable_id, actor_id, old_value, new_value, reason)
            VALUES (OLD.id, audit_actor, to_jsonb(OLD), to_jsonb(NEW), audit_reason);
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """,
    )
    for statement in statements:
        op.execute(statement)


def _protect_audit_tables() -> None:
    app_role = os.environ.get("APP_DB_ROLE")
    if not app_role:
        return
    connection = op.get_bind()
    quoted_role = connection.dialect.identifier_preparer.quote(app_role)
    role_exists = connection.scalar(
        sa.text("SELECT 1 FROM pg_roles WHERE rolname = :role_name"),
        {"role_name": app_role},
    )
    if not role_exists:
        password = os.environ.get("APP_DB_PASSWORD")
        if not password:
            raise RuntimeError("APP_DB_PASSWORD is required when creating APP_DB_ROLE")
        quoted_password = sa.String().literal_processor(connection.dialect)(password)
        op.execute(f"CREATE ROLE {quoted_role} LOGIN PASSWORD {quoted_password}")
    op.execute(f"GRANT USAGE ON SCHEMA public TO {quoted_role}")
    op.execute(
        f"GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO {quoted_role}"
    )
    op.execute(f"GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO {quoted_role}")
    op.execute(
        f"ALTER DEFAULT PRIVILEGES IN SCHEMA public "
        f"GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {quoted_role}"
    )
    op.execute(
        f"ALTER DEFAULT PRIVILEGES IN SCHEMA public "
        f"GRANT USAGE, SELECT ON SEQUENCES TO {quoted_role}"
    )
    op.execute(
        f"GRANT SELECT, INSERT ON attendance_audit, marks_audit, timetable_audit, auth_audit TO {quoted_role}"
    )
    op.execute(
        f"REVOKE UPDATE, DELETE ON attendance_audit, marks_audit, timetable_audit, auth_audit FROM {quoted_role}"
    )


def downgrade() -> None:
    _restore_legacy_audit_functions()
    op.drop_column("timetable_audit", "reason")
    op.drop_index("ix_refresh_tokens_family_id", table_name="refresh_tokens")
    op.drop_constraint("uq_refresh_tokens_jti", "refresh_tokens", type_="unique")
    op.drop_column("refresh_tokens", "revoked_at")
    op.drop_column("refresh_tokens", "family_id")
    op.drop_column("refresh_tokens", "jti")


def _restore_legacy_audit_functions() -> None:
    statements = (
        """
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
        """,
        """
        CREATE OR REPLACE FUNCTION audit_marks_changes()
        RETURNS TRIGGER AS $$
        BEGIN
            INSERT INTO marks_audit(marks_id, old_value, new_value)
            VALUES (OLD.id, to_jsonb(OLD), to_jsonb(NEW));
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """,
        """
        CREATE OR REPLACE FUNCTION audit_timetable_changes()
        RETURNS TRIGGER AS $$
        BEGIN
            INSERT INTO timetable_audit(timetable_id, old_value, new_value)
            VALUES (OLD.id, to_jsonb(OLD), to_jsonb(NEW));
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """,
    )
    for statement in statements:
        op.execute(statement)
