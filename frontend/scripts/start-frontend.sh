#!/usr/bin/env bash
set -euo pipefail

static_service="${NOTES_HELPER_STATIC_SERVICE:-0}"
while IFS= read -r cgroup; do
  if [[ "$cgroup" == *"/notes-helper-frontend.service"* ]]; then
    static_service="1"
    break
  fi
done < /proc/self/cgroup

if [[ "$static_service" == "1" ]]; then
  npm run build
  exec npm run preview -- "$@"
fi

exec vite "$@"
