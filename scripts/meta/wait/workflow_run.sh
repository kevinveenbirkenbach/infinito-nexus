#!/usr/bin/env bash
set -euo pipefail

: "${GITHUB_REPOSITORY:?Missing GITHUB_REPOSITORY}"
: "${GH_TOKEN:?Missing GH_TOKEN}"
: "${WORKFLOW_FILE:?Missing WORKFLOW_FILE}"
: "${TARGET_EVENT:?Missing TARGET_EVENT}"
: "${PR_NUMBER:?Missing PR_NUMBER}"
: "${WAIT_ATTEMPTS:?Missing WAIT_ATTEMPTS}"
: "${WAIT_SLEEP_SECONDS:?Missing WAIT_SLEEP_SECONDS}"

if ! command -v gh >/dev/null 2>&1; then
  echo "ERROR: gh CLI not found." >&2
  exit 1
fi

if ! command -v jq >/dev/null 2>&1; then
  echo "ERROR: jq not found." >&2
  exit 1
fi

pr_updated_at="${PR_UPDATED_AT:-}"
last_state=""
last_run_id=""

find_matching_run() {
  gh api --paginate \
    -H "Accept: application/vnd.github+json" \
    "/repos/${GITHUB_REPOSITORY}/actions/workflows/${WORKFLOW_FILE}/runs?event=${TARGET_EVENT}&per_page=100" \
  | jq -sc \
      --argjson pr_number "${PR_NUMBER}" \
      --arg pr_updated_at "${pr_updated_at}" '
        [
          .[]
          | .workflow_runs[]?
          | select(any(.pull_requests[]?; (.number // -1) == $pr_number))
          | select($pr_updated_at == "" or .created_at >= $pr_updated_at)
        ]
        | sort_by(.created_at)
        | last // empty
      '
}

echo "Waiting for workflow ${WORKFLOW_FILE} (${TARGET_EVENT}) for PR #${PR_NUMBER}"
if [[ -n "${pr_updated_at}" ]]; then
  echo "Ignoring runs created before PR updated_at=${pr_updated_at}"
fi

for attempt in $(seq 1 "${WAIT_ATTEMPTS}"); do
  run_json="$(find_matching_run)"

  if [[ -z "${run_json}" || "${run_json}" == "null" ]]; then
    state="missing"
    if [[ "${state}" != "${last_state}" ]]; then
      echo "[${attempt}/${WAIT_ATTEMPTS}] No matching workflow run found yet."
      last_state="${state}"
    else
      echo "[${attempt}/${WAIT_ATTEMPTS}] Still waiting for matching workflow run..."
    fi
    sleep "${WAIT_SLEEP_SECONDS}"
    continue
  fi

  run_id="$(jq -r '.id' <<<"${run_json}")"
  status="$(jq -r '.status' <<<"${run_json}")"
  conclusion="$(jq -r '.conclusion // ""' <<<"${run_json}")"
  url="$(jq -r '.html_url // ""' <<<"${run_json}")"
  created_at="$(jq -r '.created_at // ""' <<<"${run_json}")"
  state="${run_id}:${status}:${conclusion}"

  if [[ "${state}" != "${last_state}" || "${run_id}" != "${last_run_id}" ]]; then
    echo "[${attempt}/${WAIT_ATTEMPTS}] Matching run ${run_id} created_at=${created_at} status=${status} conclusion=${conclusion:-<pending>}"
    if [[ -n "${url}" ]]; then
      echo "Run URL: ${url}"
    fi
    last_state="${state}"
    last_run_id="${run_id}"
  else
    echo "[${attempt}/${WAIT_ATTEMPTS}] Waiting for run ${run_id}... status=${status}"
  fi

  if [[ "${status}" != "completed" ]]; then
    sleep "${WAIT_SLEEP_SECONDS}"
    continue
  fi

  if [[ "${conclusion}" == "success" ]]; then
    echo "Workflow run completed successfully: ${run_id}"
    exit 0
  fi

  echo "Workflow run ${run_id} finished with conclusion=${conclusion}" >&2
  if [[ -n "${url}" ]]; then
    echo "Run URL: ${url}" >&2
  fi
  exit 1
done

echo "Timed out waiting for workflow ${WORKFLOW_FILE} (${TARGET_EVENT}) for PR #${PR_NUMBER}" >&2
exit 1
