#!/usr/bin/env python3
"""
Run the full localhost integration flow entirely inside the infinito Docker container,
without writing any artifacts to the host filesystem.
Catches missing schema/config errors during credential vaulting and skips those apps.
"""
import subprocess
import os
import sys

def main():
    repo = os.path.abspath(os.getcwd())

    bash_script = '''
set -e

ART=/integration-artifacts
mkdir -p "$ART"
echo testpassword > "$ART/vaultpw.txt"

# 1) Generate inventory
python3 -m cli.build.inventory.full \
  --host localhost \
  --inventory-style hostvars \
  --format yaml \
  --output "$ART/inventory.yml"

# 2) Credentials per-app
apps=$(python3 <<EOF
import yaml
inv = yaml.safe_load(open('/integration-artifacts/inventory.yml'))
print(' '.join(inv['_meta']['hostvars']['localhost']['invokable_applications']))
EOF
)
for app in $apps; do
  echo "⏳ Vaulting credentials for $app..."
  output=$(python3 -m cli.create.credentials \
    --role-path "/repo/roles/$app" \
    --inventory-file "$ART/inventory.yml" \
    --vault-password-file "$ART/vaultpw.txt" \
    --force 2>&1) || rc=$?; rc=${rc:-0}

  if [ "$rc" -eq 0 ]; then
    echo "✅ Credentials generated for $app"
  elif echo "$output" | grep -q "No such file or directory"; then
    echo "⚠️  Skipping $app (no schema/config)"
  elif echo "$output" | grep -q "Plain algorithm for"; then
    # Collect all plain-algo keys
    keys=( $(echo "$output" | grep -oP "Plain algorithm for '\K[^']+") )
    overrides=()
    for key in "${keys[@]}"; do
      if [[ "$key" == *api_key ]]; then
        val=$(python3 - << 'PY'
import random, string
print(''.join(random.choices(string.ascii_letters+string.digits, k=32)))
PY
)
      elif [[ "$key" == *password ]]; then
        val=$(python3 - << 'PY'
import random, string
print(''.join(random.choices(string.ascii_letters+string.digits, k=12)))
PY
)
      else
        val=$(python3 - << 'PY'
import random, string
print(''.join(random.choices(string.ascii_letters+string.digits, k=16)))
PY
)
      fi
      echo "  → Overriding $key=$val"
      overrides+=("--set" "$key=$val")
    done
    # Retry with overrides
    echo "🔄 Retrying with overrides..."
    retry_out=$(python3 -m cli.create.credentials \
      --role-path "/repo/roles/$app" \
      --inventory-file "$ART/inventory.yml" \
      --vault-password-file "$ART/vaultpw.txt" \
      "${overrides[@]}" \
      --force 2>&1) || retry_rc=$?; retry_rc=${retry_rc:-0}
    if [ "$retry_rc" -eq 0 ]; then
      echo "✅ Credentials generated for $app (with overrides)"
    else
      echo "❌ Override failed for $app:"
      echo "$retry_out"
    fi
  else
    echo "❌ Credential error for $app:"
    echo "$output"
  fi
done

# 3) Show generated files
ls -R "$ART" 2>/dev/null

echo "
===== inventory.yml ====="
cat "$ART/inventory.yml"

echo "
===== vaultpw.txt ====="
cat "$ART/vaultpw.txt"

# 4) Deploy
python3 -m cli.deploy \
  "$ART/inventory.yml" \
  --limit localhost \
  --vault-password-file "$ART/vaultpw.txt" \
  --verbose
'''

    cmd = [
        "docker", "run", "--rm",
        "-v", f"{repo}:/repo",
        "-w", "/repo",
        "--entrypoint", "bash",
        "infinito:latest",
        "-c", bash_script
    ]
    print(f"\033[96m> {' '.join(cmd)}\033[0m")
    rc = subprocess.call(cmd)
    sys.exit(rc)

if __name__ == '__main__':
    main()
