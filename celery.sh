#!/usr/bin/env bash
celery -A app.tasks.celery worker --loglevel=info --concurrency=${CELERY_CONCURRENCY:-2}
