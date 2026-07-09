"""Axis scoring per SPEC v3.1 section 2.2 (UNKNOWN scoring policy).

score_raw = count(PASS), denominator fixed at 6, with NO implicit normalization.
The optional normalized-by-known-checks metric is not part of the runtime output."""
from collections import defaultdict

AXES = ("value", "future", "past", "health", "dividend")


def compute_axis_scores(checks) -> dict:
    by_axis = defaultdict(list)
    for c in checks:
        by_axis[c.axis].append(c)
    scores = {}
    for axis in AXES:
        axis_checks = by_axis.get(axis, [])
        n_pass = sum(1 for c in axis_checks if c.result == "PASS")
        n_fail = sum(1 for c in axis_checks if c.result == "FAIL")
        n_unknown = sum(1 for c in axis_checks if c.result == "UNKNOWN")
        known = n_pass + n_fail
        scores[axis] = {
            "score_raw": n_pass,
            "known_checks_count": known,
            "unknown_checks_count": n_unknown,
            "coverage_pct": round(known / 6.0, 4),
        }
    return scores
