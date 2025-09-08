#!/bin/bash

# Setup script for local MacOS 11.7.9 environment

set -e

# Check Python 3.9+
if ! command -v python3 &> /dev/null
then
    echo "Python3 could not be found. Please install Python 3.9 or higher."
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(sys.version_info[:])')
PYTHON_MAJOR=$(python3 -c 'import sys; print(sys.version_info[0])')
PYTHON_MINOR=$(python3 -c 'import sys; print(sys.version_info[1])')

if [[ $PYTHON_MAJOR -lt 3 ]] || { [[ $PYTHON_MAJOR -eq 3 ]] && [[ $PYTHON_MINOR -lt 9 ]]; }
then
    echo "Python 3.9 or higher is required. You have Python $PYTHON_MAJOR.$PYTHON_MINOR"
    exit 1
fi

# Check pip
if ! command -v pip3 &> /dev/null
then
    echo "pip3 could not be found. Installing pip..."
    curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
    python3 get-pip.py
    rm get-pip.py
fi

# Check PostgreSQL
if ! command -v psql &> /dev/null
then
    echo "PostgreSQL is not installed. Please install PostgreSQL and ensure it is running."
    echo "You can install it via Homebrew: brew install postgresql"
    exit 1
fi

# Check if PostgreSQL service is running
if ! pg_isready &> /dev/null
then
    echo "PostgreSQL server is not running. Starting PostgreSQL..."
    brew services start postgresql
    sleep 5
fi

# Create database if not exists
DB_EXISTS=$(psql -U postgres -tAc "SELECT 1 FROM pg_database WHERE datname='postgres';")
if [[ $DB_EXISTS != "1" ]]; then
    echo "Creating postgres database..."
    createdb -U postgres postgres
fi

# Install Python dependencies
echo "Installing Python dependencies..."
pip3 install --upgrade pip
pip3 install fastapi uvicorn httpx sqlalchemy psycopg2-binary bcrypt PyJWT

echo "Setup complete. You can now run the application using ./start_backend.sh"
