"""Bounded integrity checks for repository-native ABY authority wiring.

The tests intentionally lock status tokens, navigation, and the frozen P0 byte
boundary. They do not freeze full authority prose, so later versioned doctrine
can evolve without copying an entire document into a test.
"""

from hashlib import sha256
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
AUTHORITY_DIR = REPO_ROOT / "docs" / "authority"

AUTHORITY_FILES = (
    "README.md",
    "ABY_PROJECT_DOCTRINE_V0_1.md",
    "ABY_TARGET_ARCHITECTURE_P1_HYPOTHESIS_V0_1.md",
    "ABY_PHASE_GATES_AND_ROADMAP_V0_1.md",
)

AGENT_REQUIRED_DOCS = (
    "docs/authority/README.md",
    "docs/authority/ABY_PROJECT_DOCTRINE_V0_1.md",
    "docs/authority/ABY_TARGET_ARCHITECTURE_P1_HYPOTHESIS_V0_1.md",
    "docs/authority/ABY_PHASE_GATES_AND_ROADMAP_V0_1.md",
)

P0_FROZEN_SHA256 = {
    "ABY_P0_THEORY_FREEZE_EXPERIMENTAL_ARCHITECTURE_V0_1.md":
        "0900350395d44ba478990af47686ecdab5a8c7918fd2a377ced5303ff72984d4",
    "CHANGELOG.md":
        "6f2d3da76965dd0dca5d1666952c93d38bdea3e127c4bc1e97296302a50bb594",
    "P0_ACCEPTANCE_TRACKER.md":
        "ebab3f12155a5334cd32d914b3c8afb8fec141f0af32b22f27b75246c083d93f",
}


def read_repo_text(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def test_root_agents_exists_is_concise_and_wires_canonical_authority():
    agents_path = REPO_ROOT / "AGENTS.md"
    assert agents_path.is_file()
    agents = agents_path.read_text(encoding="utf-8")
    assert len(agents.splitlines()) <= 80
    for required_doc in AGENT_REQUIRED_DOCS:
        assert required_doc in agents
    for required_rule in (
        "TASK_GOAL",
        "TASK_PROGRESS",
        "FAIL CLOSED",
        "exact Git/GitHub state",
    ):
        assert required_rule in agents


def test_canonical_authority_files_exist():
    for filename in AUTHORITY_FILES:
        assert (AUTHORITY_DIR / filename).is_file()


def test_project_doctrine_preserves_stable_semantic_boundaries():
    doctrine = read_repo_text(
        "docs/authority/ABY_PROJECT_DOCTRINE_V0_1.md"
    )
    for token in (
        "FALSIFIABILITY: FIRST",
        "A/B/Y != a/b/y",
        "qA/qB/qY != a/b/y",
        "y_hat != y_obs",
        "r_c = w_A / w_B",
        "r_o = a / b",
    ):
        assert token in doctrine


def test_target_architecture_status_and_pipeline_are_explicit():
    target = read_repo_text(
        "docs/authority/ABY_TARGET_ARCHITECTURE_P1_HYPOTHESIS_V0_1.md"
    )
    for status in (
        "GEODESIC_COORDINATION_HYPOTHESIS",
        "EXPERIMENTAL",
        "NOT_P0_AUTHORITY",
        "NOT_SCIENTIFICALLY_VALIDATED",
    ):
        assert status in target
    for concept in (
        "Semantic Atomizer",
        "Shared Semantic Manifold / Atlas",
        "Y Dissipation Geometry",
        "Minimum-Dissipation Geodesic Resolver",
        "Commit Barrier",
    ):
        assert concept in target


def test_roadmap_locks_accepted_baselines_and_future_p1_5_gate():
    roadmap = read_repo_text(
        "docs/authority/ABY_PHASE_GATES_AND_ROADMAP_V0_1.md"
    )
    for marker in (
        "P1.2_STATUS: ACCEPTED",
        "P1.3_STATUS: ACCEPTED",
        "P1.4_STATUS: ACCEPTED",
        "P1.5_STATUS: NOT_STARTED",
        "PRE-P1.5 RUNTIME HARDENING",
    ):
        assert marker in roadmap


def test_historical_s3_skeleton_is_unmistakably_non_authoritative():
    skeleton = read_repo_text("experiments/configs/example_s3_aby_fixed.yaml")
    for marker in (
        "DEPRECATED_EARLY_P1_S3_SKELETON",
        "NOT_CURRENT_ARCHITECTURE_AUTHORITY",
        "DO_NOT_IMPLEMENT_S3_FROM_THIS_FILE",
    ):
        assert marker in skeleton


def test_frozen_p0_directory_remains_byte_identical():
    p0_dir = REPO_ROOT / "docs" / "p0"
    assert {path.name for path in p0_dir.iterdir() if path.is_file()} == set(
        P0_FROZEN_SHA256
    )
    for filename, expected in P0_FROZEN_SHA256.items():
        assert sha256((p0_dir / filename).read_bytes()).hexdigest() == expected
