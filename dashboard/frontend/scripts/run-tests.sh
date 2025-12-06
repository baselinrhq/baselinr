#!/bin/bash
# Frontend test runner script for git hooks
# Runs Vitest tests and exits with appropriate code

set -e

cd "$(dirname "$0")/.." || exit 1

echo "Running frontend tests..."
npm run test:run

if [ $? -eq 0 ]; then
    echo "✓ Frontend tests passed"
    exit 0
else
    echo "✗ Frontend tests failed"
    exit 1
fi

