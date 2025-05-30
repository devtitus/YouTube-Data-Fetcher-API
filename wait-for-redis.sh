#!/bin/bash
set -e

host="$1"
port="$2"
shift 2
cmd="$@"

until redis-cli -h "$host" -p "$port" ping; do
  >&2 echo "Redis is unavailable - sleeping"
  sleep 1
done

>&2 echo "Redis is up - executing command"
exec $cmd 