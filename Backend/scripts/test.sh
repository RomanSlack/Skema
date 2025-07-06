#!/bin/bash
# Test script

echo "Running Skema API tests..."

# Run linting
echo "Running code quality checks..."
black --check app/
isort --check-only app/
flake8 app/

# Run type checking
echo "Running type checks..."
mypy app/

# Run tests
echo "Running tests..."
pytest -v --cov=app --cov-report=html

echo "Tests completed!"