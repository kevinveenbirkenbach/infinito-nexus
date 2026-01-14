from __future__ import annotations

import subprocess
from pathlib import Path

from .compose import Compose
from .deps import apps_with_deps, resolve_run_after
from .logs import append_text, log_path, write_text


def _repo_root_from_here() -> Path:
    return Path(__file__).resolve().parents[3]


def _ensure_vault_password_file(compose: Compose) -> None:
    compose.exec(
        [
            "sh",
            "-lc",
            "mkdir -p /etc/inventories/github-ci && "
            "[ -f /etc/inventories/github-ci/.password ] || "
            "printf '%s\n' 'ci-vault-password' > /etc/inventories/github-ci/.password",
        ],
        check=True,
    )


def _create_inventory(compose: Compose, *, include: list[str]) -> None:
    if not include:
        raise ValueError("include must not be empty")

    cmd = [
        "python3",
        "-m",
        "cli.create.inventory",
        "/etc/inventories/github-ci",
        "--host",
        "localhost",
        "--ssl-disabled",
        "--primary-domain",
        "infinito.localhost",
        "--vars-file",
        "inventory.sample.yml",
        "--include",
        ",".join(include),
    ]

    compose.exec(cmd, check=True, workdir="/opt/src/infinito")
    _ensure_vault_password_file(compose)


def _run_deploy(
    compose: Compose,
    *,
    deploy_type: str,
    deploy_ids: list[str],
    debug: bool,
) -> int:
    """
    deploy_type: "server", "workstation" or "universal"
    """
    cmd = [
        "python3",
        "-m",
        "cli.deploy.dedicated",
        "/etc/inventories/github-ci/servers.yml",
        "-p",
        "/etc/inventories/github-ci/.password",
        "-vv",
        "--assert",
        "true",
        "--diff",
        "-T",
        deploy_type,
        "-i",
        *deploy_ids,
    ]
    if debug:
        cmd.insert(cmd.index("-T"), "--debug")

    r = compose.exec(cmd, check=False)
    return r.returncode


def run_test_plan(
    *,
    deploy_type: str,
    distro: str,
    no_cache: bool,
    missing_only: bool,
    only_app: str | None,
    logs_dir: Path,
    keep_stack_on_failure: bool,
    debug: bool,
) -> int:
    if not only_app:
        raise ValueError(
            "Runner no longer performs discovery. You must pass --app from the workflow matrix."
        )

    if deploy_type not in {"server", "workstation", "universal"}:
        raise ValueError(f"Invalid deploy_type: {deploy_type}")

    repo_root = _repo_root_from_here()
    compose = Compose(repo_root=repo_root, distro=distro)

    exit_code = 0
    main_log = log_path(logs_dir, deploy_type, distro, "orchestrator")
    write_text(
        main_log,
        f"deploy_type={deploy_type}\ndistro={distro}\nonly_app={only_app}\ndebug={debug}\n",
    )

    try:
        compose.build_infinito(no_cache=no_cache, missing_only=missing_only)
        compose.up()

        deps = resolve_run_after(compose, only_app)
        deploy_ids = apps_with_deps(only_app, deps_role_names=deps)

        per_app_log = log_path(logs_dir, deploy_type, distro, f"app-{only_app}")
        write_text(
            per_app_log,
            " ".join(
                [
                    f"app={only_app}",
                    f"deps={','.join(deps) if deps else '<none>'}",
                    f"deploy_ids={','.join(deploy_ids) if deploy_ids else '<none>'}",
                ]
            )
            + "\n",
        )

        append_text(
            main_log, f"\nmode=single-with-deps\nresolved_ids={','.join(deploy_ids)}\n"
        )

        _create_inventory(compose, include=deploy_ids)

        rc = _run_deploy(
            compose, deploy_type=deploy_type, deploy_ids=deploy_ids, debug=debug
        )
        exit_code = rc

        if rc != 0:
            append_text(
                per_app_log,
                "\n--- hint ---\n"
                "Search workflow logs for the failing task output.\n"
                f"Also run: INFINITO_DISTRO={distro} docker compose --profile ci logs --tail=200\n",
            )
        return rc

    except subprocess.CalledProcessError as exc:
        exit_code = exc.returncode
        append_text(main_log, f"\nERROR: {exc}\n")
        return exc.returncode
    except Exception as exc:
        exit_code = 1
        append_text(main_log, f"\nERROR: {exc}\n")
        return 1
    finally:
        should_keep = keep_stack_on_failure and exit_code != 0
        if not should_keep:
            try:
                compose.down()
            except Exception:
                pass
