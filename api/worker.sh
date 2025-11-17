#!/usr/bin/env bash
set -e
rq worker -u "${REDIS_URL}" --worker-ttl 600 docparser-queue


