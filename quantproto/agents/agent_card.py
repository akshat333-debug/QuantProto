"""A2A Agent Card specification.

Each agent publishes a card describing its capabilities, endpoint, and auth.
Cards serialise to JSON for discovery.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class AgentCard:
    """A2A Agent Card.

    Attributes
    ----------
    name : human-readable agent name.
    description : what this agent does.
    capabilities : list of capability strings.
    endpoint : HTTP endpoint URL.
    auth_scheme : authentication scheme (e.g. "bearer_jwt").
    version : agent version.
    metadata : arbitrary extra fields.
    """

    name: str
    description: str
    capabilities: list[str]
    endpoint: str
    auth_scheme: str = "bearer_jwt"
    version: str = "0.1.0"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> str:
        """Serialise to JSON string."""
        return json.dumps(asdict(self), indent=2)

    def to_dict(self) -> dict[str, Any]:
        """Serialise to dict."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AgentCard":
        """Deserialise from dict."""
        return cls(**data)

    @classmethod
    def from_json(cls, json_str: str) -> "AgentCard":
        """Deserialise from JSON string."""
        return cls.from_dict(json.loads(json_str))
