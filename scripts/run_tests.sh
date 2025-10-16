#!/bin/bash

# Script to run E2E tests locally
# Usage: ./scripts/run_tests.sh

set -e

echo "Starting services with docker compose..."
docker compose up -d

echo "Waiting for app to be ready..."
timeout 60 bash -c 'until curl -f http://localhost:5000 > /dev/null 2>&1; do sleep 2; done' || {
    echo "App failed to start. Showing logs:"
    docker compose logs
    docker compose down
    exit 1
}

echo "App is ready! Running tests..."
TEST_BASE_URL=http://localhost:5000 pytest tests/ -v

TEST_EXIT_CODE=$?

echo "Stopping services..."
docker compose down

exit $TEST_EXIT_CODE
