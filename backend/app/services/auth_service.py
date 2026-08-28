"""Password hashing, user authentication, and signed session tokens."""

from datetime import UTC, datetime, timedelta

import jwt
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import AuthSettings
from app.models import User

JWT_ALGORITHM = "HS256"
JWT_AUDIENCE = "parcelpulse-web"
JWT_ISSUER = "parcelpulse-api"

password_hash = PasswordHash.recommended()
_DUMMY_PASSWORD_HASH = password_hash.hash("parcelpulse-dummy-password")


class DuplicateEmailError(Exception):
    """Raised when registration conflicts with an existing email address."""


def create_user(session: Session, email: str, password: str) -> User:
    """Create an account after irreversibly hashing its password."""
    user = User(email=email, password_hash=password_hash.hash(password))
    session.add(user)

    try:
        session.commit()
        session.refresh(user)
    except IntegrityError as error:
        session.rollback()
        raise DuplicateEmailError from error

    return user


def authenticate_user(
    session: Session,
    email: str,
    password: str,
) -> User | None:
    """Return the matching user only when the password hash verifies."""
    user = session.scalar(select(User).where(User.email == email))
    encoded_hash = (
        user.password_hash if user is not None else _DUMMY_PASSWORD_HASH
    )

    try:
        password_matches = password_hash.verify(password, encoded_hash)
    except (TypeError, ValueError):
        password_matches = False

    if user is None or not password_matches:
        return None
    return user


def create_session_token(user: User, settings: AuthSettings) -> str:
    """Create a signed, expiring token containing only the account ID."""
    issued_at = datetime.now(UTC)
    return jwt.encode(
        {
            "sub": str(user.id),
            "iat": issued_at,
            "exp": issued_at + timedelta(
                minutes=settings.token_expire_minutes
            ),
            "iss": JWT_ISSUER,
            "aud": JWT_AUDIENCE,
        },
        settings.secret_key.get_secret_value(),
        algorithm=JWT_ALGORITHM,
    )


def decode_session_token(token: str, settings: AuthSettings) -> int | None:
    """Validate a session token and return its positive integer user ID."""
    try:
        payload = jwt.decode(
            token,
            settings.secret_key.get_secret_value(),
            algorithms=[JWT_ALGORITHM],
            audience=JWT_AUDIENCE,
            issuer=JWT_ISSUER,
            options={"require": ["sub", "iat", "exp", "iss", "aud"]},
        )
        user_id = int(payload["sub"])
    except (InvalidTokenError, KeyError, TypeError, ValueError):
        return None

    return user_id if user_id > 0 else None
