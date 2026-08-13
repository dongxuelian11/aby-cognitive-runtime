"""Live P1.6 Y-Layer — parallel Dissipation Field (P0 V0.1 §5.3)."""

from ..contracts.frames import DissipationFrame
from ..providers.base import LLMProvider
from ..runtime.bundle import (
    LaneGenerationConfig,
    LaneStatus,
    YLaneExecutionResult,
    YProposal,
)
from ..runtime.lane_events import LaneName
from ..runtime.snapshot import RuntimeSnapshot
from .base import (
    Y_LANE_PROMPT,
    Y_LANE_PROMPT_SHA256,
    Y_LANE_PROMPT_VERSION,
    BaseLiveLane,
    proposal_common,
    result_usage,
)


class YLayer(BaseLiveLane):
    """Detects unresolved inconsistency and waste across A, B, memory, tools, and evidence.

    Y is NOT a third answer generator (P0 §5.3).

    Typical inputs: MacroFrame, ActionFrame, current event, memory evidence,
    tool evidence, prior episode state, execution trace.

    Output contract: DissipationFrame.

    Forbidden behavior (P0 §5.3):
    - Must not directly block execution.
    - Must not own final control authority.
    - Must not inflate y merely because information is incomplete.
    - Must distinguish normal uncertainty from harmful unresolved mismatch.
    - Must not recursively request unlimited verification.

    P0 §15: Y may be lightweight and frequent.
    """

    lane = LaneName.Y
    prompt = Y_LANE_PROMPT
    prompt_version = Y_LANE_PROMPT_VERSION
    prompt_hash = Y_LANE_PROMPT_SHA256

    def __init__(self, provider: LLMProvider) -> None:
        super().__init__(provider)

    def observe(
        self, snapshot: RuntimeSnapshot, generation: LaneGenerationConfig
    ) -> YLaneExecutionResult:
        raw = self._execute(snapshot, generation)
        common = result_usage(raw)
        if raw.failure is not None:
            return YLaneExecutionResult(
                status=LaneStatus.FAILED, failure=raw.failure, **common
            )
        if not isinstance(raw.frame, DissipationFrame):
            return YLaneExecutionResult(
                status=LaneStatus.FAILED,
                failure={"error_category": "Y_FRAME_TYPE_MISMATCH"},
                **common,
            )
        proposal = YProposal(
            frame=raw.frame,
            **proposal_common(
                raw,
                snapshot=snapshot,
                generation=generation,
                prompt_version=self.prompt_version,
                prompt_hash=self.prompt_hash,
            ),
        )
        return YLaneExecutionResult(
            status=LaneStatus.SUCCEEDED, proposal=proposal, **common
        )
