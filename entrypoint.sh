#!/bin/sh
set -eu

echo "Running database migrations..."
alembic upgrade head

case "${SEED_ON_STARTUP:-true}" in
    1|true|TRUE|True|yes|YES|Yes)
        echo "Seeding demo products..."
        python -m scripts.seed_products
        ;;
    *)
        echo "Skipping demo data seeding."
        ;;
esac

echo "Starting Paw Pantry API..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
