#!/usr/bin/env bash
# Changelog workflow helper scripts
# Usage: changelog.sh <command> [args...]
#
# Commands:
#   generate-entry <version>    — Generate <Update> block from git log
#   prepend-entry <file>         — Prepend entry from stdin to changelog.mdx

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── Generate a Mintlify <Update> block from commits since last tag ──
generate_entry() {
  local version="${1:?version required}"
  local date
  date="$(date +"%B %d, %Y")"

  # Find the previous tag
  local prev_tag
  prev_tag="$(git describe --tags --abbrev=0 "${version}"^ 2> /dev/null || echo "")"

  # Gather commits between previous tag and this tag
  local log_range
  if [ -n "$prev_tag" ]; then
    log_range="${prev_tag}..${version}"
  else
    log_range="HEAD"  # first tag — get all commits
  fi

  local commits
  commits="$(git log "${log_range}" --oneline --no-merges 2>/dev/null || true)"

  # Categorize commits by conventional commit prefix
  local features="" fixes="" perf="" docs="" refactor="" other="" deprecated="" removed="" deps=""

  while IFS= read -r line; do
    local msg="${line#* }"  # strip commit hash
    local category=""

    if echo "$msg" | grep -qiE "^feat(\(.*\))?:"; then
      features="$features  - ${msg#*: }\n"
    elif echo "$msg" | grep -qiE "^fix(\(.*\))?:"; then
      fixes="$fixes  - ${msg#*: }\n"
    elif echo "$msg" | grep -qiE "^perf(\(.*\))?:"; then
      perf="$perf  - ${msg#*: }\n"
    elif echo "$msg" | grep -qiE "^docs(\(.*\))?:"; then
      docs="$docs  - ${msg#*: }\n"
    elif echo "$msg" | grep -qiE "^refactor(\(.*\))?:"; then
      refactor="$refactor  - ${msg#*: }\n"
    elif echo "$msg" | grep -qiE "^deprecat(ed|ing)?(\(.*\))?:"; then
      deprecated="$deprecated  - ${msg#*: }\n"
    elif echo "$msg" | grep -qiE "^(remove|delete)(\(.*\))?:"; then
      removed="$removed  - ${msg#*: }\n"
    elif echo "$msg" | grep -qiE "^chore\(deps\):"; then
      deps="$deps  - ${msg#*: }\n"
    else
      other="$other  - $msg\n"
    fi
  done <<< "$commits"

  # Build the <Update> block content
  local body=""

  if [ -n "$features" ]; then
    body="${body}  ### New Features\n${features}\n"
  fi
  if [ -n "$fixes" ]; then
    body="${body}  ### Bug Fixes\n${fixes}\n"
  fi
  if [ -n "$perf" ]; then
    body="${body}  ### Performance\n${perf}\n"
  fi
  if [ -n "$refactor" ]; then
    body="${body}  ### Refactoring\n${refactor}\n"
  fi
  if [ -n "$docs" ]; then
    body="${body}  ### Documentation\n${docs}\n"
  fi
  if [ -n "$deprecated" ]; then
    body="${body}  ### Deprecations\n${deprecated}\n"
  fi
  if [ -n "$removed" ]; then
    body="${body}  ### Removals\n${removed}\n"
  fi
  if [ -n "$deps" ]; then
    body="${body}  ### Dependencies\n${deps}\n"
  fi
  if [ -n "$other" ]; then
    body="${body}  ### Other Changes\n${other}\n"
  fi

  # Strip trailing whitespace from each line
  body="$(echo -e "$body" | sed 's/[[:space:]]*$//')"

  # Output the <Update> block
  cat << UPDATE

<Update label="${version}" description="${date}">
${body}
</Update>
UPDATE
}

# ── Prepend an entry to changelog.mdx ──────────────────────────────
prepend_entry() {
  local file="${1:?changelog file required}"
  local tmpfile
  tmpfile="$(mktemp)"

  if [ ! -f "$file" ]; then
    echo "Error: $file not found" >&2
    exit 1
  fi

  # Read the new entry from stdin
  local entry
  entry="$(cat)"

  # Find the end of YAML frontmatter (second ---)
  local ln
  ln=0
  local count=0
  while IFS= read -r line; do
    ln=$((ln + 1))
    if [ "$line" = "---" ]; then
      count=$((count + 1))
      if [ "$count" -eq 2 ]; then
        break
      fi
    fi
  done < "$file"

  # Write: frontmatter + blank line + new entry + original content after frontmatter
  head -n "$ln" "$file" > "$tmpfile"
  echo "" >> "$tmpfile"
  echo "$entry" >> "$tmpfile"
  echo "" >> "$tmpfile"
  tail -n +$((ln + 1)) "$file" >> "$tmpfile"

  mv "$tmpfile" "$file"
  echo "✅ Prepended entry to $file"
}

# ── Main dispatch ──────────────────────────────────────────────────
COMMAND="${1:-}"
shift || true

case "$COMMAND" in
  generate-entry)
    generate_entry "$@"
    ;;
  prepend-entry)
    prepend_entry "$@"
    ;;
  *)
    echo "Usage: $0 {generate-entry|prepend-entry} [args...]"
    exit 1
    ;;
esac
