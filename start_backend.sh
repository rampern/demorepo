#!/bin/bash

# Start backend server locally

set -e

export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/postgres"
export JWT_SECRET="supersecretjwtkey"

echo "Starting backend server at http://localhost:8000"

uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
