"""Check bookkeeping shared by the experiment scripts.

Every quantitative claim an experiment makes goes through ``CheckLog.check`` so
that the script's exit status, not the reader's eye, decides whether the run
reproduced. Controls are registered with ``check_control`` purely so they print
under their own heading -- a result without its control is not acceptable
(CLAUDE.md 3), so it should be impossible to skim the output and miss one.
"""

import sys

__all__ = ["CheckLog", "approx", "run_tests"]

_PASS = "PASS"
_FAIL = "FAIL"


def approx(a, b, tol=1e-6):
    return abs(float(a) - float(b)) <= tol


def run_tests(namespace, title):
    """Run every ``test_*`` callable in ``namespace``, in source order.

    Lets the test files double as plain scripts (``python tests/test_solver.py``)
    without adding pytest as a dependency, while staying pytest-compatible if it is
    available.
    """
    names = [
        n
        for n, v in namespace.items()
        if n.startswith("test_") and callable(v) and hasattr(v, "__code__")
    ]
    names.sort(key=lambda n: namespace[n].__code__.co_firstlineno)
    print(f"\n{'=' * 78}\n{title}\n{'=' * 78}")
    failures = []
    for name in names:
        try:
            namespace[name]()
        except Exception as exc:  # noqa: BLE001 - a test file wants every failure
            failures.append((name, exc))
            print(f"  [{_FAIL}] {name}\n         {type(exc).__name__}: {exc}")
        else:
            print(f"  [{_PASS}] {name}")
    print(f"\n  {len(names)} tests, {len(failures)} failed")
    if failures:
        sys.exit(1)
    return True


class CheckLog:
    def __init__(self, title):
        self.title = title
        self.rows = []          # (kind, name, passed, detail)
        self.figures = []
        self.findings = []
        print(f"\n{'=' * 78}\n{title}\n{'=' * 78}")

    def check(self, name, passed, detail="", kind="check"):
        passed = bool(passed)
        self.rows.append((kind, name, passed, detail))
        flag = _PASS if passed else _FAIL
        tag = "CONTROL " if kind == "control" else ""
        print(f"  [{flag}] {tag}{name}" + (f"  --  {detail}" if detail else ""))
        return passed

    def check_control(self, name, passed, detail=""):
        return self.check(name, passed, detail, kind="control")

    def note(self, text):
        print(f"    . {text}")

    def finding(self, text):
        self.findings.append(text)
        print(f"  [NOTE] {text}")

    def figure(self, path):
        self.figures.append(path)
        print(f"  [FIG ] {path}")
        return path

    @property
    def failed(self):
        return [r for r in self.rows if not r[2]]

    def summary(self, exit_on_failure=True):
        n_checks = sum(1 for r in self.rows if r[0] == "check")
        n_controls = sum(1 for r in self.rows if r[0] == "control")
        n_bad = len(self.failed)
        print(f"\n  {n_checks} acceptance checks, {n_controls} controls, {n_bad} failed")
        for _, name, _, detail in self.failed:
            print(f"    FAILED: {name}  --  {detail}")
        if self.figures:
            print("  figures:")
            for f in self.figures:
                print(f"    {f}")
        ok = n_bad == 0
        if not ok and exit_on_failure:
            sys.exit(1)
        return ok
