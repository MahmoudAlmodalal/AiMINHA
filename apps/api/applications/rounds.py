"""Reviewed round labels are identity; ambiguous identities fail closed.

ASSUMPTION: a normalized distinct reviewed label identifies a round across date
revisions. A sole unlabeled round has one stable key, never an invented year.
"""

import hashlib
import unicodedata
from typing import Any

from identity.security import IdentityError

UNKNOWN_ROUND = {
    "kind": "UNKNOWN",
    "label": "",
    "source_text": "",
    "closes_at": None,
    "deadline_date": None,
    "timezone": None,
}


def round_options(rounds: list[dict[str, Any]]) -> list[dict[str, Any]]:
    values = rounds or [UNKNOWN_ROUND.copy()]
    labels = [
        unicodedata.normalize("NFC", row.get("label", "")).strip().casefold() for row in values
    ]
    if len(set(labels)) != len(labels) or (len(values) > 1 and "" in labels):
        raise IdentityError("ROUND_IDENTITY_UNAVAILABLE", 503, "Round labels need source review")
    return [
        {
            **row,
            "round_key": hashlib.sha256(
                ("label:" + label if label else "single-unlabeled-round").encode()
            ).hexdigest(),
        }
        for row, label in zip(values, labels, strict=True)
    ]
