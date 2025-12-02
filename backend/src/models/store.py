"""In-memory store for reference bundles and regions."""
from typing import Dict, List

from models.reference_bundle import ReferenceBundle
from models.region import Region

# In-memory storage for reference bundles
REFERENCE_BUNDLES: Dict[str, ReferenceBundle] = {}

# In-memory storage for detected regions per reference
REFERENCE_REGIONS: Dict[str, List[Region]] = {}

