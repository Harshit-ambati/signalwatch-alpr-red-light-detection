"""Password gate for the single-reviewer research deployment."""
import hmac
import os


def configured_password(secrets):
    password = os.environ.get('SIGNALWATCH_PASSWORD')
    if password:
        return password
    try:
        return secrets.get('APP_PASSWORD', '')
    except FileNotFoundError:
        return ''


def password_matches(candidate, expected):
    return bool(expected) and hmac.compare_digest(candidate, expected)
