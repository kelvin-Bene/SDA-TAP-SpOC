# Project Decision Log

<!-- AI_METADATA
purpose: Track major project decisions with rationale and status
status: active
related_files: [planning/PROJECT_STATUS.md, planning/INTEGRATED_ROADMAP.md, technical/DATA_SOURCE_RATIONALE.md]
last_updated: 2026-02-03
-->

This document tracks major project decisions, their rationale, and outcomes. It serves as a historical record for understanding why certain architectural and strategic choices were made.

---

## Decision Status Legend

| Status | Meaning |
|--------|---------|
| **DECIDED** | Decision made and implemented |
| **PENDING** | Awaiting input or decision |
| **REVISIT** | Previously decided but may need reconsideration |

---

<!-- AI_SECTION: decisions -->

## Strategic Decisions

### Decision 1: External Data Provider Registration

**Status**: DECIDED
**Date**: January 2026
**Decision Maker**: Blake (Project Lead)

**Question**: Should we pursue registration with external data providers that require signup?

| Option | Description |
|--------|-------------|
| A) Yes, both | Register with Vimpel (Russian GEO/HEO debris) AND EU SST (European CA services) |
| B) EU SST only | Focus on European services, skip Russian catalog |
| **C) Neither for now** | Start with fully open sources only (SatNOGS, GCAT, ILRS, UCS) |

**Decision**: **Option C - Neither for now**

**Rationale**: Starting with fully open sources makes sense for an open-source project. Can revisit Vimpel/EU SST later if needed. This approach:
- Ensures all data can be freely redistributed
- Reduces onboarding friction for new contributors
- Avoids dependency on registration processes
- Aligns with open-source project philosophy

**Follow-up**: See [DATA_SOURCE_RATIONALE.md](../technical/DATA_SOURCE_RATIONALE.md) for detailed source selection criteria.

---

### Decision 2: ILRS Precision Validation Focus

**Status**: PENDING
**Date**: -
**Decision Maker**: Awaiting input

**Question**: What should be the primary focus for ILRS (International Laser Ranging Service) precision validation data?

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| A) LEO satellites | Low Earth orbit satellites (ISS, TOPEX, etc.) | Most relevant to UCT challenges, abundant data | Higher drag uncertainty |
| B) GNSS satellites | Navigation satellites (GPS, GLONASS, Galileo) | Very stable orbits, good for reference | Fewer UCT scenarios |
| C) Geodetic satellites | LAGEOS, Starlette, LARES | Highest precision (mm-level), perfect for ground truth | Limited to specific objects |
| D) All available | Download all ILRS-tracked satellites | Maximum coverage | Large data volume |

**Decision**: _Pending_

**Additional Context**: ILRS provides sub-centimeter range measurements that can serve as ground truth for evaluating state vector accuracy. The choice affects which objects we can validate against.

<!-- AI_IMPROVEMENT_OPPORTUNITY: This decision should be made before implementing ILRS integration -->

---

### Decision 3: TraCSS Beta Access

**Status**: REVISIT
**Date**: January 2026
**Decision Maker**: Awaiting input

**Question**: Should we contact TraCSS for beta access before the January 2026 production release?

| Option | Description |
|--------|-------------|
| A) Yes, request beta | Contact TraCSS.Commerce@noaa.gov to request early access |
| **B) Wait for production** | Wait for January 2026 production release |

**Decision**: **Option B - Wait for production**

**Rationale**: Given the timeline and our focus on fully open sources first, we opted to wait for TraCSS production release.

**Update (Feb 2026)**: TraCSS is now in production as of January 2026. API evaluation and integration should be considered for a future sprint. Added to remaining data source work in FUTURE_IMPLEMENTATIONS.md.

<!-- AI_IMPROVEMENT_OPPORTUNITY: TraCSS production API should be evaluated for potential integration -->

---

### Decision 4: Implementation Priority for Data Sources

**Status**: DECIDED
**Date**: January 2026
**Decision Maker**: Development Team

**Question**: Which data sources should we prioritize first?

| Source | Effort | Value | Open License | Status |
|--------|--------|-------|--------------|--------|
| GCAT | Low | Medium (comprehensive catalog) | CC-BY | ✅ Implemented |
| UCS Database | Low | Medium (satellite metadata) | Open | ✅ Implemented |
| SatNOGS | Low | High (real observation timestamps) | CC-BY-SA | ✅ Implemented |
| ILRS | Medium | High (precision validation) | Open | ⚠️ Partial |
| ccsds-ndm library | Low | High (standard formats) | Open | Pending |
| spacetrack library | Low | Medium (better API client) | Open | Deferred |

**Decision**: **Implemented per recommended priority**

**Implementation Summary**:
1. ✅ GCAT - Full catalog with launches, reentries (`open_sources.py`)
2. ✅ UCS Database - Satellite metadata with mass data for HAMR detection
3. ✅ SatNOGS - RF observations, ground stations, transmitters
4. ⚠️ ILRS - Satellite/station lists work; predictions need Earthdata auth
5. Pending: ccsds-ndm for CDM parsing
6. Deferred: spacetrack library (current integration sufficient)

**Outcome**: All high-priority open sources are now integrated. DataSourceManager provides unified interface for satellite enrichment.

<!-- /AI_SECTION -->

---

## Technical Decisions

<!-- AI_SECTION: technical_decisions -->

### Decision 5: Database Technology Selection

**Status**: DECIDED
**Date**: January 2026
**Decision Maker**: SDA TAP Team

**Question**: What database technology should be used for centralized data storage?

| Option | Pros | Cons |
|--------|------|------|
| PostgreSQL | Mature, scalable, full ACID | Heavier setup |
| SQLite | Simple, embedded | Limited concurrency |
| **DuckDB** | Fast analytics, embedded, columnar | Newer technology |

**Decision**: **DuckDB**

**Rationale**:
- Excellent for analytical queries (our primary use case)
- Embedded - no server setup required
- Columnar storage efficient for time-series observation data
- Good Python integration
- Supports Parquet export for data sharing

**Implementation**: See `uct_benchmark/database/` for implementation details.

---

### Decision 6: Web Framework Selection

**Status**: DECIDED
**Date**: January 2026
**Decision Maker**: SpOC Team

**Question**: What frameworks should be used for the web platform?

**Decision**:
- **Frontend**: React with TypeScript, Vite build system
- **Backend**: FastAPI (Python)
- **State Management**: Zustand

**Rationale**:
- React: Large ecosystem, component reusability
- TypeScript: Type safety for complex data structures
- FastAPI: Integrates naturally with existing Python codebase
- Zustand: Simpler than Redux for our scale

---

### Decision 7: Tier System Design

**Status**: DECIDED
**Date**: Fall 2025
**Decision Maker**: Original project team

**Question**: How should dataset difficulty be classified?

**Decision**: Five-tier system (T1-T5)

| Tier | Quality | Processing Required |
|------|---------|---------------------|
| T1 | High | Light downsampling (optional) |
| T2 | Good | Heavy downsampling |
| T3 | Moderate | Observation simulation |
| T4 | Low | Object simulation |
| T5 | Unusable | Reject request |

**Rationale**: Provides clear quality levels that map directly to processing requirements. Each tier represents a distinct challenge level for UCTP algorithms.

**Implementation Status**:
- T1/T2: Fully implemented
- T3: Fully implemented
- T4: Not started (stretch goal)
- T5: N/A (rejection case)

<!-- /AI_SECTION -->

---

## Architectural Decisions

<!-- AI_SECTION: architecture_decisions -->

### Decision 8: Orbit Association Algorithm

**Status**: DECIDED
**Date**: Fall 2025
**Decision Maker**: SpOC Team

**Question**: How should UCTP output be associated with reference orbits?

**Decision**: Hungarian algorithm with Euclidean position norm

**Rationale**: Per tech lead Lewis:
> "The UCT processor is not going to tell us 'Oh, we think this is this object.' It's just gonna say all of these observations are correlated with each other and this is the orbit the object is in."

Hungarian algorithm provides globally optimal one-to-one matching, which is appropriate for this scenario.

**Implementation**: `uct_benchmark/evaluation/orbitAssociation.py`

---

### Decision 9: Propagator Selection

**Status**: DECIDED
**Date**: Fall 2025

**Question**: What orbit propagator(s) should be used?

**Decision**: Orekit-based propagators via Python wrapper

| Propagator | Use Case |
|------------|----------|
| Monte Carlo | Covariance propagation, uncertainty analysis |
| Ephemeris | Efficient batch propagation |
| TLE (SGP4/SDP4) | Two-line element propagation |

**Rationale**: Orekit provides production-quality implementations with extensive force modeling options.

### Decision 10: UCTP Lab Architecture

**Status**: DECIDED
**Date**: January 2026
**Decision Maker**: Development Team

**Question**: How should the UCTP Lab framework be structured for algorithm development?

**Decision**: Modular framework with sandbox environment

**Implementation**:
- Location: `uct_benchmark/uctp_lab/`
- Provides isolated environment for UCT processor development
- Integration with existing evaluation metrics
- Test data generation capabilities
- Supports algorithm iteration without affecting production pipeline

**Rationale**: Separate UCTP Lab allows algorithm developers to iterate quickly without impacting the main benchmark infrastructure. Clean separation of concerns.

---

### Decision 11: Credential Management System

**Status**: DECIDED
**Date**: January 2026
**Decision Maker**: SpOC Team

**Question**: How should external API credentials be managed?

**Decision**: Supabase-backed credential storage with anonymous fallback

**Implementation**:
- Backend: `backend_api/auth/` with JWT tokens
- Frontend: `useCredentials` hook for secure credential handling
- Dual-mode: Supabase when configured, in-memory for development
- External APIs (UDL, Space-Track) credentials stored securely
- Anonymous mode allows operation without credentials for open sources

**Rationale**: Secure credential management is essential for API access while maintaining ease of development. Anonymous fallback ensures the system works without external dependencies during development.

<!-- /AI_SECTION -->

---

## Process for Adding Decisions

When a significant project decision is made:

1. Add a new section under the appropriate category
2. Include:
   - **Status**: DECIDED, PENDING, or REVISIT
   - **Date**: When decided (or when question arose)
   - **Decision Maker**: Who made/will make the decision
   - **Question**: The decision being made
   - **Options**: Available choices with pros/cons
   - **Decision**: The chosen option
   - **Rationale**: Why this option was selected
3. Add AI markers if the decision creates improvement opportunities
4. Update related documents as needed

---

## References

- [PROJECT_STATUS.md](PROJECT_STATUS.md) - Current implementation status
- [INTEGRATED_ROADMAP.md](INTEGRATED_ROADMAP.md) - Project timeline
- [DATA_SOURCE_RATIONALE.md](../technical/DATA_SOURCE_RATIONALE.md) - Data source decisions
- [FUTURE_IMPLEMENTATIONS.md](FUTURE_IMPLEMENTATIONS.md) - Planned features

---

*Transformed from `blakes-questions.md` on 2026-02-03*
