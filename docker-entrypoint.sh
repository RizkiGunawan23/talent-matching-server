#!/bin/bash
set -e

if [ "$ENVIRONMENT" = "production" ]; then
    echo "Starting in PRODUCTION mode"
    exec /usr/local/bin/gunicorn --workers=2 --threads=4 --worker-class=gthread --bind 0.0.0.0:8000 talent_matching_server.wsgi:application
else
    echo "Starting in DEVELOPMENT mode"
    exec /usr/local/bin/gunicorn --reload --workers=1 --threads=1 --bind 0.0.0.0:8000 talent_matching_server.wsgi:application
fi