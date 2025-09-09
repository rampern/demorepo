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
npm run dev
