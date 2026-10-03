import json
import sqlite3
from contextlib import closing
from pathlib import Path

from id_utils import canonical_id


class SQLiteProfileStore:
    def __init__(self, database_path: str | Path):
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.database_path)) as connection:
            with connection:
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS candidate_profiles (
                        candidate_id TEXT PRIMARY KEY,
                        profile_json TEXT NOT NULL
                    )
                    """
                )

    def save(self, candidate_key: str, profile: dict) -> dict:
        candidate_id = canonical_id(candidate_key)
        stored_profile = {**profile, "candidate_id": candidate_id}
        profile_json = json.dumps(stored_profile, ensure_ascii=False)
        with closing(sqlite3.connect(self.database_path)) as connection:
            with connection:
                connection.execute(
                    """
                    INSERT INTO candidate_profiles (candidate_id, profile_json)
                    VALUES (?, ?)
                    ON CONFLICT(candidate_id) DO UPDATE SET
                        profile_json = excluded.profile_json
                    """,
                    (candidate_id, profile_json),
                )
        return stored_profile

    def get(self, candidate_key: str) -> dict | None:
        candidate_id = canonical_id(candidate_key)
        with closing(sqlite3.connect(self.database_path)) as connection:
            row = connection.execute(
                "SELECT profile_json FROM candidate_profiles WHERE candidate_id = ?",
                (candidate_id,),
            ).fetchone()
        if row is None:
            return None
        return json.loads(row[0])
