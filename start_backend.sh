#!/bin/bash

# Start backend server locally

set -e

export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/postgres"
export JWT_SECRET="supersecretjwtkey"

# Run uvicorn with reload for development
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
