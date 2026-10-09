import json
import logging

from app.core.logging import JSONFormatter, request_id_context


def test_structured_log_with_request_id() -> None:
    token = request_id_context.set("request-123")
    try:
        record = logging.LogRecord("devassist", logging.INFO, "", 0, "request_completed", (), None)
        data = json.loads(JSONFormatter().format(record))
        assert data["request_id"] == "request-123"
        assert data["level"] == "INFO"
        assert data["message"] == "request_completed"
    finally:
        request_id_context.reset(token)


def test_exception_details_are_not_logged() -> None:
    error = ValueError("secret-token")
    record = logging.LogRecord(
        "devassist", logging.ERROR, "", 0, "operation_failed", (), (ValueError, error, None)
    )
    output = JSONFormatter().format(record)
    assert "secret-token" not in output
    assert json.loads(output)["exception_type"] == "ValueError"
