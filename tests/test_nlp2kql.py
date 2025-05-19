import pytest
from app.nlp2kql import nl_to_kql

def test_nl_to_kql(monkeypatch):
    def mock_get_kql_from_nl(nl, context=None):
        return "StormEvents | count"
    monkeypatch.setattr("app.azure_openai_client.get_kql_from_nl", mock_get_kql_from_nl)
    kql = nl_to_kql("Count all storm events")
    assert kql == "StormEvents | count" 