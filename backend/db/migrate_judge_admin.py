from sqlalchemy import Engine, inspect, text

from db.session import engine
from db.tables_phase1 import Base
import db.tables_phase2  # noqa: F401


def migrate_judge_schema(database_engine: Engine) -> None:
    Base.metadata.create_all(bind=database_engine)

    with database_engine.begin() as connection:
        problem_columns = {
            column["name"]
            for column in inspect(connection).get_columns("problem")
        }
        if "data_constraints" not in problem_columns:
            connection.execute(
                text("ALTER TABLE problem ADD COLUMN data_constraints TEXT")
            )

        submission_columns = {
            column["name"]
            for column in inspect(connection).get_columns("submission")
        }
        if "contest_id" not in submission_columns:
            connection.execute(
                text(
                    "ALTER TABLE submission "
                    "ADD COLUMN contest_id INTEGER "
                    "REFERENCES contest(contest_id) ON DELETE SET NULL"
                )
            )
        if "source_code" not in submission_columns:
            connection.execute(
                text("ALTER TABLE submission ADD COLUMN source_code TEXT")
            )

        for table_name, column_name in (
            ("problem", "created_by"),
            ("contest", "created_by"),
            ("submission", "account_id"),
        ):
            columns = {
                column["name"]: column
                for column in inspect(connection).get_columns(table_name)
            }
            if not columns[column_name]["nullable"]:
                connection.execute(
                    text(
                        f"ALTER TABLE {table_name} "
                        f"ALTER COLUMN {column_name} DROP NOT NULL"
                    )
                )


if __name__ == "__main__":
    migrate_judge_schema(engine)
    print("Judge-admin tables, class requests, and submission fields are ready.")
