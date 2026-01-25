# Blake's Questions - Space Data Sources Integration

**Created**: January 2026
**Context**: Planning data source integrations for UCT Benchmark project

---

## Questions to Answer

### Question 1: External Data Provider Registration

**Should we pursue registration with external data providers that require signup?**

| Option | Description |
|--------|-------------|
| A) Yes, both | Register with Vimpel (Russian GEO/HEO debris) AND EU SST (European CA services) |
| B) EU SST only | Focus on European services, skip Russian catalog |
| C) Neither for now | Start with fully open sources only (SatNOGS, GCAT, ILRS, UCS) |

**Your Answer**: `Neither for now` *(answered)*

**Notes**: Starting with fully open sources makes sense for an open-source project. Can revisit Vimpel/EU SST later if needed.

---

### Question 2: ILRS Precision Validation Focus

**What should be the primary focus for ILRS (International Laser Ranging Service) precision validation data?**

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| A) LEO satellites | Low Earth orbit satellites (ISS, TOPEX, etc.) | Most relevant to UCT challenges, abundant data | Higher drag uncertainty |
| B) GNSS satellites | Navigation satellites (GPS, GLONASS, Galileo) | Very stable orbits, good for reference | Fewer UCT scenarios |
| C) Geodetic satellites | LAGEOS, Starlette, LARES | Highest precision (mm-level), perfect for ground truth | Limited to specific objects |
| D) All available | Download all ILRS-tracked satellites | Maximum coverage | Large data volume |

**Your Answer**: ______________________

**Additional context**: ILRS provides sub-centimeter range measurements that can serve as ground truth for evaluating state vector accuracy. The choice affects which objects we can validate against.

---

### Question 3: TraCSS Beta Access

**Should we contact TraCSS for beta access before the January 2026 production release?**

| Option | Description |
|--------|-------------|
| A) Yes, request beta | Contact TraCSS.Commerce@noaa.gov to request early access |
| B) Wait for production | Wait for January 2026 production release |

**Your Answer**: ______________________

**Additional context**: TraCSS (Traffic Coordination System for Space) is the new US system replacing some Space-Track functions. Beta users include SpaceX, Planet Labs, etc. Production release is January 2026.

---

### Question 4: Implementation Priority (Optional)

**Which data sources should we prioritize first?**

| Source | Effort | Value | Open License |
|--------|--------|-------|--------------|
| SatNOGS | Low | High (real observation timestamps) | CC-BY-SA |
| GCAT | Low | Medium (comprehensive catalog) | CC-BY |
| ILRS | Medium | High (precision validation) | Open |
| UCS Database | Low | Medium (satellite metadata) | Open |
| ccsds-ndm library | Low | High (standard formats) | Open |
| spacetrack library | Low | Medium (better API client) | Open |

**Your preferred order**: ______________________

---

## After Answering

Once you've filled in your answers, use this prompt to continue:

---

## Continuation Prompt

```
I've answered the questions in blakes-questions.md. Here are my answers:

1. External Registration: Neither for now (already answered)
2. ILRS Focus: [YOUR ANSWER]
3. TraCSS Beta: [YOUR ANSWER]
4. Priority Order (optional): [YOUR ANSWER]

Please continue with the implementation plan based on these decisions. The comprehensive research plan is in:
- Plan file: C:\Users\bcmister\.claude\plans\witty-crunching-stallman.md
- Research doc: RESEARCH_SPACE_DATA_SOURCES.md
- Planning prompt: PLANNING_PROMPT_DATA_SOURCES.md

I want to proceed with implementing the data source integrations.
```

---

## Files for Reference

| File | Purpose |
|------|---------|
| `RESEARCH_SPACE_DATA_SOURCES.md` | Initial research on all data sources |
| `PLANNING_PROMPT_DATA_SOURCES.md` | Prompt for strategic planning tied to Lewis's requirements |
| `.claude/plans/witty-crunching-stallman.md` | Comprehensive implementation plan with code examples |

---

## Summary of Research Completed

### High-Value Open Sources (No Registration Required)
1. **SatNOGS** - Real observation timestamps, 200+ ground stations, fully open API
2. **GCAT** - Comprehensive catalog with objects not in US catalog, CC-BY license
3. **ILRS** - Sub-centimeter precision laser ranging, NASA Earthdata access
4. **UCS Database** - Satellite metadata (mass, power, purpose, operator)
5. **ccsds-ndm** - Python library for CCSDS CDM/ODM/OMM parsing
6. **spacetrack** - Official Python library for Space-Track API

### Medium-Value (Registration Required)
7. **Vimpel** - Russian catalog with GEO/HEO debris (registration + citation)
8. **EU SST** - European collision avoidance services (registration, free)
9. **TraCSS** - New US system, production January 2026 (beta available)

### How These Improve Core Functionality

| Source | Improves | UCT Challenge Addressed |
|--------|----------|------------------------|
| SatNOGS | Dataset realism | Long periods between tracks |
| ILRS | Evaluation accuracy | Ground truth validation |
| GCAT | Catalog diversity | Objects in close angular space |
| Multi-source | Cross-validation | Poor sensor calibration |
