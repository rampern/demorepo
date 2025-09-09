#!/bin/bash

# Start frontend development server locally

set -e

cd frontend

if ! command -v npm &> /dev/null
then
    echo "npm could not be found. Please install Node.js and npm."
    exit 1
fi

npm install --legacy-peer-deps
# Use 127.0.0.1 to avoid proxy ECONNREFUSED errors
npm run dev
