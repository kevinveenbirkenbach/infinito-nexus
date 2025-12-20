from __future__ import annotations

from . import __main__ as _main

# Expose patchable symbols for unit tests
build_mappings = _main.build_mappings
output_graph = _main.output_graph

def find_roles(*args, **kwargs):
    return _main.find_roles(*args, **kwargs)

def process_role(*args, **kwargs):
    # sync patched callables into the implementation module
    _main.build_mappings = build_mappings
    _main.output_graph = output_graph
    return _main.process_role(*args, **kwargs)

def main(*args, **kwargs):
    _main.build_mappings = build_mappings
    _main.output_graph = output_graph
    return _main.main(*args, **kwargs)

def __getattr__(name: str):
    return getattr(_main, name)
