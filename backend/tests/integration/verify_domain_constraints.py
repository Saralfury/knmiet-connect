import asyncio
import os

import asyncpg


EXPECTED_CONSTRAINTS = {
    "ck_students_semester",
    "ck_courses_semester",
    "ck_courses_total_lectures",
    "ck_enrollment_semester",
    "ck_timetable_day",
    "ck_timetable_time_order",
    "ck_marks_sessional1",
    "ck_marks_sessional2",
    "ck_marks_put",
    "ck_marks_total",
}


async def verify() -> None:
    dsn = os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://", 1)
    connection = await asyncpg.connect(dsn)
    try:
        names = set(
            await connection.fetch(
                "SELECT conname FROM pg_constraint WHERE contype = 'c' AND conname = ANY($1::text[])",
                list(EXPECTED_CONSTRAINTS),
            )
        )
        actual = {record["conname"] for record in names}
        if actual != EXPECTED_CONSTRAINTS:
            raise AssertionError(f"Missing CHECK constraints: {sorted(EXPECTED_CONSTRAINTS - actual)}")
    finally:
        await connection.close()


if __name__ == "__main__":
    asyncio.run(verify())
    print("domain-constraints-ok")
