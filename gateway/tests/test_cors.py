from fastapi.testclient import TestClient


def test_loopback_flutter_web_origin_allowed(client: TestClient) -> None:
    response = client.options(
        "/v1/health",
        headers={
            "Origin": "http://localhost:53711",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:53711"
