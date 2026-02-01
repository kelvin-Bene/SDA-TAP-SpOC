"""API integration module for UDL and other data sources."""

from .udl_publisher import (
    UDLPublisher,
    PublishResult,
    ValidationResult,
    DryRunReport,
    DataMode,
    UDLService,
    TIER_DATA_MODE_MAP,
    validate_payload,
    map_observation_to_udl,
    map_state_vector_to_udl,
    map_element_set_to_udl,
)

from .apiIntegration import (
    TLEToSV,
    UDLQuery,
    UDLToDatetime,
    UDLTokenGen,
    asyncUDLBatchQuery,
    datetimeToUDL,
    generateDataset,
    get_api_metrics,
    loadDataset,
    parseTLE,
    pullStates,
    reset_api_metrics,
    saveDataset,
    smart_query,
    spacetrackTokenGen,
)

# Open source data integrations (no auth required)
from .open_sources import (
    # SatNOGS (CC-BY-SA)
    satnogsQuery,
    satnogsGetSatellites,
    satnogsGetTransmitters,
    satnogsGetObservations,
    satnogsGetStations,
    # GCAT (CC-BY)
    gcatQuery,
    gcatGetSatelliteCatalog,
    gcatGetLaunches,
    gcatGetReentries,
    gcatLookupByNorad,
    # ILRS (Public Domain)
    ilrsGetSatellites,
    ilrsGetStations,
    ilrsQueryPredictions,
    # UCS Database (Open)
    ucsQuery,
    ucsLookupByNorad,
    ucsGetByCountry,
    ucsGetByPurpose,
    # Utilities
    enrichSatelliteData,
    getOpenSourceCatalogStats,
    clearOpenSourceCache,
)

# Data Source Manager (orchestrates open source integration)
from .data_source_manager import (
    DataSourceManager,
    EnrichmentReport,
    get_data_source_manager,
    HAMR_AMR_THRESHOLD,
)

__all__ = [
    # UDL Publisher (write integration)
    "UDLPublisher",
    "PublishResult",
    "ValidationResult",
    "DryRunReport",
    "DataMode",
    "UDLService",
    "TIER_DATA_MODE_MAP",
    "validate_payload",
    "map_observation_to_udl",
    "map_state_vector_to_udl",
    "map_element_set_to_udl",
    # Primary sources (existing)
    "UDLTokenGen",
    "spacetrackTokenGen",
    "UDLQuery",
    "asyncUDLBatchQuery",
    "generateDataset",
    "pullStates",
    "loadDataset",
    "saveDataset",
    "TLEToSV",
    "parseTLE",
    "datetimeToUDL",
    "UDLToDatetime",
    "smart_query",
    "get_api_metrics",
    "reset_api_metrics",
    # SatNOGS
    "satnogsQuery",
    "satnogsGetSatellites",
    "satnogsGetTransmitters",
    "satnogsGetObservations",
    "satnogsGetStations",
    # GCAT
    "gcatQuery",
    "gcatGetSatelliteCatalog",
    "gcatGetLaunches",
    "gcatGetReentries",
    "gcatLookupByNorad",
    # ILRS
    "ilrsGetSatellites",
    "ilrsGetStations",
    "ilrsQueryPredictions",
    # UCS
    "ucsQuery",
    "ucsLookupByNorad",
    "ucsGetByCountry",
    "ucsGetByPurpose",
    # Utilities
    "enrichSatelliteData",
    "getOpenSourceCatalogStats",
    "clearOpenSourceCache",
    # Data Source Manager
    "DataSourceManager",
    "EnrichmentReport",
    "get_data_source_manager",
    "HAMR_AMR_THRESHOLD",
]
