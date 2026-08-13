"""Live P1.6 B-Layer — Micro Direction / Action (P0 V0.1 §5.2)."""

from ..contracts.frames import ActionFrame
from ..providers.base import LLMProvider
from ..runtime.bundle import (
    BLaneExecutionResult,
    BProposal,
    LaneGenerationConfig,
    LaneStatus,
)
from ..runtime.lane_events import LaneName
from ..runtime.snapshot import RuntimeSnapshot
from .base import (
    B_LANE_PROMPT,
    B_LANE_PROMPT_SHA256,
    B_LANE_PROMPT_VERSION,
    BaseLiveLane,
    proposal_common,
    result_usage,
)


class BLayer(BaseLiveLane):
    """Solves the immediate task with local context, tools, and minimum macro constraints.

    Mission (P0 §5.2): solve the immediate task using current input, local
    context, tools, and only the minimum macro constraints required.

    Typical inputs: current user request or event, current task, available
    tools, local working context, selected constraints from A, relevant evidence.

    Output contract: ActionFrame.

    Forbidden behavior (P0 §5.2):
    - Must not load all historical memory by default.
    - Must not autonomously redefine long-term goals.
    - Must not treat stale memory as current authority.
    - Must not use A's uncertainty as permission to fabricate.

    P0 §15: B is typically highest-frequency.
    """

    lane = LaneName.B
    prompt = B_LANE_PROMPT
    prompt_version = B_LANE_PROMPT_VERSION
    prompt_hash = B_LANE_PROMPT_SHA256

    def __init__(self, provider: LLMProvider) -> None:
        super().__init__(provider)

    def produce(
        self, snapshot: RuntimeSnapshot, generation: LaneGenerationConfig
    ) -> BLaneExecutionResult:
        raw = self._execute(snapshot, generation)
        common = result_usage(raw)
        if raw.failure is not None:
            return BLaneExecutionResult(
                status=LaneStatus.FAILED, failure=raw.failure, **common
            )
        if not isinstance(raw.frame, ActionFrame):
            return BLaneExecutionResult(
                status=LaneStatus.FAILED,
                failure={"error_category": "B_FRAME_TYPE_MISMATCH"},
                **common,
            )
        proposal = BProposal(
            frame=raw.frame,
            **proposal_common(
                raw,
                snapshot=snapshot,
                generation=generation,
                prompt_version=self.prompt_version,
                prompt_hash=self.prompt_hash,
            ),
        )
        return BLaneExecutionResult(
            status=LaneStatus.SUCCEEDED, proposal=proposal, **common
        )
