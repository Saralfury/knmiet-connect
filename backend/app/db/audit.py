from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def set_audit_context(db: AsyncSession, actor_id: UUID, reason: str) -> None:
    normalized_reason = reason.strip()
    if not normalized_reason:
        raise ValueError("Audit reason is required")
    await db.execute(
        text(
            "SELECT "
            "set_config('app.actor_id', :actor_id, true), "
            "set_config('app.audit_reason', :reason, true)"
        ),
        {"actor_id": str(actor_id), "reason": normalized_reason},
    )
