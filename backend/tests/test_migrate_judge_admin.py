from sqlalchemy import create_engine, inspect, text

from db.migrate_judge_admin import migrate_judge_schema


def test_migration_adds_contest_link_to_existing_submission_table():
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(
            text("CREATE TABLE contest (contest_id INTEGER PRIMARY KEY)")
        )
        connection.execute(
            text("CREATE TABLE submission (submission_id INTEGER PRIMARY KEY)")
        )

    migrate_judge_schema(engine)
    migrate_judge_schema(engine)

    submission_columns = {
        column["name"] for column in inspect(engine).get_columns("submission")
    }
    assert "contest_id" in submission_columns
    assert "source_code" in submission_columns
    assert inspect(engine).has_table("class_join_request")

    foreign_keys = inspect(engine).get_foreign_keys("submission")
    assert any(foreign_key["referred_table"] == "contest" for foreign_key in foreign_keys)
