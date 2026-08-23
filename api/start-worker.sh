#!/bin/sh
set -e

echo "Starting background job worker..."
exec dramatiq app.workers.exports
