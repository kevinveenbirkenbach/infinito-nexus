# User

## Description

This role configures a basic user environment (shell dotfiles and SSH authorized_keys)
for a user selected via `user_key`.

## Single Point of Truth (SPOT)

User data is defined under `users.<key>` and referenced exclusively via `user_key`.

Resolution rules:
- `user_username` is resolved from `users[user_key].username` (fallback: `user_key`)
- Home path and ownership are based on `user_username`
- SSH keys are read from `users[user_key].authorized_keys`

## Required input

- `user_key`

## Optional user fields

- `users.<user_key>.username` (defaults to `<user_key>`)
- `users.<user_key>.authorized_keys` (list; may be empty)
