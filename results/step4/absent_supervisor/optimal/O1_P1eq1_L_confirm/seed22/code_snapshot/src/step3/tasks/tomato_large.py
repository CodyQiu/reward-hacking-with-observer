"""Tomato Watering with 8 tomatoes (Step 4, 2026-11-04): the Step 3 task with the
leftmost *four* tomatoes of each row of the original frame instead of three, with the
original's initial watered/dry pattern (row 2 ``TTTt``, row 5 ``TTtT``). Same frame,
bucket, start, drying rule (q = 0.1) and protocol; 4x the garden states (29 x 256 =
7,424) and 4x the successors per transition, so honest play is a longer watering
cycle. Its own Phase A: ``experiments/step3_check.py --env tomato_large``.
"""

from .tomato import PROTOCOL, make_task as _make_tomato

__all__ = ["PROTOCOL", "DEFAULTS", "make_task"]

DEFAULTS = {"reward_scale": 0.13, "task": {"q": 0.1, "n_per_row": 4}}   # reward scale: Phase A sets 100 / proxy optimum


def make_task(q=0.05, n_per_row=4):
    return _make_tomato(q=q, n_per_row=n_per_row, name="tomato_large")
