from unittest.mock import MagicMock

from app.main import app
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError


def test_metrics_api_reads_postgres_and_reports_missing_runs():
    with TestClient(app) as client:
        database = MagicMock()
        app.state.database = database
        connection = database.connect.return_value.__enter__.return_value
        connection.execute.return_value.mappings.return_value = [
            {"run_id": "test", "status": "completed", "metadata": {"best_macro_f1": 0.1}}
        ]
        assert client.get("/training/runs").json()[0]["run_id"] == "test"
        assert client.get("/training/runs/test").json()["status"] == "completed"
        assert client.get("/training/runs?limit=1000").status_code == 422
        connection.execute.return_value.mappings.return_value = []
        assert client.get("/training/runs/missing").status_code == 404
        database.connect.side_effect = OperationalError("test", {}, Exception("test-only outage"))
        assert client.get("/training/runs").status_code == 503
