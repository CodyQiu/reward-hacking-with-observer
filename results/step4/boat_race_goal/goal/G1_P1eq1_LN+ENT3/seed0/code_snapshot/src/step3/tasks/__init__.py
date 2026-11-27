"""Step 3 tasks. ``get_task(name, **params)`` builds one by name."""

import importlib

NAMES = ("grid", "tomato", "taxi", "absent_supervisor", "mountain_car", "lunar_lander", "boat_race",
         "tomato_large", "grid_routes", "grid_hideout",
         "grid_goal", "absent_supervisor_goal", "tomato_goal", "taxi_goal", "boat_race_goal")


def module(name):
    if name not in NAMES:
        raise ValueError(f"unknown task {name!r}; choose from {NAMES}")
    return importlib.import_module(f"{__name__}.{name}")


def get_task(name, **params):
    return module(name).make_task(**params)
