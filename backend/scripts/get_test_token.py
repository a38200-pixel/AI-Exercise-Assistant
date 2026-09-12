"""Sign in a manually-created Supabase test user and print an access token."""

from __future__ import annotations

import argparse
from getpass import getpass
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.core.config import get_settings
from backend.app.core.supabase_client import create_supabase_client


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--email", help="Test user's email (prompted when omitted)")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    email = (args.email or input("Email: ")).strip()
    password = getpass("Password (hidden): ")
    if not email or not password:
        print("Email and password are required.")
        return 2

    try:
        client = create_supabase_client(get_settings())
        response = client.auth.sign_in_with_password(
            {"email": email, "password": password}
        )
    except Exception as exc:
        print(f"Login failed: {type(exc).__name__}")
        return 1

    if response.user is None or response.session is None:
        print("Login failed: Supabase returned no user session.")
        return 1

    print("\nLogin successful")
    print(f"User ID: {response.user.id}")
    print(f"Email: {response.user.email}")
    print("\nAccess Token (development testing only; do not commit or share):")
    print(response.session.access_token)
    print("\nThe refresh token is intentionally not printed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
