"""Tests for account authentication and shipment authorization."""

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.models import Shipment, User

PASSWORD = "Correct-Horse-42!"
UPS_TRACKING_NUMBER = "1Z999AA10123456784"


def register(
    client: TestClient,
    email: str,
    password: str = PASSWORD,
):
    """Register through the public API."""
    return client.post(
        "/api/auth/register",
        json={"email": email, "password": password},
    )


def login(
    client: TestClient,
    email: str,
    password: str = PASSWORD,
):
    """Log in through the public API."""
    return client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
    )


def track_ups(client: TestClient):
    """Create the deterministic UPS shipment for the current user."""
    return client.post(
        "/api/tracking",
        json={"tracking_number": UPS_TRACKING_NUMBER},
    )


def test_registration_normalizes_email_and_hashes_password(
    auth_client: TestClient,
    isolated_database: sessionmaker[Session],
) -> None:
    response = register(auth_client, "  Owner@Example.COM ")

    assert response.status_code == 201
    assert response.json()["email"] == "owner@example.com"
    assert "password" not in response.json()
    assert "password_hash" not in response.json()
    set_cookie = response.headers["set-cookie"].lower()
    assert "httponly" in set_cookie
    assert "samesite=lax" in set_cookie

    with isolated_database() as session:
        user = session.scalar(
            select(User).where(User.email == "owner@example.com")
        )

    assert user is not None
    assert user.password_hash != PASSWORD
    assert user.password_hash.startswith("$argon2")


def test_duplicate_email_is_rejected_after_normalization(
    auth_client: TestClient,
) -> None:
    assert register(auth_client, "owner@example.com").status_code == 201

    response = register(auth_client, "OWNER@EXAMPLE.COM")

    assert response.status_code == 409
    assert response.json() == {
        "detail": "An account with that email already exists"
    }


def test_login_success_and_failure(auth_client: TestClient) -> None:
    register(auth_client, "owner@example.com")
    auth_client.cookies.clear()

    failed = login(auth_client, "owner@example.com", "Incorrect-Password!")
    assert failed.status_code == 401
    assert failed.json() == {"detail": "Invalid email or password"}

    succeeded = login(auth_client, " OWNER@EXAMPLE.COM ")
    assert succeeded.status_code == 200
    assert succeeded.json()["email"] == "owner@example.com"
    assert "parcelpulse_session" in auth_client.cookies


def test_authenticated_me_and_logout(auth_client: TestClient) -> None:
    registered = register(auth_client, "owner@example.com")

    me = auth_client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json() == registered.json()

    logout = auth_client.post("/api/auth/logout")
    assert logout.status_code == 204
    assert logout.content == b""
    assert auth_client.get("/api/auth/me").status_code == 401


def test_shipment_endpoints_require_authentication(
    auth_client: TestClient,
) -> None:
    assert auth_client.get("/api/shipments").status_code == 401
    assert auth_client.get("/api/shipments/1").status_code == 401
    assert auth_client.post("/api/shipments/1/refresh").status_code == 401
    assert auth_client.delete("/api/shipments/1").status_code == 401
    assert track_ups(auth_client).status_code == 401


def test_users_only_see_and_refresh_their_own_shipments(
    auth_client: TestClient,
    isolated_database: sessionmaker[Session],
) -> None:
    first_user = register(auth_client, "first@example.com").json()
    first_lookup = track_ups(auth_client)
    assert first_lookup.status_code == 200
    first_shipment = auth_client.get("/api/shipments").json()[0]

    auth_client.post("/api/auth/logout")
    second_user = register(auth_client, "second@example.com").json()
    assert auth_client.get("/api/shipments").json() == []

    second_lookup = track_ups(auth_client)
    assert second_lookup.status_code == 200
    second_shipment = auth_client.get("/api/shipments").json()[0]
    assert second_shipment["id"] != first_shipment["id"]

    assert auth_client.get(
        f"/api/shipments/{first_shipment['id']}"
    ).status_code == 404
    assert auth_client.delete(
        f"/api/shipments/{first_shipment['id']}"
    ).status_code == 404
    assert auth_client.post(
        f"/api/shipments/{first_shipment['id']}/refresh"
    ).status_code == 404

    refreshed = auth_client.post(
        f"/api/shipments/{second_shipment['id']}/refresh"
    )
    assert refreshed.status_code == 200
    assert refreshed.json()["id"] == second_shipment["id"]
    assert len(refreshed.json()["tracking_events"]) == 4

    with isolated_database() as session:
        saved_shipments = session.scalars(
            select(Shipment).order_by(Shipment.id)
        ).all()

    assert [shipment.user_id for shipment in saved_shipments] == [
        first_user["id"],
        second_user["id"],
    ]
    assert [shipment.tracking_number for shipment in saved_shipments] == [
        UPS_TRACKING_NUMBER,
        UPS_TRACKING_NUMBER,
    ]


def test_user_cannot_open_or_delete_another_users_shipment(
    auth_client: TestClient,
) -> None:
    register(auth_client, "first@example.com")
    track_ups(auth_client)
    first_shipment_id = auth_client.get("/api/shipments").json()[0]["id"]

    auth_client.post("/api/auth/logout")
    register(auth_client, "second@example.com")

    detail = auth_client.get(f"/api/shipments/{first_shipment_id}")
    refresh = auth_client.post(
        f"/api/shipments/{first_shipment_id}/refresh"
    )
    deletion = auth_client.delete(f"/api/shipments/{first_shipment_id}")

    assert detail.status_code == 404
    assert refresh.status_code == 404
    assert deletion.status_code == 404
