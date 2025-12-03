"""In-memory store for reference bundles and regions."""
from typing import Dict, List, TYPE_CHECKING

from models.reference_bundle import ReferenceBundle
from models.region import Region

if TYPE_CHECKING:
    from models.annotations import ReferenceAnnotations

# In-memory storage for reference bundles
REFERENCE_BUNDLES: Dict[str, ReferenceBundle] = {}

# In-memory storage for detected regions per reference
REFERENCE_REGIONS: Dict[str, List[Region]] = {}

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

