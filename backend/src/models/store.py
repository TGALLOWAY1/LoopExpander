"""In-memory store for reference bundles and regions."""
from typing import Dict, List

from models.reference_bundle import ReferenceBundle
from models.region import Region

# In-memory storage for reference bundles
REFERENCE_BUNDLES: Dict[str, ReferenceBundle] = {}

# In-memory storage for detected regions per reference
REFERENCE_REGIONS: Dict[str, List[Region]] = {}

# In-memory storage for detected motifs per reference
# Maps reference_id -> (instances, groups)
REFERENCE_MOTIFS: Dict[str, tuple] = {}

# In-memory storage for detected call-response pairs per reference
REFERENCE_CALL_RESPONSE: Dict[str, List] = {}

# In-memory storage for detected fills per reference
REFERENCE_FILLS: Dict[str, List] = {}

