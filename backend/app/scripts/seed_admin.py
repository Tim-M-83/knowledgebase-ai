import argparse

from app.core.security import get_password_hash
from app.db.session import SessionLocal
from app.models.user import Role, User


def main() -> None:
    parser = argparse.ArgumentParser(description='Seed first admin user')
    parser.add_argument('--email', required=True)
    parser.add_argument('--password', required=True)
    args = parser.parse_args()

    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == args.email).first()
        if existing:
            existing.role = Role.admin
            existing.password_hash = get_password_hash(args.password)
            existing.must_change_credentials = False
            existing.is_bootstrap_admin = False
            db.commit()
            print(f'Updated existing user {args.email} to admin')
            return

        user = User(
            email=args.email,
            password_hash=get_password_hash(args.password),
            role=Role.admin,
            must_change_credentials=False,
            is_bootstrap_admin=False,
        )
        db.add(user)
        db.commit()
        print(f'Created admin user {args.email}')
    finally:
        db.close()


if __name__ == '__main__':
    main()
