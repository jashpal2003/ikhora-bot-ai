"""Identity module."""

from relay.identity.models import CapabilityTier, MatchBasis, IdentityCandidate
from relay.identity.resolution import IdentityResolver

__all__ = ["CapabilityTier", "MatchBasis", "IdentityCandidate", "IdentityResolver"]
