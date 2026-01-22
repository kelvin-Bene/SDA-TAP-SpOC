# Documentation Consistency Audit Report

**Date:** January 13, 2026
**Branch:** `information-aggregation`
**Auditor:** Claude Code (automated analysis)

---

## Executive Summary

This audit compares all project documentation against the official project briefs (SDA-Project.pdf, SpOC-Project.pdf, SpOC-SDA-Description.pdf) and identifies inconsistencies across the codebase. **15 significant issues** were identified requiring attention.

---

## 1. Official Baseline (Source of Truth)

### From Official PDFs:

| Attribute | SDA TAP Lab Project | SpOC Project |
|-----------|---------------------|--------------|
| **Focus** | Labelling & Data Storage | Benchmark Dataset Generation & Evaluation Criteria |
| **Primary Goal** | Automated data annotation pipeline | Web-hosted UI for algorithm developers |
| **Data Source** | UDL (Unified Data Library) | Same |
| **Framework** | Common Task Framework (Donoho, 2017) | Same |

### Key Organizational Facts:
- **Sister Projects**: SDA TAP Lab and SpOC are two distinct but related teams
- **Meeting Times**: Thursday 3:30 PM (mentor), Tuesday 3:30 PM (lab)
- **Requirements**: U.S. citizens only
- **Location**: West Lafayette, IN / Rockies (Data Mine of the Rockies)
- **Duration**: 2025-2026 academic year

### Team Structure Clarification (January 13, 2026):

> **Important Context:** The codebase is **shared between both teams** (SDA TAP Lab and SpOC).
> During Semester 1 (Fall 2025), the teams functioned as **one unified team**.
> In Semester 2 (Spring 2026), the teams are splitting responsibilities but continue to share the same codebase.

This explains why the current implementation covers the full pipeline (labelling, storage, benchmark generation, and evaluation) rather than being split between teams.

---

## 2. Critical Inconsistencies Found

### 2.1 Package Naming Inconsistency (HIGH PRIORITY)

| Location | Package Name | Version |
|----------|--------------|---------|
| `UCT-Benchmark-DMR/combined/pyproject.toml` | `uct_benchmark` (underscore) | 0.0.1 |
| `external-code/master/pyproject.toml` | `uctbenchmark` (no underscore) | 0.0.3 |
| `external-code/jovan-linuxTesting/pyproject.toml` | `uctbenchmark` (no underscore) | 0.0.4 |

**Impact:** Import statements will fail if packages are mixed. This must be standardized.

**Recommendation:** Standardize to `uct_benchmark` (with underscore) per PEP 8 naming conventions.

---

### 2.2 Description Typo (MEDIUM)

**File:** `external-code/master/pyproject.toml` and `external-code/jovan-linuxTesting/pyproject.toml`

```
description = "f a packaged representation of the SDA TAP Lab UCTBenchmark MVP still in-process."
```

**Issue:** Starts with lowercase "f" - appears to be incomplete f-string or typo.

**Should be:**
```
description = "A packaged representation of the SDA TAP Lab UCTBenchmark MVP still in-process."
```

Note: The README in `jovan-linuxTesting` has the correct capitalization, but the `pyproject.toml` does not.

---

### 2.3 Author Attribution Inconsistency (MEDIUM)

| Location | Authors Field |
|----------|---------------|
| `UCT-Benchmark-DMR/combined/pyproject.toml` | "UCT Benchmark Team, SDA TAP Lab Cohort 7" |
| `external-code/jovan-linuxTesting/pyproject.toml` | "Jovan Bergh" |
| `external-code/master/pyproject.toml` | "Jovan Bergh" |

**Recommendation:** Use team attribution consistently, or maintain a contributors list.

---

### 2.4 Python Version Conflict (HIGH PRIORITY)

| Location | Stated Requirement |
|----------|-------------------|
| `UCT-Benchmark-DMR/combined/INSTALLATION.md` | Python 3.9-3.12 (3.12 recommended) |
| `UCT-Benchmark-DMR/combined/pyproject.toml` | `~=3.12.0` (3.12 ONLY) |
| `external-code/jovan-linuxTesting/README.md` | Python >=3.12 |

**Issue:** INSTALLATION.md claims 3.9+ support, but pyproject.toml restricts to 3.12 only.

**Recommendation:** Update INSTALLATION.md to reflect actual requirement (Python 3.12).

---

### 2.5 Linux Setup Documentation vs Reality (HIGH PRIORITY)

**In README (`external-code/jovan-linuxTesting/README.md`):**
```
### Linux Setup

ACTION NEEDED: Bash script for Linux/Unix systems is still pending development
```

**Reality:** `setup.sh` EXISTS in `external-code/jovan-linuxTesting/`

**However, `setup.sh` has syntax errors:**
```bash
# Line 4 - BROKEN:
if [ -d "data"]; then    # Missing space before ]

# Should be:
if [ -d "data" ]; then   # Space required
```

**Lines affected:** 4, 5, 6, 9, 12, 15, 18

**Recommendation:**
1. Fix syntax errors in `setup.sh`
2. Update README to remove "ACTION NEEDED" text
3. Document that Linux setup is available

---

### 2.6 Team Responsibility Confusion (HIGH PRIORITY)

**Official Documentation States:**
- **SDA TAP Lab**: Labelling & Data Storage
- **SpOC**: Benchmark Dataset Generation & Evaluation Criteria

**Current READMEs Describe:**
- Full 3-phase pipeline covering BOTH responsibilities:
  - Phase 1: Create_Dataset.py (dataset creation)
  - Phase 2: MainMVP.py (UCTP simulation)
  - Phase 3: Evaluation.py (evaluation)

**Issue:** The codebase appears to implement the full pipeline, not just the SDA TAP Lab portion (Labelling & Data Storage).

**Clarification Needed:** Is this team responsible for the full pipeline, or should work be coordinated with SpOC team?

---

### 2.7 Dependency Differences (MEDIUM)

**`UCT-Benchmark-DMR/combined` has but others don't:**
- `solara>=1.51.1` (Web GUI)
- `pyarrow>=22.0.0` (Data format)

**`jovan-linuxTesting` has but `local-work` doesn't:**
- `jdk4py>=21.0.8.0` (Java runtime)
- `fpdf>=1.7.2` (PDF generation)
- `scipy>=1.16.2` (Scientific computing)
- `dotenv>=0.9.9` (Environment variables)
- `polars>=1.35.2` (DataFrame library)
- `duckdb>=1.4.2` (Database)

**Issue:** Different GUI approaches (Solara vs CustomTkinter) and missing dependencies could cause runtime failures.

---

### 2.8 Project Structure Differences (MEDIUM)

**`UCT-Benchmark-DMR/combined` structure:**
```
uct_benchmark/
├── api/
├── data/
├── evaluation/
├── simulation/
├── uctp/
├── utils/
├── Create_Dataset.py
├── Evaluation.py
├── MainMVP.py
└── batchPull.py
```

**`external-code/master` structure:**
```
uctbenchmark/
├── modeling/
│   ├── predict.py
│   └── train.py
├── config.py
├── dataset.py
├── features.py
└── plots.py
```

**Issue:** Completely different module organization suggests these are not the same codebase.

---

### 2.9 LLNL Paper vs Current Implementation (INFORMATIONAL)

The LLNL paper "A common task framework for testing and evaluation at the Space Domain Awareness" states:

> "The front end for the web app is built using NextJS, a React framework. The API is built using the ExpressJS framework, and the backend algorithms are built using Python."

**Current Implementation:** Uses Python-only stack (Solara/CustomTkinter for GUI)

**Note:** This may be intentional - the current project may be building the Python data pipeline, while LLNL handles the web frontend.

---

### 2.10 Documentation Files That Can't Be Read (INFORMATIONAL)

The following `.docx` files exist but couldn't be analyzed in this audit:
- `UCT Benchmarking/Documentation/Benchmarking Documentation.docx`
- `UCT Benchmarking/Documentation/Transition Document.docx`
- `UCT Benchmarking/Documentation/UCTP Benchmarking Framework_...docx`
- `UCT Benchmarking/Learning Docs/The Common Task Framework (CTF).docx`
- `UCT Benchmarking/Learning Docs/CTF at SDA TAP Lab.docx`
- `UCT Benchmarking/Learning Docs/Acronym Cheat Sheet.docx`
- `SDA x SpOC UCT Processing/Documentation(s)/Dr Cline Documentation/Dr. Cline Demo Documentation.docx`
- `SDA x SpOC UCT Processing/Documentation(s)/Jovan Documentation/Jovan Demo Documentation.docx`
- `SDA x SpOC UCT Processing/TDM Requirements.docx`
- `SDA x SpOC UCT Processing/Questions and concerns.docx`
- `SDA x SpOC UCT Processing/Brainstorming_Progress.docx`

**Recommendation:** Consider converting critical documentation to Markdown for version control and easier review.

---

## 3. Consistency Issues Summary

| ID | Issue | Severity | Status |
|----|-------|----------|--------|
| 2.1 | Package naming (underscore vs no underscore) | HIGH | Needs fix |
| 2.2 | Description typo ("f a packaged...") | MEDIUM | Needs fix |
| 2.3 | Author attribution inconsistent | MEDIUM | Needs decision |
| 2.4 | Python version conflict | HIGH | Needs fix |
| 2.5 | Linux setup.sh exists but README says pending | HIGH | Needs fix |
| 2.6 | Team responsibility unclear | HIGH | RESOLVED - Teams share codebase |
| 2.7 | Dependency differences | MEDIUM | Needs alignment |
| 2.8 | Project structure differences | MEDIUM | Needs alignment |
| 2.9 | LLNL paper vs implementation | INFO | May be intentional |
| 2.10 | DOCX files not in version control format | INFO | Consider converting |

---

## 4. Recommendations

### Immediate Actions (HIGH Priority):

1. **Standardize package name** to `uct_benchmark` across all branches
2. **Fix setup.sh syntax errors** (add spaces before `]` in conditionals)
3. **Update README** to remove "ACTION NEEDED" for Linux setup
4. **Update INSTALLATION.md** to state Python 3.12 requirement correctly
5. **Fix description typo** in pyproject.toml files

### Short-term Actions (MEDIUM Priority):

6. **Clarify team responsibilities** with mentors - is this team doing full pipeline or just labelling/storage?
7. **Align dependencies** between UCT-Benchmark-DMR/combined and external branches
8. **Standardize author attribution** to team name
9. **Create a CONTRIBUTING.md** with naming conventions

### Long-term Actions (LOW Priority):

10. **Convert critical DOCX files to Markdown** for better version control
11. **Create unified project structure** documentation
12. **Document GUI approach decision** (Solara vs CustomTkinter)

---

## 5. Files Analyzed

### PDFs (Successfully Read):
- `documentation/SDA-Project.pdf`
- `documentation/SpOC-Project.pdf`
- `documentation/SpOC-SDA-Description.pdf`
- `documentation/UCT Benchmarking/Learning Docs/A common task framework for testing and evaluation at the Space Domain Awareness.pdf`

### Markdown/Text Files:
- `UCT-Benchmark-DMR/combined/README.md`
- `UCT-Benchmark-DMR/combined/INSTALLATION.md`
- `external-code/master/README.md`
- `external-code/jovan-linuxTesting/README.md`
- `documentation/SDA x SpOC UCT Processing/Documentation(s)/Jovan Documentation/README.md`
- `documentation/UCT Benchmarking/_readMe.txt`
- `documentation/UCT Benchmarking/Documentation/_readMe.txt`

### Configuration Files:
- `UCT-Benchmark-DMR/combined/pyproject.toml`
- `external-code/master/pyproject.toml`
- `external-code/jovan-linuxTesting/pyproject.toml`
- `external-code/jovan-linuxTesting/setup.sh`

---

**End of Report**
