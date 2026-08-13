"""P1.6 ABY Parallel Runtime implementation candidate.

This package ends at parallel proposals plus an optional accepted P1.5 geometry
handoff. It contains no Resolver, geodesic, Commit Barrier, tools, or authority
mutation path.
"""

from .bundle import (
    ABY_PARALLEL_RUNTIME_SCHEMA_VERSION,
    ABYParallelRuntimeConfig,
    ABYParallelRuntimeResult,
    LaneGenerationConfig,
    LaneStatus,
    RuntimeStatus,
    SemanticGeometryRuntimeConfig,
)
from .lane_events import LaneEvent, LaneEventBuffer, LaneName, merge_lane_events
from .parallel import ABYParallelRuntime
from .snapshot import RUNTIME_SNAPSHOT_SCHEMA_VERSION, RuntimeSnapshot, project_snapshot
from .structured_output import (
    LANE_STRUCTURED_OUTPUT_PROTOCOL,
    NATIVE_PROVIDER_SCHEMA_ENFORCEMENT,
    StructuredOutputError,
    parse_lane_frame,
)

__all__ = [name for name in globals() if not name.startswith("_")]
