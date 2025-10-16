#!/bin/bash

# Setup test data for E2E tests
# This script copies test PDFs and loads them into the database

set -e

echo "Setting up test data..."

# Ensure directories exist
mkdir -p /data/pdfs /data/images

# Remove existing test data first (idempotent)
echo "Cleaning up old test data..."
flask remove-docs 'test-bund-2020.pdf' 2>/dev/null || true

# Copy test PDFs
echo "Copying test PDFs..."
cp tests/fixtures/pdfs/*.pdf /data/pdfs/

# Load test documents into database
echo "Loading test documents into database..."
flask update-docs 'test-*'

echo "Test data setup complete!"
