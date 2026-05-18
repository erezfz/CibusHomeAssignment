"""Unit tests for domain-level value objects and enum helpers."""

import pytest

from domains.models import VoteSelection


def test_vote_selection_internal_value_mapping() -> None:
    """Ensure external vote enum values map to expected internal integer representation."""
    assert VoteSelection.UP.internal_value == 1
    assert VoteSelection.DOWN.internal_value == -1


def test_vote_selection_from_internal_value_roundtrip() -> None:
    """Ensure internal integer values map back into public vote enum values."""
    assert VoteSelection.from_internal_value(1) == VoteSelection.UP
    assert VoteSelection.from_internal_value(-1) == VoteSelection.DOWN


def test_vote_selection_from_internal_value_invalid_raises_value_error() -> None:
    """Ensure unsupported internal vote values raise a clear ValueError."""
    with pytest.raises(ValueError, match="Invalid vote selection"):
        VoteSelection.from_internal_value(0)
