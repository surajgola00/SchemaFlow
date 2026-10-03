"""DAG nodes registry."""
from app.services.executor.nodes.base import BaseNode, NodeResult
from app.services.executor.nodes.core_nodes import (
    DedupeNode,
    DiscoverSourcesNode,
    EnrichNode,
    ExtractNode,
    FetchNode,
    FinalizeNode,
    NormalizeNode,
    ScoreNode,
    ValidateNode,
)

NODE_REGISTRY: dict[str, BaseNode] = {
    "discover_sources": DiscoverSourcesNode(),
    "fetch": FetchNode(),
    "extract": ExtractNode(),
    "normalize": NormalizeNode(),
    "validate": ValidateNode(),
    "dedupe": DedupeNode(),
    "enrich": EnrichNode(),
    "score": ScoreNode(),
    "finalize": FinalizeNode(),
}

__all__ = [
    "BaseNode",
    "NodeResult",
    "NODE_REGISTRY",
    "DiscoverSourcesNode",
    "FetchNode",
    "ExtractNode",
    "NormalizeNode",
    "ValidateNode",
    "DedupeNode",
    "ScoreNode",
    "FinalizeNode",
    "EnrichNode",
]
