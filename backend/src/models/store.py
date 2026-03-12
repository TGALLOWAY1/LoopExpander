"""In-memory store for reference bundles and regions."""
from typing import Dict, List, TYPE_CHECKING

from models.reference_bundle import ReferenceBundle
from models.reference_mix import ReferenceMix
from models.region import Region
from models.role_activity import RoleActivityTimeline
from models.interaction_label import InteractionLabel
from models.user_loop import UserLoopBundle
from arrangement.models import Arrangement

if TYPE_CHECKING:
    from models.annotations import ReferenceAnnotations

# In-memory storage for reference bundles
REFERENCE_BUNDLES: Dict[str, ReferenceBundle] = {}

# In-memory storage for single full-mix reference tracks
REFERENCE_MIXES: Dict[str, ReferenceMix] = {}

# In-memory storage for role activity timelines per reference
REFERENCE_ROLE_ACTIVITY: Dict[str, List[RoleActivityTimeline]] = {}

# In-memory storage for energy curves per reference
REFERENCE_ENERGY_CURVES: Dict[str, dict] = {}

# In-memory storage for detected regions per reference
REFERENCE_REGIONS: Dict[str, List[Region]] = {}

# In-memory storage for tonal balance per reference
# Maps reference_id -> list of RegionTonalBalance dicts
REFERENCE_TONAL_BALANCE: Dict[str, List[dict]] = {}

# In-memory storage for detected motifs per reference
# Maps reference_id -> (instances, groups)
REFERENCE_MOTIFS: Dict[str, tuple] = {}

# In-memory storage for raw motif instances (before clustering) per reference
# Maps reference_id -> list[MotifInstance] (raw instances with features but no group_id)
REFERENCE_MOTIF_INSTANCES_RAW: Dict[str, List] = {}

# In-memory storage for detected call-response pairs per reference
REFERENCE_CALL_RESPONSE: Dict[str, List] = {}

# In-memory storage for detected fills per reference
REFERENCE_FILLS: Dict[str, List] = {}

# In-memory storage for computed subregions per reference
# Maps reference_id -> list[RegionSubRegions]
REFERENCE_SUBREGIONS: Dict[str, List] = {}

# In-memory storage for Visual Composer annotations per reference
# Maps reference_id -> ReferenceAnnotations
REFERENCE_ANNOTATIONS: Dict[str, "ReferenceAnnotations"] = {}

# In-memory storage for interaction labels per reference
# Maps reference_id -> list[InteractionLabel]
INTERACTION_LABELS: Dict[str, List[InteractionLabel]] = {}

# In-memory storage for user loop bundles per reference/project
# Maps project_id (reference_id) -> UserLoopBundle
USER_LOOPS: Dict[str, UserLoopBundle] = {}

# In-memory storage for generated arrangements per project
# Maps project_id (reference_id) -> Arrangement
ARRANGEMENTS: Dict[str, Arrangement] = {}

# In-memory storage for variation suggestions per project
# Maps project_id -> list[VariationSuggestion]
VARIATION_SUGGESTIONS: Dict[str, List] = {}

# In-memory storage for guidance messages per project
# Maps project_id -> list[GuidanceMessage]
GUIDANCE_MESSAGES: Dict[str, List] = {}

# In-memory storage for guide markers per project
# Maps project_id -> list[GuideMarker]
GUIDE_MARKERS: Dict[str, List] = {}

