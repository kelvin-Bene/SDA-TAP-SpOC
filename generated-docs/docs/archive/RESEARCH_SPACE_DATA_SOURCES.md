# Space Tracking Data Sources Research

<!-- AI_METADATA
purpose: Archived research document on space data sources
status: archived
related_files: [planning/FUTURE_IMPLEMENTATIONS.md, technical/DATA_SOURCE_RATIONALE.md]
last_updated: 2026-02-03
archived_from: /RESEARCH_SPACE_DATA_SOURCES.md
archive_reason: Initial research document. Content synthesized into DATA_SOURCE_RATIONALE.md and FUTURE_IMPLEMENTATIONS.md
-->

> **ARCHIVED**: This research document has been synthesized into:
> - [DATA_SOURCE_RATIONALE.md](../technical/DATA_SOURCE_RATIONALE.md) - Why each data source was chosen
> - [FUTURE_IMPLEMENTATIONS.md](../planning/FUTURE_IMPLEMENTATIONS.md) - Planned future integrations

---

## Executive Summary

This document catalogs open and accessible space tracking data sources that can enhance the SDA-TAP-SpOC UCT Benchmark project. The research focuses on sources compatible with open-source distribution.

---

## Current Data Sources (Already Integrated)

| Source | Data Types | Auth Required | Integration Status |
|--------|-----------|---------------|-------------------|
| [UDL](https://unifieddatalibrary.com) | Observations, State Vectors, TLEs, Conjunctions | Yes (Base64 token) | **Primary source** |
| [Space-Track.org](https://www.space-track.org) | Historical TLEs, Satellite Catalog | Yes (Account) | Integrated |
| [CelesTrak](https://celestrak.org) | Current TLEs, Catalog | No | Integrated |
| [ESA DiscoWeb](https://discosweb.esoc.esa.int) | Physical properties (mass, area) | Yes (Bearer token) | Integrated |

---

## HIGH PRIORITY: New Data Sources to Integrate

### 1. EU SST (European Space Surveillance and Tracking)

**URL:** https://www.eusst.eu/

**What It Provides:**
- Collision Avoidance (CA) warnings
- Re-entry (RE) analysis
- Fragmentation (FG) analysis
- European catalog of tracked objects

**Access Method:**
- SST Service Provision Portal via EUSPA
- Services available to spacecraft operators worldwide
- Contact: https://www.euspa.europa.eu/eu-space-programme/ssa/eu-sst

**Status (2026):**
- 19 EU Member States in partnership
- Production system operational
- Free services for spaceflight safety

**Codebase Integration Opportunity:**
- Add `eusstQuery()` function to `apiIntegration.py`
- Complement UDL conjunction data with European perspective
- Cross-validate collision warnings

---

### 2. JSC Vimpel (Russian Space Catalog)

**URL:** http://spacedata.vimpel.ru/

**What It Provides:**
- Alternative space object catalog (independent from US)
- Strong coverage of GEO and HEO objects
- Hundreds of debris objects not in US catalog
- Data from 80+ optical observation systems

**Access Method:**
- Registration required with User Agreement
- Weekly data releases
- Citation required for publications

**Why It's Valuable:**
- Contains objects NOT tracked by US Space Command
- Strong focus on high-altitude debris
- Independent verification source

**Codebase Integration Opportunity:**
- Add `vimpelQuery()` function
- Cross-reference with Space-Track catalog
- Improve GEO/HEO object coverage in benchmarks

---

### 3. SatNOGS (Open Source Ground Station Network)

**URL:** https://satnogs.org/

**What It Provides:**
- 200+ operational ground stations worldwide
- 64+ million data frames collected
- Satellite transmitter information
- Real RF observation data

**Access Method:**
- Fully open API (Creative Commons CC-BY-SA)
- Network API: https://network.satnogs.org/
- Database API: https://db.satnogs.org/

**Why It's Valuable:**
- Completely open source (no auth barriers)
- Community-validated data
- Real observation timestamps
- Used by ESA for operational missions

**Codebase Integration Opportunity:**
- Add `satnogsQuery()` function for observation data
- Use as validation source for simulated observations
- Ground-truth for RF observation timestamps

---

### 4. ASTRIAGraph / University of Texas

**URL:** http://astria.tacc.utexas.edu/AstriaGraph/

**What It Provides:**
- Aggregated space object data from multiple sources
- Neo4j graph database architecture
- Combines: US Space Command, Vimpel, Planet Labs, SpaceX Starlink, SeeSat-L
- Open-source visualization and data

**Access Method:**
- Public web visualization
- DataVerse repository: https://dataverse.tdl.org/dataverse/ASTRIA
- Open-source code: https://github.com/ut-astria/AstriaGraph

**Related Tool - orbdetpy:**
- Python orbit determination library
- Based on Orekit (same as your project!)
- GitHub: https://github.com/ut-astria/orbdetpy
- Supports Kalman filtering, DMC, multiple measurement types

**Codebase Integration Opportunity:**
- Use ASTRIAGraph as unified data source for cross-validation
- Integrate orbdetpy algorithms for IOD comparison
- Leverage their multi-source catalog for benchmark diversity

---

### 5. GCAT (General Catalog of Artificial Space Objects)

**URL:** https://planet4589.org/space/gcat/

**What It Provides:**
- 57,000+ cataloged objects
- Complete launch history
- Object type classification
- TSV downloadable format
- Weekly updates

**Maintained By:** Dr. Jonathan McDowell (Harvard-Smithsonian)

**License:** Creative Commons CC-BY

**Codebase Integration Opportunity:**
- Supplement satellite catalog metadata
- Historical launch data for object classification
- Independent verification of object counts

---

### 6. ILRS (International Laser Ranging Service)

**URL:** https://ilrs.gsfc.nasa.gov/

**What It Provides:**
- Millimeter-precision range measurements
- 100+ satellites tracked (LEO, MEO, GEO, GNSS)
- Precise ephemerides
- Station position data

**Access Method:**
- Fully open (NASA CDDIS archive)
- https://www.earthdata.nasa.gov/data/space-geodesy-techniques/slr

**Why It's Valuable:**
- Highest precision tracking data available
- Independent validation for state vectors
- Ground-truth for orbit accuracy assessment

**Codebase Integration Opportunity:**
- Use as ground-truth for evaluation metrics
- Validate propagator accuracy
- High-precision reference for covariance calibration

---

### 7. UCS Satellite Database

**URL:** https://www.ucs.org/resources/satellite-database

**What It Provides:**
- 7,560+ operational satellites
- 28 data fields per satellite
- Ownership and usage information
- Technical specs (mass, power, lifetime)

**Access Method:**
- Free Excel/TSV download
- No authentication required

**Codebase Integration Opportunity:**
- Enrich satellite metadata
- Mission purpose classification
- Operational status tracking

---

## MEDIUM PRIORITY: Emerging Systems

### 8. TraCSS (Traffic Coordination System for Space)

**URL:** https://space.commerce.gov/traffic-coordination-system-for-space-tracss/

**What It Will Provide:**
- Next-generation US space traffic coordination
- Replacing/supplementing Space-Track.org functions
- On-demand conjunction screening
- Bulk ephemeris submission
- CDM distribution via API

**Status:**
- Production release: **January 2026**
- Beta users include: SpaceX, NOAA, Maxar, Planet Labs, Iridium

**Access Method:**
- Will provide REST API
- Contact: TraCSS.Commerce@noaa.gov

**Codebase Integration Opportunity:**
- Prepare `tracssQuery()` function for 2026 transition
- Enhanced conjunction data access
- Bulk screening capabilities for benchmarks

---

### 9. NASA CARA Tools

**URL:** https://github.com/nasa/CARA_Analysis_Tools

**What It Provides:**
- Open-source conjunction risk assessment algorithms
- Matlab SDK for collision probability calculation
- 20+ years of CDM analysis expertise
- Historical dataset of 11+ million CDMs

**License:** NASA Open Source Software Agreement

**Codebase Integration Opportunity:**
- Port CARA algorithms to Python for evaluation module
- Standardize Pc (probability of collision) calculations
- Benchmark against NASA's methodology

---

### 10. LeoLabs (Limited Free Access)

**URL:** https://leolabs.space/

**What It Provides:**
- Commercial radar tracking network
- Debris down to 2cm size
- High-quality ephemerides
- Public visualization tool

**Access Method:**
- Free public visualization: https://platform.leolabs.space/visualization
- 14-day free API trial
- Subscription for full access

**Codebase Integration Opportunity:**
- Use visualization for validation
- Consider academic partnership for research data

---

### 11. CORDS Reentry Database (Aerospace Corporation)

**URL:** https://aerospace.org/reentries

**What It Provides:**
- Historical reentry records since 2000
- Reentry predictions
- Sighting reports integration

**Access Method:**
- Publicly browsable database
- Sighting submission portal

**Codebase Integration Opportunity:**
- Add reentry prediction module
- Historical reentry data for validation

---

## Open-Source Tools to Leverage

### Orbit Determination & Propagation

| Tool | Language | License | URL |
|------|----------|---------|-----|
| orbdetpy | Python/Java | Open Source | https://github.com/ut-astria/orbdetpy |
| ccsds-ndm | Python | Open Source | https://github.com/egemenimre/ccsds-ndm |
| Orekit | Java | Apache 2.0 | https://www.orekit.org/ |

### Data Standards

| Standard | Purpose | Specification |
|----------|---------|---------------|
| CCSDS CDM | Conjunction Data Messages | [CCSDS 508.0-B-1](https://ccsds.org/Pubs/508x0b1e2c2.pdf) |
| CCSDS ODM | Orbit Data Messages | [CCSDS 502.0-B-3](https://ccsds.org/Pubs/502x0b3e1.pdf) |
| TLE/3LE | Two-Line Elements | Legacy NORAD format |
| OMM | Orbit Mean-Elements Message | XML/KVN/JSON |

---

## Codebase Improvement Roadmap

### Phase 1: Quick Wins (No API changes needed)

1. **Integrate GCAT data** - Download TSV, parse into database
2. **Add UCS satellite metadata** - Enrich `SATELLITES` table
3. **Implement ccsds-ndm parsing** - Standard CDM/ODM support

### Phase 2: New API Integrations

1. **SatNOGS API** - Fully open, no auth barriers
   - File: `apiIntegration.py`
   - New function: `satnogsQuery()`
   - Data: Observation timestamps, transmitter info

2. **Vimpel Catalog** - Registration required
   - File: `apiIntegration.py`
   - New function: `vimpelQuery()`
   - Data: Alternative TLEs, debris objects

3. **ILRS Data** - NASA CDDIS access
   - File: `apiIntegration.py`
   - New function: `ilrsQuery()`
   - Data: High-precision laser ranging

### Phase 3: Enhanced Evaluation

1. **Multi-source validation**
   - Compare results against US, Russian, European catalogs
   - Quantify inter-catalog differences

2. **CARA algorithm integration**
   - Port Pc calculation to Python
   - Standardize conjunction risk metrics

3. **TraCSS preparation**
   - Build adapter layer for 2026 transition
   - Test with beta API when available

### Phase 4: Advanced Features

1. **ASTRIAGraph integration**
   - Real-time multi-source fusion
   - Graph-based object correlation

2. **EU SST services**
   - European collision avoidance data
   - Fragmentation event tracking

---

## Architecture Recommendations

### Suggested New Module Structure

```
uct_benchmark/
├── api/
│   ├── apiIntegration.py      # Existing (UDL, Space-Track, CelesTrak, DiscoWeb)
│   ├── european_sources.py    # NEW: EU SST, Vimpel
│   ├── open_sources.py        # NEW: SatNOGS, GCAT, UCS, ILRS
│   └── commercial_sources.py  # NEW: LeoLabs, COMSPOC (if partnerships)
├── standards/
│   ├── ccsds_parser.py        # NEW: CDM/ODM parsing with ccsds-ndm
│   └── tle_converter.py       # Existing TLE parsing
└── validation/
    └── multi_source.py        # NEW: Cross-catalog validation
```

### Database Schema Extensions

```sql
-- New table for tracking data provenance
CREATE TABLE data_sources (
    id INTEGER PRIMARY KEY,
    source_name VARCHAR,         -- 'UDL', 'VIMPEL', 'SATNOGS', etc.
    source_url VARCHAR,
    last_sync TIMESTAMP,
    record_count INTEGER
);

-- Extend observations with source tracking
ALTER TABLE observations ADD COLUMN source_id INTEGER REFERENCES data_sources(id);

-- New table for cross-catalog correlation
CREATE TABLE catalog_correlation (
    us_norad_id INTEGER,
    vimpel_id VARCHAR,
    gcat_id VARCHAR,
    correlation_confidence FLOAT
);
```

---

## Summary: Priority Data Sources for Open-Source Project

| Priority | Source | Auth | Open License | Data Value |
|----------|--------|------|--------------|------------|
| **HIGH** | SatNOGS | None | CC-BY-SA | Real RF observations |
| **HIGH** | GCAT | None | CC-BY | Comprehensive catalog |
| **HIGH** | ILRS | None | Open | Precision validation |
| **HIGH** | Vimpel | Registration | Citation | Alternative catalog |
| **MEDIUM** | UCS Database | None | Open | Satellite metadata |
| **MEDIUM** | TraCSS | TBD (2026) | TBD | Next-gen US system |
| **MEDIUM** | NASA CARA | None | NASA OSS | Risk algorithms |
| **LOW** | EU SST | Operator | Service | European CA |
| **LOW** | LeoLabs | Trial/Paid | Commercial | High-res tracking |

---

## Sources

- [EU SST](https://www.eusst.eu/)
- [Space-Track.org](https://www.space-track.org/)
- [SatNOGS](https://satnogs.org/)
- [ASTRIAGraph](http://astria.tacc.utexas.edu/AstriaGraph/)
- [GCAT](https://planet4589.org/space/gcat/)
- [JSC Vimpel](http://spacedata.vimpel.ru/)
- [ILRS](https://ilrs.gsfc.nasa.gov/)
- [UCS Satellite Database](https://www.ucs.org/resources/satellite-database)
- [TraCSS](https://space.commerce.gov/traffic-coordination-system-for-space-tracss/)
- [NASA CARA Tools](https://github.com/nasa/CARA_Analysis_Tools)
- [CORDS Reentry Database](https://aerospace.org/reentries)
- [Satellite Dashboard](https://satellitedashboard.org/)
- [orbdetpy](https://github.com/ut-astria/orbdetpy)
- [ccsds-ndm](https://github.com/egemenimre/ccsds-ndm)
- [CCSDS CDM Standard](https://ccsds.org/Pubs/508x0b1e2c2.pdf)

---

*Research conducted: January 2026*
*For: SDA-TAP-SpOC UCT Benchmark Project*
