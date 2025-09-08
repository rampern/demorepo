#!/bin/bash

# Script to initialize the database schema using Alembic migrations or SQLAlchemy

set -e

# Set default DATABASE_URL if not set
DATABASE_URL=${DATABASE_URL:-"postgresql://postgres:postgres@localhost:5432/postgres"}

export DATABASE_URL

# Check if alembic is installed, if not install it
if ! command -v alembic &> /dev/null
then
    echo "Alembic not found, installing..."
    pip3 install alembic
fi

# Check if alembic.ini exists
if [ ! -f alembic.ini ]; then
    echo "Alembic configuration not found. Creating default alembic.ini and migration environment..."
    alembic init alembic

    # Modify alembic.ini to use DATABASE_URL environment variable
    sed -i.bak 's#sqlalchemy.url = .*#sqlalchemy.url = ${DATABASE_URL}#' alembic.ini

    # Create initial migration
    alembic revision --autogenerate -m "Initial migration"
fi

# Run migrations
alembic upgrade head

echo "Database initialized and migrations applied successfully."
