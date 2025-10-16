#!/bin/bash

# Script to run E2E tests locally
# Usage: ./scripts/run_tests.sh

set -e

echo "Starting services with docker compose..."
docker compose up -d

echo "Waiting for app to be ready..."
timeout 60 bash -c 'until curl -f http://localhost:5001 > /dev/null 2>&1; do sleep 2; done' || {
    echo "App failed to start. Showing logs:"
    docker compose logs
    docker compose down
    exit 1
}

echo "Loading test data into database..."
docker compose exec -T web bash /app/scripts/setup_test_data.sh || {
    echo "Failed to load test data. Showing logs:"
    docker compose logs
    docker compose down
    exit 1
}

echo "Installing test dependencies in container..."
docker compose exec -T web pip install -q -r requirements-test.txt

echo "Running tests in container..."
docker compose exec -T web sh -c "TEST_BASE_URL=http://localhost:5000 pytest /app/tests/ -v"

TEST_EXIT_CODE=$?

echo "Stopping services..."
docker compose down

exit $TEST_EXIT_CODE
