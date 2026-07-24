import argparse
import asyncio
import getpass

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import AsyncSessionLocal
from app.models.users import User, UserRole


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create the first KNMIET administrator")
    parser.add_argument("--email", required=True)
    parser.add_argument("--name", required=True)
    return parser.parse_args()


async def bootstrap(email: str, name: str, password: str) -> None:
    if (
        len(password) < 14
        or not any(char.islower() for char in password)
        or not any(char.isupper() for char in password)
        or not any(char.isdigit() for char in password)
    ):
        raise SystemExit("Password must be 14+ characters with upper, lower, and numeric characters")

    async with AsyncSessionLocal() as db:
        existing_admin = await db.scalar(select(User.id).where(User.role == UserRole.admin).limit(1))
        if existing_admin:
            raise SystemExit("Bootstrap refused: an administrator already exists")
        db.add(
            User(
                email=email.lower(),
                name=name,
                password_hash=await hash_password(password),
                role=UserRole.admin,
            )
        )
        await db.commit()


if __name__ == "__main__":
    arguments = parse_args()
    entered_password = getpass.getpass("Admin password: ")
    asyncio.run(bootstrap(arguments.email, arguments.name, entered_password))
    print("Initial administrator created")
