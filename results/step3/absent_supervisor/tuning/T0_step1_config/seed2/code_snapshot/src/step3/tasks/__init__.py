"""Step 3 tasks. ``get_task(name, **params)`` builds one by name."""

import importlib

NAMES = ("grid", "tomato", "taxi", "absent_supervisor", "mountain_car", "lunar_lander")


def module(name):
    if name not in NAMES:
        raise ValueError(f"unknown task {name!r}; choose from {NAMES}")
    return importlib.import_module(f"{__name__}.{name}")


def get_task(name, **params):
    return module(name).make_task(**params)
