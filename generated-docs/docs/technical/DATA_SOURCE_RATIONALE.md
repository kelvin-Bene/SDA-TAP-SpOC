# Data Source Rationale

<!-- AI_METADATA
purpose: Document WHY each data source was chosen with trade-offs and alternatives
status: active
related_files: [planning/DECISION_LOG.md, planning/FUTURE_IMPLEMENTATIONS.md, technical/DATA_SOURCES.md]
last_updated: 2026-02-03
-->

This document explains the rationale behind data source selection for the UCT Benchmark project. It covers why certain sources were chosen, why others were excluded, and the trade-offs considered.

---

## Guiding Principles

Data source selection follows these principles (in order of priority):

1. **Open-source compatibility** - Data must be redistributable
2. **Functional value** - Must improve evaluation accuracy or dataset realism
3. **Integration simplicity** - Prefer low-effort, high-value integrations
4. **Independence** - Prefer sources that provide unique data not available elsewhere

Per [Decision 1 in the Decision Log](../planning/DECISION_LOG.md#decision-1-external-data-provider-registration):
> Starting with fully open sources makes sense for an open-source project. Can revisit registration-required sources later if needed.

---

<!-- AI_SECTION: current_primary_sources -->

## 1. Current Primary Sources

### 1.1 UDL (Unified Data Library)

**URL**: https://unifieddatalibrary.com
**Status**: Primary source (integrated)
**Auth**: Base64 token

**Why Selected**:
- Primary U.S. Space Force repository for space domain awareness data
- Comprehensive observation data (observations, state vectors, TLEs, conjunctions)
- High update frequency
- Official government data source

**Trade-offs**:
- Requires authentication (not fully open)
- Limited to U.S. government-approved data
- API rate limits apply

**Used For**: Primary observation data, state vectors, reference TLEs

---

### 1.2 Space-Track.org

**URL**: https://www.space-track.org
**Status**: Integrated
**Auth**: Account required

**Why Selected**:
- Official source for historical TLE data
- Comprehensive satellite catalog
- Well-documented API
- Standard reference for space surveillance

**Trade-offs**:
- Requires account registration
- Rate-limited API
- Some data restricted by classification

**Used For**: Historical TLEs, satellite catalog supplementation

---

### 1.3 CelesTrak

**URL**: https://celestrak.org
**Status**: Integrated
**Auth**: None required

**Why Selected**:
- No authentication required
- Real-time TLE updates
- Curated satellite categories (active, debris, etc.)
- Supplementary Object Metadata (SATCAT)
- Widely used in academic and commercial applications

**Trade-offs**:
- Derived from Space-Track (not independent source)
- Limited historical data
- No observation data (TLEs only)

**Used For**: Current TLEs, SATCAT catalog data

---

### 1.4 ESA DiscoWeb

**URL**: https://discosweb.esoc.esa.int
**Status**: Integrated
**Auth**: Bearer token

**Why Selected**:
- Physical properties data (mass, cross-sectional area)
- Required for accurate force modeling
- Independent European source
- Complements U.S. sources

**Trade-offs**:
- Requires token authentication
- Limited to objects ESA tracks
- Update frequency varies

**Used For**: Satellite physical properties (mass, area) for propagation

<!-- /AI_SECTION -->

---

<!-- AI_SECTION: planned_sources -->

## 2. Planned Sources (with Rationale)

### 2.1 SatNOGS

**URL**: https://satnogs.org
**Status**: Planned (high priority)
**Auth**: None required
**License**: CC-BY-SA

**Why Selected**:
- **Completely open source** - No authentication barriers
- Real RF observation data with timestamps
- 200+ operational ground stations worldwide
- Community-validated data quality
- Used by ESA for operational missions

**UCT Challenges Addressed**:
- Long periods between tracks (multi-station coverage)
- Poor sensor calibration (cross-validation source)
- Real observation timestamps for simulation validation

**Trade-offs**:
- RF observations, not optical (different modality)
- Variable data quality (community-contributed)
- Not all satellites covered

**Planned Use**: Validation source for simulated observations, real observation timestamp reference

---

### 2.2 GCAT (General Catalog of Artificial Space Objects)

**URL**: https://planet4589.org/space/gcat/
**Status**: Planned (high priority)
**Auth**: None required
**License**: CC-BY

**Why Selected**:
- **Comprehensive catalog** - 57,000+ objects
- Includes objects not in U.S. catalog
- Complete launch history
- Object type classification
- Maintained by respected expert (Dr. Jonathan McDowell, Harvard-Smithsonian)

**UCT Challenges Addressed**:
- Objects in close angular space (more complete catalog)
- Unknown target characteristics (classification data)

**Trade-offs**:
- Weekly updates (not real-time)
- Catalog only (no observations)

**Planned Use**: Catalog supplementation, launch history, object classification

---

### 2.3 ILRS (International Laser Ranging Service)

**URL**: https://ilrs.gsfc.nasa.gov
**Status**: Planned (high priority)
**Auth**: NASA CDDIS access
**License**: Open

**Why Selected**:
- **Highest precision tracking data available** (millimeter-level)
- 100+ satellites tracked across all regimes
- Independent validation source
- Ground-truth for orbit accuracy assessment

**UCT Challenges Addressed**:
- Small orbital arc observed (precision reference)
- Unknown target characteristics (calibrated orbits)
- Poor sensor calibration (cross-validation)

**Trade-offs**:
- Requires NASA Earthdata credentials
- Limited to retroreflector-equipped satellites
- Complex data formats

**Planned Use**: Ground-truth for evaluation metrics, propagator accuracy validation, covariance calibration

**Decision Pending**: Focus on LEO, GNSS, or Geodetic satellites - see [DECISION_LOG.md](../planning/DECISION_LOG.md#decision-2-ilrs-precision-validation-focus)

---

### 2.4 UCS Satellite Database

**URL**: https://www.ucs.org/resources/satellite-database
**Status**: Planned (medium priority)
**Auth**: None required
**License**: Open

**Why Selected**:
- Comprehensive operational satellite metadata
- 7,560+ satellites with 28 data fields each
- Mission purpose classification
- Technical specifications (mass, power, lifetime)

**UCT Challenges Addressed**:
- Unknown target characteristics (metadata enrichment)
- High area-to-mass ratio objects (mass data)

**Trade-offs**:
- Operational satellites only (no debris)
- Quarterly updates

**Planned Use**: Satellite metadata enrichment, mission classification

<!-- /AI_SECTION -->

---

<!-- AI_SECTION: excluded_sources -->

## 3. Sources Explicitly Excluded (with Reasoning)

### 3.1 LeoLabs

**URL**: https://leolabs.space
**Status**: Excluded
**Reason**: Commercial/proprietary

**What It Offers**:
- Commercial radar tracking network
- Debris down to 2cm size
- High-quality ephemerides

**Why Excluded**:
- Commercial subscription required
- Data cannot be redistributed
- Conflicts with open-source project goals
- Only 14-day free trial available

**Alternative Approach**: Use public visualization for manual validation if needed

---

### 3.2 Vimpel (Russian Space Catalog)

**URL**: http://spacedata.vimpel.ru
**Status**: Deferred
**Reason**: Registration required (per Decision 1)

**What It Offers**:
- Alternative space object catalog (independent from U.S.)
- Strong GEO/HEO coverage
- Debris objects not in U.S. catalog

**Why Deferred**:
- Registration required with User Agreement
- Citation requirements for publications
- Geopolitical considerations

**Future Consideration**: May revisit if independent GEO/HEO validation becomes critical

---

### 3.3 EU SST (European Space Surveillance and Tracking)

**URL**: https://www.eusst.eu
**Status**: Deferred
**Reason**: Operator registration required (per Decision 1)

**What It Offers**:
- Collision avoidance warnings
- Re-entry analysis
- European catalog data

**Why Deferred**:
- Requires operator registration
- Service-oriented (not raw data)
- Focus is collision avoidance, not UCT benchmarking

**Future Consideration**: May revisit if European conjunction data becomes valuable

---

### 3.4 COMSPOC (Commercial Space Operations Center)

**Status**: Not evaluated
**Reason**: Commercial service

**What It Offers**:
- Commercial space traffic management
- Enhanced tracking data

**Why Not Evaluated**:
- Commercial service requiring contract
- Data redistribution restrictions expected
- Beyond project scope

<!-- /AI_SECTION -->

---

## 4. Integration Priority Decision

Based on the rationale above, the recommended integration priority is:

### Tier 1: Immediate (Low Effort, High Value, Fully Open)
1. **GCAT** - Comprehensive catalog, CC-BY license, TSV download
2. **UCS Database** - Metadata enrichment, no auth, free download
3. **ccsds-ndm library** - Standard format parsing, open source tool

### Tier 2: Short-term (Medium Effort, High Value)
4. **SatNOGS** - Real observations, fully open API, CC-BY-SA
5. **ILRS** - Precision validation (requires NASA CDDIS setup)

### Tier 3: Future Consideration
6. **TraCSS** - Evaluate now that it's in production
7. **Vimpel/EU SST** - Only if independent validation becomes critical

---

## 5. Data Source Mapping to UCT Challenges

| UCT Challenge | Current Sources | Planned Sources |
|---------------|-----------------|-----------------|
| High area-to-mass ratio objects | ESA DiscoWeb (mass) | UCS Database |
| Long periods between tracks | UDL observations | SatNOGS (multi-station) |
| Very few tracks | UDL, Space-Track | GCAT (more objects) |
| Small orbital arc observed | State vectors | ILRS (precision reference) |
| Objects in close angular space | CelesTrak SATCAT | GCAT (comprehensive) |
| Unknown target characteristics | DiscoWeb | UCS Database |
| Poor sensor calibration | Multi-source comparison | SatNOGS, ILRS |

---

## Related Documents

- [DECISION_LOG.md](../planning/DECISION_LOG.md) - Strategic decisions
- [FUTURE_IMPLEMENTATIONS.md](../planning/FUTURE_IMPLEMENTATIONS.md) - Planned integrations
- [DATA_SOURCES.md](DATA_SOURCES.md) - Technical integration details
- [Archive: RESEARCH_SPACE_DATA_SOURCES.md](../archive/RESEARCH_SPACE_DATA_SOURCES.md) - Original research

---

*Created 2026-02-03 by synthesizing archived research documents*
