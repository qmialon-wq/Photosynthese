from contextlib import contextmanager
from typing import Any

from shared.training_metrics import connect

REVIEW_LOCK = 641728103


def jsonb(value: Any) -> Any:
    from psycopg.types.json import Jsonb

    return Jsonb(value)


class ReviewError(Exception):
    def __init__(self, message: str, status: int = 409) -> None:
        self.status = status
        super().__init__(message)


@contextmanager
def transaction(write: bool = False) -> Any:
    from psycopg.rows import dict_row

    with connect() as connection:
        connection.row_factory = dict_row
        if write:
            connection.execute("SELECT pg_advisory_xact_lock(%s)", (REVIEW_LOCK,))
        yield connection
