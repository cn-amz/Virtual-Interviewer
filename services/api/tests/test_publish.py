from app.publish import LocalOnlyProvider, ReservedProvider


def test_local_provider_returns_localhost_url():
    endpoint = LocalOnlyProvider().expose(5173, "http", "frontend")

    assert endpoint.url == "http://localhost:5173"
    assert endpoint.provider == "local"


def test_reserved_provider_documents_next_step():
    endpoint = ReservedProvider("frp").expose(8000, "https", "api")

    assert endpoint.url == ""
    assert endpoint.provider == "frp"
    assert "Forward local port 8000" in endpoint.notes[1]
