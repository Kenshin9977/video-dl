#!/usr/bin/env bash
# Submit a file to Apple's notary service and wait for the verdict, surviving the
# two things that make `notarytool submit --wait` fragile: transient network
# errors on a poll (it aborts and throws away however long it already waited) and
# Apple backlogs that leave a submission "In Progress" for the better part of an
# hour. Submit once, then poll on our own loop that shrugs off a dropped request.
#
# Env: NOTARY_KEY (path to the .p8), MACOS_NOTARY_KEY_ID, MACOS_NOTARY_ISSUER
# Usage: notarize.sh <file-to-submit>
set -euo pipefail

FILE=$1
creds=(--key "$NOTARY_KEY" --key-id "$MACOS_NOTARY_KEY_ID" --issuer "$MACOS_NOTARY_ISSUER")

id=$(xcrun notarytool submit "$FILE" "${creds[@]}" --output-format json \
  | python3 -c 'import sys, json; print(json.load(sys.stdin)["id"])')
echo "Notarization submitted: $FILE -> $id"

# 90 minutes: Apple's backlogs run long, but a submission still "In Progress" past
# that is a service incident to wait out on a re-run, not something to block on.
deadline=$(( $(date +%s) + 5400 ))
while :; do
  # 2>/dev/null so a network blip yields empty output, parsed as "Unreachable"
  # below, rather than killing the script under `set -e`.
  status=$(xcrun notarytool info "$id" "${creds[@]}" --output-format json 2>/dev/null \
    | python3 -c 'import sys, json
try:
    print(json.load(sys.stdin).get("status", "Unknown"))
except Exception:
    print("Unreachable")')
  echo "  $id: $status"
  case "$status" in
    Accepted) exit 0 ;;
    Invalid|Rejected)
      xcrun notarytool log "$id" "${creds[@]}" || true
      exit 1 ;;
  esac
  if [ "$(date +%s)" -gt "$deadline" ]; then
    echo "::error::notarization unresolved after 90 min (Apple backlog); submission $id still $status"
    exit 1
  fi
  sleep 30
done
