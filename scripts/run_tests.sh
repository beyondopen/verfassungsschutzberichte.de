#!/bin/bash

# Script to run E2E tests locally with code coverage
# Usage: ./scripts/run_tests.sh

set -e

COMPOSE_FILES="-f docker-compose.yml -f docker-compose.test.yml"

cleanup() {
    echo "Stopping services..."
    docker compose $COMPOSE_FILES down
}
trap cleanup EXIT

# Clean old coverage data from volume mount
/bin/rm -f src/.coverage src/.coverage.*

echo "Starting services with coverage instrumentation..."
docker compose $COMPOSE_FILES up -d

echo "Waiting for app to be ready..."
timeout 90 bash -c 'until curl -f http://localhost:5001 > /dev/null 2>&1; do sleep 2; done' || {
    echo "App failed to start. Showing logs:"
    docker compose $COMPOSE_FILES logs
    exit 1
}

echo "Loading test data into database..."
docker compose $COMPOSE_FILES exec -T web bash /app/scripts/setup_test_data.sh || {
    echo "Failed to load test data. Showing logs:"
    docker compose $COMPOSE_FILES logs
    exit 1
}

echo "Installing test dependencies in container..."
docker compose $COMPOSE_FILES exec -T web pip install -q -r requirements-test.txt

echo "Running E2E tests in container..."
set +e
docker compose $COMPOSE_FILES exec -T web sh -c "TEST_BASE_URL=http://localhost:5000 pytest /app/tests/test_integration.py -v"
E2E_EXIT_CODE=$?
set -e

echo "Running unit tests with separate coverage data..."
set +e
docker compose $COMPOSE_FILES exec -T web sh -c "cd /app && coverage run --source=/app --data-file=/app/.coverage.unit -m pytest /app/tests/test_unit.py -v"
UNIT_EXIT_CODE=$?
set -e

echo "Stopping Flask to flush E2E coverage data..."
# SIGINT the coverage run process so it writes .coverage.e2e to the volume mount
docker compose $COMPOSE_FILES stop -t 10 web 2>/dev/null || true
sleep 1

echo ""
echo "=== Combining and Reporting Coverage ==="
# Start a temporary container to combine and report coverage
# The coverage data files are on the volume mount at src/
docker compose $COMPOSE_FILES run --rm -T --no-deps web sh -c '
  cd /app
  pip install -q coverage==7.4.0
  coverage combine
  coverage report --show-missing
'
echo ""

# Fail if either test suite failed
if [ $E2E_EXIT_CODE -ne 0 ] || [ $UNIT_EXIT_CODE -ne 0 ]; then
    echo "Tests failed (E2E=$E2E_EXIT_CODE, Unit=$UNIT_EXIT_CODE)"
    exit 1
fi
