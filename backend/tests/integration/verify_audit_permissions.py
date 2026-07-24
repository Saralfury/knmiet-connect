import asyncio
import os

import asyncpg


AUDIT_TABLES = (
    "attendance_audit",
    "marks_audit",
    "timetable_audit",
    "auth_audit",
)


def asyncpg_url() -> str:
    value = os.environ["DATABASE_URL"]
    return value.replace("postgresql+asyncpg://", "postgresql://", 1)


async def expect_denied(connection: asyncpg.Connection, statement: str) -> None:
    try:
        await connection.execute(statement)
    except asyncpg.InsufficientPrivilegeError:
        return
    raise AssertionError(f"Database unexpectedly allowed: {statement}")


async def verify() -> None:
    connection = await asyncpg.connect(asyncpg_url())
    try:
        current_user = await connection.fetchval("SELECT current_user")
        expected_user = os.environ.get("APP_DB_ROLE", "knmiet_app")
        if current_user != expected_user:
            raise AssertionError(f"Expected role {expected_user}, connected as {current_user}")
        for table in AUDIT_TABLES:
            await expect_denied(
                connection,
                f"UPDATE {table} SET timestamp = timestamp WHERE false",
            )
            await expect_denied(connection, f"DELETE FROM {table} WHERE false")
    finally:
        await connection.close()


if __name__ == "__main__":
    asyncio.run(verify())
    print("audit-role-permissions-ok")
