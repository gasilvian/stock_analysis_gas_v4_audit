"""Single source of truth for recommendation-language guardrail tokens.

P1.0 consolidation. Prior to this module, the FORBIDDEN_RECOMMENDATION_TOKENS
list was duplicated verbatim in four modules (investment_memo, workflow_package,
run_comparison, release manifest). Duplication risked silent divergence: a token
added in one surface but forgotten in another would weaken the no-investment-
advice guardrail. All surfaces must import from this module.

Governance rules served by this module (non-negotiable):
- No BUY / SELL / HOLD language in any product surface.
- No investment recommendation language.

Matching convention: callers are expected to scan a text padded with leading
and trailing spaces (f" {text} ") so the word-boundary tokens like " BUY "
match at the beginning/end of the text as well. `find_recommendation_tokens`
applies this padding itself.
"""
from __future__ import annotations

# NOTE: order and exact spelling are part of the guardrail contract; several
# offline tests snapshot behavior against these tokens. Add new tokens at the
# end. Never remove tokens without an explicit governance decision.
FORBIDDEN_RECOMMENDATION_TOKENS: list[str] = [
    " BUY ",
    " SELL ",
    " HOLD ",
    "BUY/SELL/HOLD",
    "Buy rating",
    "Sell rating",
    "Hold rating",
    "price target",
    "target price",
    "recommendation to",
    "overweight recommendation",
    "underweight recommendation",
    "rebalance into",
]


def find_recommendation_tokens(text: str) -> list[str]:
    """Return the raw forbidden tokens found in ``text`` (padded scan)."""
    padded = f" {text} "
    return [token for token in FORBIDDEN_RECOMMENDATION_TOKENS if token in padded]


def contains_recommendation_language(text: str) -> bool:
    """True when any forbidden recommendation token appears in ``text``."""
    return bool(find_recommendation_tokens(text))
