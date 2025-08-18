def dict_to_cli_args(data):
    """
    Convert a dictionary into CLI argument string.
    Example:
    {
        "backup-dir": "/mnt/backups",
        "shutdown": True,
        "ignore-volumes": ["redis", "memcached"]
    }
    becomes:
    --backup-dir=/mnt/backups --shutdown --ignore-volumes="redis memcached"
    """
    if not isinstance(data, dict):
        raise TypeError("Expected a dictionary for CLI argument conversion")

    args = []

    for key, value in data.items():
        cli_key = f"--{key}"

        if isinstance(value, bool):
            if value:
                args.append(cli_key)
        elif isinstance(value, list):
            items = " ".join(map(str, value))
            args.append(f'{cli_key}="{items}"')
        elif value is not None:
            args.append(f'{cli_key}={value}')

    return " ".join(args)

class FilterModule(object):
    def filters(self):
        return {
            'dict_to_cli_args': dict_to_cli_args
        }
