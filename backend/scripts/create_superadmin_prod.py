#!/usr/bin/env python
"""Create a superadmin user in the production database using the app context.

Usage:
  python backend/scripts/create_superadmin_prod.py --username Frank --email frankadmin@trackit.com --password 'P@55w0rd123!_'

This script loads `backend/.env.production` (dotenv) and starts the app
with the `production` config. It will reuse the first Organization if
one exists, or create a "System" organization otherwise (because the
`users.organisation_id` column is NOT NULL).

WARNING: Run this against a backed-up production database. This script
creates a single user and does not modify other data.
"""

import argparse
import os
from dotenv import load_dotenv

# Load production env if present
env_path = os.path.join(os.path.dirname(__file__), '..', '.env.production')
if os.path.exists(env_path):
    load_dotenv(env_path)

from app import create_app, db
from app.models.user import User
from app.models.organization import Organization


def create_superadmin(username, email, password):
    app = create_app('production')
    with app.app_context():
        # Ensure there is an organisation to attach the user to
        org = Organization.query.first()
        if not org:
            org = Organization(name='System', code='SYSTEM', description='System organisation')
            db.session.add(org)
            db.session.commit()

        # Check if user already exists
        existing = User.query.filter_by(email=email).first()
        if existing:
            print(f"User with email {email} already exists (id={existing.id}, role={existing.role}). Aborting.")
            return

        user = User(
            organisation_id=org.id,
            username=username,
            email=email,
            first_name=username,
            last_name='Superadmin',
            role='superadmin'
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        print(f"Created superadmin: {email} (id={user.id}) attached to organisation id={org.id}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--username', required=True)
    parser.add_argument('--email', required=True)
    parser.add_argument('--password', required=True)
    args = parser.parse_args()

    create_superadmin(args.username, args.email, args.password)


if __name__ == '__main__':
    main()
