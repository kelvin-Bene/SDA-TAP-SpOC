# UDL v1.39.0 Impact Analysis on UCT Benchmark

**Date:** 2026-03-31
**Release Window:** April 2026 (exact date TBD — follow-up notice expected)

## How Our App Uses UDL

1. **Token validation** (`token_validation.py`) — validates user-provided UDL API tokens by making test requests to the UDL API
2. **Observation data fetching** (`datasets.py` / generation pipeline) — queries UDL for space object observations to build benchmark datasets
3. **Dataset generation** — pulls observation data filtered by regime (LEO/MEO/GEO/HEO), sensor type, coverage level, and object count
4. **Frontend** — stores/manages UDL tokens per user, lets users configure and generate datasets

## Impact Assessment by Release Item

| Release Item | Impact on Our App | Severity | Action Needed |
|---|---|---|---|
| **SensorMetrics (new service)** | No impact. We don't query sensor metrics. Could be a future enhancement opportunity for benchmarking sensor performance. | NONE | Optional: consider using MoM data for benchmark quality scoring |
| **StateVector: new `missionCenter` field** | Low impact. If we consume state vectors, there's a new optional field. Won't break anything — it's additive. | LOW | Update any state vector data models if we want to capture this field |
| **PassiveRadarObservation: new fields** | Potentially relevant. If our observation queries include passive radar data, new fields (`senReferenceFrame`, `senx/y/z`) will appear in responses. Won't break existing code (additive), but our schemas might not capture the new data. | LOW | Review if observation ingestion handles unknown fields gracefully |
| **SensorCharacteristics: 10 new fields + 30+ updated descriptions** | Potentially relevant. If we use sensor characteristics to filter or classify sensors for dataset generation, the new fields (settle time, tracking params, data formats) could enhance benchmarking. | LOW | No breaking change; optional enhancement |
| **RFObservationDetails: `jamBands` and `jamToSigRatios`** | Low. Additive fields. Only matters if we process RF observations. | LOW | None unless we process RF obs |
| **StarCatalog: `neighborId` Integer to Long** | Potentially breaking if we parse this field. If our code casts `neighborId` to a 32-bit int, values exceeding 2^31 will overflow. | MEDIUM | Check if we consume StarCatalog data and handle Long types |
| **CurrentElsets: query by `ephType`, `algorithm`, `origin`** | Useful enhancement. If our dataset generation queries elsets, we can now filter more precisely. No breaking change. | LOW | Optional: leverage new query params for better dataset filtering |
| **RF signal max file size to 30MB** | No impact (we don't upload RF signals). | NONE | None |
| **SensorMaintenance `inactiveDate` behavior** | No impact unless we track sensor maintenance windows. | NONE | None |
| **429 rate limit responses on POST endpoints** | **IMPORTANT.** If our dataset generation pipeline makes POST requests to UDL, we now need to handle HTTP 429 (Too Many Requests) responses. Our `_request_with_retry` currently only retries on `Timeout` and `ConnectionError` — it does NOT retry on 429. | **HIGH** | **Must update `_request_with_retry` to handle 429 with backoff** |
| **Video Streaming service removed** | No impact (we don't use it). | NONE | None |
| **Storefront changes** | No impact (UI-only on UDL's side). | NONE | None |

## Future Updates (Heads-Up Items)

| Future Item | Impact | Action |
|---|---|---|
| **GeoJSON validation (RFC 7946)** | If we submit any GeoJSON fields (geography, regionGeoJSON, etc.), malformed GeoJSON will be rejected. Need to verify our payloads comply. | Audit any GeoJSON we send to UDL |
| **Launch APIs rework** | No impact unless we use LaunchEvent/DISOBEquipment. | None |
| **FlightPlan `estDepTime` required** | No impact unless we query flight plans. | None |
| **SCS V1 to V2 migration** | If we use Secure Content Store for file storage/retrieval, V1 endpoints will be removed. | Check if we use SCS endpoints |
| **UTC timestamp validation (require 'Z' offset)** | Potentially breaking. If any timestamps we submit to UDL don't include the 'Z' suffix (e.g., `2026-03-30T12:00:00` instead of `2026-03-30T12:00:00Z`), they'll be rejected. | **Audit all timestamp formatting in our API calls** |
| **Notification to Status topic migration** | Only relevant if we use UDL's messaging/notification system. | Check if applicable |

## Top 3 Action Items (Priority Order)

### 1. HIGH — Handle 429 rate limiting
The new 429 responses on POST endpoints mean our `_request_with_retry` in `token_validation.py` (and any dataset generation code that POSTs to UDL) needs to detect HTTP 429 and retry with exponential backoff + respect `Retry-After` headers. Currently we only retry on network errors, not HTTP status codes.

### 2. MEDIUM — Audit timestamp formatting
The upcoming strict UTC validation (`Z` offset required) is a future breaking change. We should proactively ensure all timestamps we send include the `Z` suffix.

### 3. LOW — Brief service outage during upgrade
During the actual maintenance window, dataset generation will fail. Our stuck-dataset cleanup (the 15-minute timeout) should handle this gracefully — any generation in progress during the outage will auto-fail and users can retry. No code change needed, but worth noting for users.

## What Won't Break

- All schema additions are **additive** (new optional fields) — our existing queries won't break
- We don't use Video Streaming, Launch APIs, FlightPlan, or SCS, so those removals/changes don't affect us
- The Storefront UI changes are on UDL's platform, not our API integration

## Bottom Line

The only **immediate action item** is adding 429 handling to our retry logic. The rest is either additive/non-breaking or future warnings we should plan for.
