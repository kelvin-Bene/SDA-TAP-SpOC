# Beginner's Guide to UCT Benchmark

Welcome to the UCT Benchmark project! This guide explains the fundamental concepts in plain language, helping you understand what this system does and why it matters.

## What is the UCT Benchmark?

The UCT Benchmark is a tool for **testing satellite tracking algorithms**. Think of it like a standardized test for software that tries to identify unknown objects in space.

### The Problem We're Solving

Thousands of objects orbit Earth: satellites, rocket bodies, and debris. Space surveillance systems track these objects by observing them with telescopes and radars. But sometimes, a system detects an object it can't identify - this is called an **Uncorrelated Track (UCT)**.

A UCT processor's job is to:
1. Take observations of an unknown object
2. Figure out what orbit it's on
3. Try to match it to known objects in the catalog

The challenge: How do you know if your UCT processor is working correctly? That's where benchmarking comes in.

### What This Project Provides

The UCT Benchmark provides:
- **Standardized test datasets** with known answers
- **Evaluation metrics** to score algorithm performance
- **A web platform** to compare different algorithms
- **Tools** to generate new test datasets

## Understanding the Basics

### Orbital Mechanics 101

**Orbit**: The curved path an object takes around Earth due to gravity. An orbit is completely described by six numbers (called orbital elements).

**Orbital Regimes**: Orbits are categorized by altitude:

| Regime | Altitude | Period | Example |
|--------|----------|--------|---------|
| **LEO** (Low Earth Orbit) | 200-2,000 km | ~90 min | International Space Station |
| **MEO** (Medium Earth Orbit) | 2,000-35,786 km | 2-24 hr | GPS satellites |
| **GEO** (Geostationary) | 35,786 km | 24 hr | TV satellites |
| **HEO** (Highly Elliptical) | Varies | 8-24 hr | Molniya satellites |

### Observations and Tracks

**Observation**: A single measurement of where an object appeared in the sky at a specific time. Usually includes:
- Right Ascension (RA) - like longitude in the sky
- Declination (Dec) - like latitude in the sky
- Time of observation

**Track**: A series of observations that belong to the same object, grouped together.

**Uncorrelated Track (UCT)**: A track that doesn't match any known satellite in the catalog.

### Data Tiers

The benchmark uses a "tier" system to create increasingly difficult test cases:

| Tier | Description | Difficulty |
|------|-------------|------------|
| **T1** | Full real observations | Easy |
| **T2** | Downsampled (fewer observations) | Medium |
| **T3** | Simulated observations (gaps filled) | Medium-Hard |
| **T4** | Fully synthetic satellites | Hard |

## Your First Dataset

### Understanding the Web Interface

When you open the UCT Benchmark web app, you'll see:

1. **Dashboard** - Overview of datasets and recent submissions
2. **Datasets** - Browse, generate, and manage test datasets
3. **Submit** - Upload your algorithm's results for evaluation
4. **Results** - View detailed evaluation metrics
5. **Leaderboard** - Compare algorithm performance

### Step-by-Step: Viewing a Dataset

1. Click **Datasets** in the navigation
2. Select a dataset from the list
3. Review the dataset properties:
   - **Orbital Regime**: Which type of orbits are included
   - **Tier**: Difficulty level
   - **Observation Count**: How many measurements
   - **Object Count**: How many satellites

### Step-by-Step: Running an Evaluation

1. Process the dataset with your UCT algorithm
2. Go to **Submit** page
3. Upload your algorithm's output file
4. Click **Evaluate**
5. View results on the **Results** page

## Common Terminology

| Term | Definition |
|------|------------|
| **TLE** | Two-Line Element set - a standard format for describing satellite orbits |
| **State Vector** | Position and velocity of a satellite at a specific time |
| **Epoch** | A reference time for orbital calculations |
| **Propagation** | Predicting where a satellite will be at a future time |
| **IOD** | Initial Orbit Determination - figuring out an orbit from observations |
| **Association** | Matching observations to known satellites |

For a complete list, see the [Glossary](../reference/GLOSSARY.md).

## The Evaluation Pipeline

Here's how datasets flow through the system:

```
1. DATA GENERATION
   ┌──────────────────┐
   │  Pull satellite  │
   │  data from APIs  │
   └────────┬─────────┘
            ▼
   ┌──────────────────┐
   │  Create dataset  │
   │  with known truth│
   └────────┬─────────┘
            ▼
2. PROCESSING (Your Algorithm)
   ┌──────────────────┐
   │  UCT Processor   │
   │  analyzes data   │
   └────────┬─────────┘
            ▼
3. EVALUATION
   ┌──────────────────┐
   │  Compare results │
   │  to ground truth │
   └────────┬─────────┘
            ▼
   ┌──────────────────┐
   │  Generate score  │
   │  and metrics     │
   └──────────────────┘
```

## Interpreting Results

### Key Metrics

**Precision**: Of all the objects your algorithm found, how many were correct?
- Formula: True Positives / (True Positives + False Positives)
- High precision = few false alarms

**Recall**: Of all the actual objects, how many did your algorithm find?
- Formula: True Positives / (True Positives + False Negatives)
- High recall = few missed objects

**F1 Score**: Combines precision and recall into a single number
- Formula: 2 × (Precision × Recall) / (Precision + Recall)
- Higher is better (max = 1.0)

**Position Error**: How far off is your calculated orbit from the true orbit?
- Measured in kilometers
- Lower is better

### What Good Results Look Like

| Metric | Good | Excellent |
|--------|------|-----------|
| Precision | >0.8 | >0.95 |
| Recall | >0.8 | >0.95 |
| F1 Score | >0.8 | >0.95 |
| Position Error | <10 km | <1 km |

## Architecture Overview

The UCT Benchmark consists of three main parts:

```
┌─────────────────────────────────────────────────────────────┐
│                    UCT BENCHMARK SYSTEM                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────┐  ┌─────────────────┐                  │
│  │   Web Frontend  │  │   Backend API   │                  │
│  │   (React)       │──│   (FastAPI)     │                  │
│  │   Port 5173     │  │   Port 8000     │                  │
│  └─────────────────┘  └────────┬────────┘                  │
│                                │                            │
│                       ┌────────┴────────┐                  │
│                       │  Python Core    │                  │
│                       │  - Data processing                 │
│                       │  - Orbit propagation               │
│                       │  - Evaluation metrics              │
│                       └────────┬────────┘                  │
│                                │                            │
│                       ┌────────┴────────┐                  │
│                       │    Database     │                  │
│                       │    (DuckDB)     │                  │
│                       └─────────────────┘                  │
└─────────────────────────────────────────────────────────────┘
```

## Next Steps

Now that you understand the basics:

1. **Try the Quick Start** - [Quick Start Guide](../QUICK_START.md)
2. **Set up your environment** - [Getting Started](../getting-started.md)
3. **Generate a dataset** - [Dataset Generation Guide](DATASET_GENERATION.md)
4. **Learn the web interface** - [UI Guide](UI_GUIDE.md)
5. **Explore the API** - [Backend API Documentation](../technical/BACKEND_API.md)

## FAQ for Beginners

**Q: Do I need space expertise to use this?**
A: No! The system handles the orbital mechanics. You just need to provide observations and get back results.

**Q: What programming languages are supported?**
A: The benchmark system itself is in Python (backend) and TypeScript/React (frontend). Your algorithm can be in any language - you just need to produce output in the specified JSON format.

**Q: Can I use this for real satellite tracking?**
A: This is a benchmarking tool for testing algorithms with known ground truth. For operational tracking, you would integrate with actual space surveillance networks.

**Q: Where does the data come from?**
A: Real satellite data comes from public sources like Space-Track.org and CelesTrak. The system can also generate simulated observations for testing.

---

**Have more questions?** Check the [FAQ](../reference/FAQ.md) or the detailed [Glossary](../reference/GLOSSARY.md).
