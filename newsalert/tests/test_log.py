import json
import logging

from newsalert.log import JsonFormatter


def test_secrets_from_env_are_redacted(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-verysecret-123456")
    monkeypatch.setenv("NTFY_TOKEN", "tk_abcdef123456")
    fmt = JsonFormatter()
    record = logging.LogRecord("t", logging.ERROR, __file__, 1, "failed with key sk-ant-verysecret-123456", None, None)
    record.header = "Bearer tk_abcdef123456"
    line = fmt.format(record)
    assert "verysecret" not in line and "tk_abcdef" not in line
    payload = json.loads(line)
    assert payload["event"] == "failed with key ***"
    assert payload["header"] == "Bearer ***"
