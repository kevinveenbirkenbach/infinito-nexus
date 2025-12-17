import os


def cdn_dirs(tree):
    out = set()

    def walk(v):
        if isinstance(v, dict):
            for x in v.values():
                walk(x)
        elif isinstance(v, list):
            for x in v:
                walk(x)
        elif isinstance(v, str) and os.path.isabs(v):
            out.add(v)

    walk(tree)
    return sorted(out)


class FilterModule(object):
    def filters(self):
        return {"cdn_dirs": cdn_dirs}
