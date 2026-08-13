"""P1.5 Shared Semantic Geometry Foundation (experimental candidate)."""

from .artifacts import (
    SEMANTIC_ARTIFACT_FILENAMES,
    SemanticArtifactSet,
    semantic_geometry_artifact_dir,
    write_semantic_geometry_artifacts,
)
from .atlas import (
    MAX_ATLAS_K,
    SEMANTIC_ATLAS_VERSION,
    SemanticAtlas,
    SemanticAtlasEdge,
    build_directed_knn_atlas,
)
from .atomizer import FrameAtomizer
from .bundle import (
    SEMANTIC_GEOMETRY_BUNDLE_SCHEMA_VERSION,
    SemanticGeometryBundle,
    build_semantic_geometry_bundle,
)
from .encoder import (
    REFERENCE_ENCODER_ID,
    REFERENCE_ENCODER_REVISION,
    REFERENCE_ENCODER_STATUS,
    DeterministicHashingEncoder,
    EncoderProvenance,
    SharedEncoder,
)
from .geometry import (
    SPHERICAL_METRIC_VERSION,
    SemanticPoint,
    cosine_similarity,
    dot_product,
    encode_semantic_atoms,
    normalize_vector,
    spherical_distance,
)
from .ir import (
    SEMANTIC_ATOM_SCHEMA_VERSION,
    SemanticAtom,
    SemanticAtomType,
    SourceLane,
    semantic_atom_id,
)
from .matcher import SemanticMatchCandidate, match_cross_lane_candidates

__all__ = [name for name in globals() if not name.startswith("_")]
