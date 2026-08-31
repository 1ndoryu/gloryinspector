"""Use-case facade for response classification."""

from .core.classification import Classification, classify_response

__all__ = ["Classification", "classify_response"]
