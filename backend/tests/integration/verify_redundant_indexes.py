import asyncio
import os

import asyncpg


CANDIDATES = {
    "ix_users_email": (
        "SELECT id FROM users WHERE email = 'index-check@example.com'",
        "users_email_key",
    ),
    "ix_students_roll_no": (
        "SELECT id FROM students WHERE roll_no = 'INDEX-CHECK'",
        "students_roll_no_key",
    ),
    "ix_courses_course_code": (
        "SELECT id FROM courses WHERE course_code = 'INDEX-CHECK'",
        "courses_course_code_key",
    ),
    "ix_departments_code": (
        "SELECT id FROM departments WHERE code = 'INDEX-CHECK'",
        "departments_code_key",
    ),
    "ix_teachers_employee_code": (
        "SELECT id FROM teachers WHERE employee_code = 'INDEX-CHECK'",
        "teachers_employee_code_key",
    ),
}


async def explain(connection: asyncpg.Connection, query: str) -> str:
    rows = await connection.fetch(f"EXPLAIN (COSTS OFF) {query}")
    return "\n".join(record[0] for record in rows)


async def verify() -> None:
    dsn = os.environ["MIGRATION_DATABASE_URL"].replace(
        "postgresql+asyncpg://",
        "postgresql://",
        1,
    )
    connection = await asyncpg.connect(dsn)
    transaction = connection.transaction()
    await transaction.start()
    try:
        await connection.execute("SET LOCAL enable_seqscan = off")
        existing = {
            record["indexname"]
            for record in await connection.fetch(
                "SELECT indexname FROM pg_indexes WHERE schemaname = 'public'"
            )
        }
        present_candidates = set(CANDIDATES) & existing
        before = {
            index: await explain(connection, query)
            for index, (query, _) in CANDIDATES.items()
            if index in present_candidates
        }
        for index in present_candidates:
            await connection.execute(f'DROP INDEX "{index}"')
        after = {
            index: await explain(connection, query)
            for index, (query, _) in CANDIDATES.items()
        }
        device_plan = await explain(
            connection,
            "SELECT id FROM device_registrations "
            "WHERE student_id = '00000000-0000-0000-0000-000000000000' "
            "AND is_active IS true",
        )
        for index, (_, replacement) in CANDIDATES.items():
            if replacement not in after[index]:
                raise AssertionError(
                    f"{index} cannot be removed; replacement plan was:\n{after[index]}"
                )
        if "uix_student_device" not in device_plan:
            raise AssertionError(f"Device lookup did not use unique index:\n{device_plan}")
        for index in CANDIDATES:
            if index in before:
                print(f"{index}: before={before[index]!r}; after={after[index]!r}")
            else:
                print(f"{index}: removed; replacement={after[index]!r}")
        print(f"device_student_id: kept uix_student_device; plan={device_plan!r}")
    finally:
        await transaction.rollback()
        await connection.close()


if __name__ == "__main__":
    asyncio.run(verify())
    print("redundant-index-analysis-ok")
