import re


def normalize_email(email: str) -> str:
    return (email or "").strip().lower()


def password_is_strong(password: str) -> bool:
    if not password or len(password) < 10:
        return False
    checks = [
        re.search(r"[A-Z]", password),
        re.search(r"[a-z]", password),
        re.search(r"\d", password),
        re.search(r"[^A-Za-z0-9]", password),
    ]
    return all(checks)
