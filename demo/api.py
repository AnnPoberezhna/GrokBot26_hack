"""HTTP-facing handlers of the demo app."""

from demo.auth import issue, verify


def login(user_id: str) -> dict[str, str]:
    return {"token": issue(user_id)}


def me(token: str) -> dict[str, bool]:
    return {"valid": verify(token)}
