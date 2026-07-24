"""encrypt existing TOTP secrets with Fernet

Revision ID: 0002_encrypt_totp_secrets
Revises: 0001_initial_schema
Create Date: 2026-07-06
"""

import base64
import os
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from cryptography.fernet import Fernet, InvalidToken

revision: str = "0002_encrypt_totp_secrets"
down_revision: str | None = "0001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _cipher() -> Fernet:
    key = os.environ.get("TOTP_ENCRYPTION_KEY")
    if not key:
        raise RuntimeError("TOTP_ENCRYPTION_KEY is required to migrate class-session secrets")
    try:
        return Fernet(key.encode("ascii"))
    except (TypeError, ValueError) as exc:
        raise RuntimeError("TOTP_ENCRYPTION_KEY must be a valid Fernet key") from exc


def upgrade() -> None:
    connection = op.get_bind()
    cipher = _cipher()
    rows = connection.execute(
        sa.text("SELECT id, totp_secret_encrypted FROM class_sessions")
    ).mappings()
    for row in rows:
        encoded = bytes(row["totp_secret_encrypted"])
        try:
            cipher.decrypt(encoded)
            continue
        except InvalidToken:
            pass
        try:
            plaintext = base64.b64decode(encoded, validate=True)
        except ValueError as exc:
            raise RuntimeError(f"Class session {row['id']} has an unknown secret format") from exc
        connection.execute(
            sa.text(
                "UPDATE class_sessions "
                "SET totp_secret_encrypted = :secret WHERE id = :session_id"
            ),
            {"secret": cipher.encrypt(plaintext), "session_id": row["id"]},
        )


def downgrade() -> None:
    connection = op.get_bind()
    cipher = _cipher()
    rows = connection.execute(
        sa.text("SELECT id, totp_secret_encrypted FROM class_sessions")
    ).mappings()
    for row in rows:
        encrypted = bytes(row["totp_secret_encrypted"])
        try:
            plaintext = cipher.decrypt(encrypted)
        except InvalidToken as exc:
            raise RuntimeError(f"Class session {row['id']} cannot be decrypted") from exc
        connection.execute(
            sa.text(
                "UPDATE class_sessions "
                "SET totp_secret_encrypted = :secret WHERE id = :session_id"
            ),
            {"secret": base64.b64encode(plaintext), "session_id": row["id"]},
        )
