"""Request parameter spell-checking for the AumOS Python SDK.

When callers pass unknown parameter names to SDK methods, this module
suggests the closest valid field name using difflib, matching the Stripe SDK pattern.

Example:
    client.agents.create(nme="foo")  # raises ValueError with "Did you mean 'name'?"
"""

from __future__ import annotations

import difflib
from typing import Any


def suggest_close_match(unknown_field: str, valid_fields: list[str]) -> str | None:
    """Find the closest valid field name for an unknown field.

    Uses difflib to find the closest match with a similarity threshold of 0.6.

    Args:
        unknown_field: The field name the caller passed.
        valid_fields: List of valid field names to check against.

    Returns:
        The closest matching field name, or None if no close match is found.
    """
    matches = difflib.get_close_matches(unknown_field, valid_fields, n=1, cutoff=0.6)
    return matches[0] if matches else None


def check_extra_fields(
    provided: dict[str, Any],
    valid_fields: list[str],
    model_name: str,
) -> None:
    """Raise a descriptive ValueError if any provided fields are not in valid_fields.

    Suggests close matches for typos rather than raising a generic error.

    Args:
        provided: The dictionary of fields the caller provided.
        valid_fields: List of valid field names for this model/endpoint.
        model_name: The model or endpoint name for error context.

    Raises:
        ValueError: If any provided field is not in valid_fields, with a close-match suggestion.
    """
    invalid = [key for key in provided if key not in valid_fields]
    if not invalid:
        return

    errors: list[str] = []
    for field in invalid:
        suggestion = suggest_close_match(field, valid_fields)
        if suggestion:
            errors.append(
                f"  '{field}' is not a valid field for {model_name}. "
                f"Did you mean '{suggestion}'?"
            )
        else:
            errors.append(
                f"  '{field}' is not a valid field for {model_name}. "
                f"Valid fields: {', '.join(sorted(valid_fields))}"
            )

    raise ValueError(
        f"Unknown parameter(s) passed to {model_name}:\n" + "\n".join(errors)
    )
