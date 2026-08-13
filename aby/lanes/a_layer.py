"""Live P1.6 A-Layer — Macro Boundary / Continuity (P0 V0.1 §5.1)."""

from ..contracts.frames import MacroFrame
from ..providers.base import LLMProvider
from ..runtime.bundle import (
    ALaneExecutionResult,
    AProposal,
    LaneGenerationConfig,
    LaneStatus,
)
from ..runtime.lane_events import LaneName
from ..runtime.snapshot import RuntimeSnapshot
from .base import (
    A_LANE_PROMPT,
    A_LANE_PROMPT_SHA256,
    A_LANE_PROMPT_VERSION,
    BaseLiveLane,
    proposal_common,
    result_usage,
)


class ALayer(BaseLiveLane):
    """Maintains long-horizon continuity without directly solving the current task.

    Mission (P0 §5.1): maintain the long-horizon state needed for continuity
    without directly solving the current task unless required for macro
    interpretation.

    Typical inputs: current event, long-term memory, persistent facts,
    previous accepted state, long-term goals, constraints, relationship
    history, world timeline, prior commitments, selected evidence.

    Output contract: MacroFrame.

    Forbidden behavior (P0 §5.1):
    - Must not emit the final user-facing answer as its primary function.
    - Must not receive the full B scratch context by default.
    - Must not invent long-term state when evidence is missing.
    - Must not silently overwrite persistent memory.

    P0 §15: A may be slower and event-triggered.
    """

    lane = LaneName.A
    prompt = A_LANE_PROMPT
    prompt_version = A_LANE_PROMPT_VERSION
    prompt_hash = A_LANE_PROMPT_SHA256

    def __init__(self, provider: LLMProvider) -> None:
        super().__init__(provider)

    def produce(
        self, snapshot: RuntimeSnapshot, generation: LaneGenerationConfig
    ) -> ALaneExecutionResult:
        raw = self._execute(snapshot, generation)
        common = result_usage(raw)
        if raw.failure is not None:
            return ALaneExecutionResult(
                status=LaneStatus.FAILED, failure=raw.failure, **common
            )
        if not isinstance(raw.frame, MacroFrame):
            return ALaneExecutionResult(
                status=LaneStatus.FAILED,
                failure={"error_category": "A_FRAME_TYPE_MISMATCH"},
                **common,
            )
        proposal = AProposal(
            frame=raw.frame,
            **proposal_common(
                raw,
                snapshot=snapshot,
                generation=generation,
                prompt_version=self.prompt_version,
                prompt_hash=self.prompt_hash,
            ),
        )
        return ALaneExecutionResult(
            status=LaneStatus.SUCCEEDED, proposal=proposal, **common
        )
