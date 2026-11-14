"""Per-field classification.

Kind priority: dde (any formula segment hits a DDE token) > multi_formula
(two or more formula segments) > formula (exactly one) > safe (none).
"""

from collections import namedtuple

from . import dde, detect

Classification = namedtuple(
    "Classification",
    ["kind", "formula_count", "trigger", "dde_token"],
)


def classify_field(value):
    """Classify one raw field value."""
    formula_segments = detect.find_formula_segments(value)
    count = len(formula_segments)
    token = dde.find_dde_token([body for _, _, body in formula_segments])
    if token is not None:
        kind = "dde"
    elif count >= 2:
        kind = "multi_formula"
    elif count == 1:
        kind = "formula"
    else:
        kind = "safe"
    trigger = formula_segments[0][1] if formula_segments else None
    return Classification(
        kind=kind,
        formula_count=count,
        trigger=trigger,
        dde_token=token,
    )
