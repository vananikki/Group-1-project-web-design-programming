from sqlalchemy import create_engine, inspect, text

from db.migrate_judge_admin import migrate_judge_schema


def test_migration_adds_contest_link_to_existing_submission_table():
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE contest ("
                "contest_id INTEGER PRIMARY KEY, created_by INTEGER)"
            )
        )
        connection.execute(
            text(
                "CREATE TABLE submission ("
                "submission_id INTEGER PRIMARY KEY, account_id INTEGER)"
            )
        )

    migrate_judge_schema(engine)
    migrate_judge_schema(engine)

    submission_columns = {
        column["name"] for column in inspect(engine).get_columns("submission")
    }
    assert "contest_id" in submission_columns
    assert "source_code" in submission_columns
    assert inspect(engine).has_table("class_join_request")
    assert "data_constraints" in {
        column["name"] for column in inspect(engine).get_columns("problem")
    }

    foreign_keys = inspect(engine).get_foreign_keys("submission")
    assert any(foreign_key["referred_table"] == "contest" for foreign_key in foreign_keys)


def test_migration_adds_data_constraints_to_existing_problem_table():
    engine = create_engine("sqlite://")
    migrate_judge_schema(engine)
    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE problem DROP COLUMN data_constraints"))

    migrate_judge_schema(engine)

    problem_columns = {
        column["name"] for column in inspect(engine).get_columns("problem")
    }
    assert "data_constraints" in problem_columns
