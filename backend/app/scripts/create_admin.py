"""Controlled admin account creation.

Usage (from the backend directory, inside the virtualenv):

    python -m app.scripts.create_admin --email admin@annadata.local --name "Anna Admin" --password "change-me"

The same user can be promoted to admin with this script too. Farmer
self-registration can never create admin accounts.
"""

import argparse
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.security import get_password_hash  # noqa: E402
from app.database.session import SessionLocal  # noqa: E402
from app.models.user import ROLE_ADMIN, User  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Create or promote an ANNADATA admin")
    parser.add_argument("--email", required=True)
    parser.add_argument("--name", default="ANNADATA Admin")
    parser.add_argument("--password", required=True)
    args = parser.parse_args()

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == args.email).first()
        if user is None:
            user = User(
                name=args.name,
                email=args.email,
                role=ROLE_ADMIN,
                password_hash=get_password_hash(args.password),
            )
            db.add(user)
            db.commit()
            print(f"Created admin: {user.email}")
        else:
            user.role = ROLE_ADMIN
            user.password_hash = get_password_hash(args.password)
            db.commit()
            print(f"Promoted to admin: {user.email}")
    finally:
        db.close()


if __name__ == "__main__":
    main()