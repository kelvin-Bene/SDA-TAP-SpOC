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

**Status**: PENDING
**Date**: -
**Decision Maker**: Awaiting input

**Question**: Should we contact TraCSS for beta access before the January 2026 production release?

| Option | Description |
|--------|-------------|
| A) Yes, request beta | Contact TraCSS.Commerce@noaa.gov to request early access |
| B) Wait for production | Wait for January 2026 production release |

**Decision**: _Pending_

**Additional Context**: TraCSS (Traffic Coordination System for Space) is the new US system replacing some Space-Track functions. Beta users include SpaceX, Planet Labs, etc. Production release is January 2026.

**Update (Feb 2026)**: TraCSS should now be in production. Need to evaluate current API availability.

<!-- AI_IMPROVEMENT_OPPORTUNITY: TraCSS production status should be verified and integration planned -->

---

### Decision 4: Implementation Priority for Data Sources

**Status**: PENDING
**Date**: -
**Decision Maker**: Awaiting input

**Question**: Which data sources should we prioritize first?

| Source | Effort | Value | Open License |
|--------|--------|-------|--------------|
| SatNOGS | Low | High (real observation timestamps) | CC-BY-SA |
| GCAT | Low | Medium (comprehensive catalog) | CC-BY |
| ILRS | Medium | High (precision validation) | Open |
| UCS Database | Low | Medium (satellite metadata) | Open |
| ccsds-ndm library | Low | High (standard formats) | Open |
| spacetrack library | Low | Medium (better API client) | Open |

**Decision**: _Pending_

**Recommendation**: Based on Decision 1 (open sources first), suggested priority:
1. GCAT (low effort, immediately usable)
2. ccsds-ndm (enables standard format parsing)
3. UCS Database (enriches satellite metadata)
4. SatNOGS (real observation timestamps)
5. ILRS (precision validation)

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
