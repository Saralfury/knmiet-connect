import asyncio
import os

import asyncpg
from alembic import command
from alembic.config import Config
from sqlalchemy.engine import make_url


TEST_DATABASE = "knmiet_migration_test"


def owner_url():
    return make_url(os.environ["MIGRATION_DATABASE_URL"])


def asyncpg_dsn(database: str) -> str:
    return owner_url().set(drivername="postgresql", database=database).render_as_string(hide_password=False)


async def recreate_database() -> None:
    connection = await asyncpg.connect(asyncpg_dsn("postgres"))
    try:
        await connection.execute(f'DROP DATABASE IF EXISTS "{TEST_DATABASE}" WITH (FORCE)')
        await connection.execute(f'CREATE DATABASE "{TEST_DATABASE}"')
    finally:
        await connection.close()


async def drop_database() -> None:
    connection = await asyncpg.connect(asyncpg_dsn("postgres"))
    try:
        await connection.execute(f'DROP DATABASE IF EXISTS "{TEST_DATABASE}" WITH (FORCE)')
    finally:
        await connection.close()


def run_migrations() -> None:
    test_url = owner_url().set(database=TEST_DATABASE).render_as_string(hide_password=False)
    os.environ["DATABASE_URL"] = test_url
    os.environ["MIGRATION_DATABASE_URL"] = test_url
    config = Config("alembic.ini")
    command.upgrade(config, "head")
    command.downgrade(config, "base")
    command.upgrade(config, "head")
    command.downgrade(config, "base")


if __name__ == "__main__":
    asyncio.run(recreate_database())
    try:
        run_migrations()
    finally:
        asyncio.run(drop_database())
    print("migration-roundtrip-ok")
