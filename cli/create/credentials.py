#!/usr/bin/env python3
"""
Selectively add & vault NEW credentials in your inventory, preserving comments
and formatting. Existing values are left untouched unless --force is used.

Usage example:
  infinito create credentials \
    --role-path roles/web-app-akaunting \
    --inventory-file host_vars/echoserver.yml \
    --vault-password-file .pass/echoserver.txt \
    --set credentials.database_password=mysecret

With snippet mode (no file changes, just YAML output):

  infinito create credentials \
    --role-path roles/web-app-akaunting \
    --inventory-file host_vars/echoserver.yml \
    --vault-password-file .pass/echoserver.txt \
    --snippet
"""

import argparse
import sys
from pathlib import Path
from typing import Dict, Any, Union

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap

from module_utils.manager.inventory import InventoryManager
from module_utils.handler.vault import VaultHandler  # uses your existing handler


# ---------- helpers ----------

def ask_for_confirmation(key: str) -> bool:
    """Prompt the user for confirmation to overwrite an existing value."""
    confirmation = input(
        f"Are you sure you want to overwrite the value for '{key}'? (y/n): "
    ).strip().lower()
    return confirmation == 'y'


def ensure_map(node: CommentedMap, key: str) -> CommentedMap:
    """
    Ensure node[key] exists and is a mapping (CommentedMap) for round-trip safety.
    """
    if key not in node or not isinstance(node.get(key), CommentedMap):
        node[key] = CommentedMap()
    return node[key]


def _is_ruamel_vault(val: Any) -> bool:
    """Detect if a ruamel scalar already carries the !vault tag."""
    try:
        return getattr(val, 'tag', None) == '!vault'
    except Exception:
        return False


def _is_vault_encrypted(val: Any) -> bool:
    """
    Detect if value is already a vault string or a ruamel !vault scalar.
    Accept both '$ANSIBLE_VAULT' and '!vault' markers.
    """
    if _is_ruamel_vault(val):
        return True
    if isinstance(val, str) and ("$ANSIBLE_VAULT" in val or "!vault" in val):
        return True
    return False


def _vault_body(text: str) -> str:
    """
    Return only the vault body starting from the first line that contains
    '$ANSIBLE_VAULT'. If not found, return the original text.
    Also strips any leading '!vault |' header if present.
    """
    lines = text.splitlines()
    for i, ln in enumerate(lines):
        if "$ANSIBLE_VAULT" in ln:
            return "\n".join(lines[i:])
    return text


def _make_vault_scalar_from_text(text: str) -> Any:
    """
    Build a ruamel object representing a literal block scalar tagged with !vault
    by parsing a tiny YAML snippet. This avoids depending on yaml_set_tag().
    """
    body = _vault_body(text)
    indented = "  " + body.replace("\n", "\n  ")  # proper block scalar indentation
    snippet = f"v: !vault |\n{indented}\n"
    y = YAML(typ="rt")
    return y.load(snippet)["v"]


def to_vault_block(vault_handler: VaultHandler, value: Union[str, Any], label: str) -> Any:
    """
    Return a ruamel scalar tagged as !vault. If the input value is already
    vault-encrypted (string contains $ANSIBLE_VAULT or is a !vault scalar), reuse/wrap.
    Otherwise, encrypt plaintext via ansible-vault.

    Special rule:
    - Empty strings ("") are NOT encrypted and are returned as plain "".
    """
    # Empty strings should not be encrypted
    if isinstance(value, str) and value == "":
        return ""

    # Already a ruamel !vault scalar → reuse
    if _is_ruamel_vault(value):
        return value

    # Already an encrypted string (may include '!vault |' or just the header)
    if isinstance(value, str) and ("$ANSIBLE_VAULT" in value or "!vault" in value):
        return _make_vault_scalar_from_text(value)

    # Plaintext → encrypt now
    snippet = vault_handler.encrypt_string(str(value), label)
    return _make_vault_scalar_from_text(snippet)

def parse_overrides(pairs: list[str]) -> Dict[str, str]:
    """
    Parse --set key=value pairs into a dict.
    Supports both 'credentials.key=val' and 'key=val' (short) forms.
    """
    out: Dict[str, str] = {}
    for pair in pairs:
        k, v = pair.split("=", 1)
        out[k.strip()] = v.strip()
    return out


# ---------- main ----------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Selectively add & vault NEW credentials in your inventory, preserving comments/formatting."
    )
    parser.add_argument("--role-path", required=True, help="Path to your role")
    parser.add_argument("--inventory-file", required=True, help="Host vars file to update")
    parser.add_argument("--vault-password-file", required=True, help="Vault password file")
    parser.add_argument(
        "--set", nargs="*", default=[],
        help="Override values key[.subkey]=VALUE (applied to NEW keys; with --force also to existing)"
    )
    parser.add_argument(
        "-f", "--force", action="store_true",
        help="Allow overrides to replace existing values (will ask per key unless combined with --yes)"
    )
    parser.add_argument(
        "-y", "--yes", action="store_true",
        help="Non-interactive: assume 'yes' for all overwrite confirmations when --force is used"
    )
    parser.add_argument(
        "--snippet",
        action="store_true",
        help=(
            "Do not modify the inventory file. Instead, print a YAML snippet with "
            "the generated credentials to stdout. The snippet contains only the "
            "application's credentials (and ansible_become_password if provided)."
        ),
    )
    parser.add_argument(
        "--allow-empty-plain",
        action="store_true",
        help=(
            "Allow 'plain' credentials in the schema without an explicit --set override. "
            "Missing plain values will be set to an empty string before encryption."
        ),
    )
    args = parser.parse_args()

    overrides = parse_overrides(args.set)

    # Initialize inventory manager (provides schema + app_id + vault)
    manager = InventoryManager(
        role_path=Path(args.role_path),
        inventory_path=Path(args.inventory_file),
        vault_pw=args.vault_password_file,
        overrides=overrides,
        allow_empty_plain=args.allow_empty_plain,
    )

    yaml_rt = YAML(typ="rt")
    yaml_rt.preserve_quotes = True

    # Get schema-applied structure (defaults etc.) for *non-destructive* merge
    schema_inventory: Dict[str, Any] = manager.apply_schema()
    schema_apps = schema_inventory.get("applications", {})
    schema_app_block = schema_apps.get(manager.app_id, {})
    schema_creds = schema_app_block.get("credentials", {}) if isinstance(schema_app_block, dict) else {}

    # -------------------------------------------------------------------------
    # SNIPPET MODE: only build a YAML fragment and print to stdout, no file I/O
    # -------------------------------------------------------------------------
    if args.snippet:
        # Build a minimal structure:
        # applications:
        #   <app_id>:
        #     credentials:
        #       key: !vault |
        #         ...
        # ansible_become_password: !vault | ...
        snippet_data = CommentedMap()
        apps_snip = ensure_map(snippet_data, "applications")
        app_block_snip = ensure_map(apps_snip, manager.app_id)
        creds_snip = ensure_map(app_block_snip, "credentials")

        for key, default_val in schema_creds.items():
            # Priority: --set exact key → default from schema → empty string
            ov = overrides.get(f"credentials.{key}", None)
            if ov is None:
                ov = overrides.get(key, None)

            if ov is not None:
                value_for_key: Union[str, Any] = ov
            else:
                if _is_vault_encrypted(default_val):
                    creds_snip[key] = to_vault_block(manager.vault_handler, default_val, key)
                    continue
                value_for_key = "" if default_val is None else str(default_val)

            creds_snip[key] = to_vault_block(manager.vault_handler, value_for_key, key)

        # Optional ansible_become_password only if provided via overrides
        if "ansible_become_password" in overrides:
            snippet_data["ansible_become_password"] = to_vault_block(
                manager.vault_handler,
                overrides["ansible_become_password"],
                "ansible_become_password",
            )

        yaml_rt.dump(snippet_data, sys.stdout)
        return 0

    # -------------------------------------------------------------------------
    # DEFAULT MODE: modify the inventory file on disk (previous behavior)
    # -------------------------------------------------------------------------

    # 1) Load existing inventory with ruamel (round-trip)
    with open(args.inventory_file, "r", encoding="utf-8") as f:
        data = yaml_rt.load(f)  # CommentedMap or None
    if data is None:
        data = CommentedMap()

    # 2) Ensure structural path exists
    apps = ensure_map(data, "applications")
    app_block = ensure_map(apps, manager.app_id)
    creds = ensure_map(app_block, "credentials")

    # 3) Add ONLY missing credential keys (respect existing values)
    newly_added_keys = set()
    for key, default_val in schema_creds.items():
        if key in creds:
            # Existing → do not touch (preserve plaintext/vault/formatting/comments)
            continue

        # Value to use for the new key
        # Priority: --set exact key → default from schema → empty string
        ov = overrides.get(f"credentials.{key}", None)
        if ov is None:
            ov = overrides.get(key, None)

        if ov is not None:
            value_for_new_key: Union[str, Any] = ov
        else:
            if _is_vault_encrypted(default_val):
                # Schema already provides a vault value → take it as-is
                creds[key] = to_vault_block(manager.vault_handler, default_val, key)
                newly_added_keys.add(key)
                continue
            value_for_new_key = "" if default_val is None else str(default_val)

        # Insert as !vault literal (encrypt if needed)
        creds[key] = to_vault_block(manager.vault_handler, value_for_new_key, key)
        newly_added_keys.add(key)

    # 4) ansible_become_password: only add if missing;
    #    never rewrite an existing one unless --force (+ confirm/--yes) and override provided.
    if "ansible_become_password" not in data:
        val = overrides.get("ansible_become_password", None)
        if val is not None:
            data["ansible_become_password"] = to_vault_block(
                manager.vault_handler, val, "ansible_become_password"
            )
    else:
        if args.force and "ansible_become_password" in overrides:
            do_overwrite = args.yes or ask_for_confirmation("ansible_become_password")
            if do_overwrite:
                data["ansible_become_password"] = to_vault_block(
                    manager.vault_handler, overrides["ansible_become_password"], "ansible_become_password"
                )

    # 5) Overrides for existing credential keys (only with --force)
    if args.force:
        for ov_key, ov_val in overrides.items():
            # Accept both 'credentials.key' and bare 'key'
            key = ov_key.split(".", 1)[1] if ov_key.startswith("credentials.") else ov_key
            if key in creds:
                # If we just added it in this run, don't ask again or rewrap
                if key in newly_added_keys:
                    continue
                if args.yes or ask_for_confirmation(key):
                    creds[key] = to_vault_block(manager.vault_handler, ov_val, key)

    # 6) Write back with ruamel (preserve formatting & comments)
    with open(args.inventory_file, "w", encoding="utf-8") as f:
        yaml_rt.dump(data, f)

    print(f"✅ Added new credentials without touching existing formatting/comments → {args.inventory_file}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
