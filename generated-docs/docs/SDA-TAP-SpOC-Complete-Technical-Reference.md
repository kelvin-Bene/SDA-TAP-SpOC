# SDA-TAP-SpOC UCT Benchmark: Complete Technical Reference

> **Version:** 1.0 | **Last Updated:** 2026-02-05 | **Schema Version:** 1.3.0
>
> Every concept in this document is explained twice: once in precise technical language,
> and once in plain English for non-specialists.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [The Space Problem - Why This Matters](#2-the-space-problem---why-this-matters)
3. [Orbital Mechanics Fundamentals](#3-orbital-mechanics-fundamentals)
4. [Data Formats](#4-data-formats)
5. [Sensors and Observations](#5-sensors-and-observations)
6. [Data Sources](#6-data-sources)
7. [What is UCTP?](#7-what-is-uctp)
8. [The Benchmark System](#8-the-benchmark-system)
9. [Evaluation Metrics](#9-evaluation-metrics)
10. [System Architecture](#10-system-architecture)
11. [Satellite Properties & Classification](#11-satellite-properties--classification)
12. [Orbit Propagation](#12-orbit-propagation)
13. [Coordinate Systems & Reference Frames](#13-coordinate-systems--reference-frames)
14. [Glossary](#14-glossary)

---

# 1. Project Overview

## 1.1 What is SDA-TAP-SpOC?

**Technical:**
SDA-TAP-SpOC stands for **Space Domain Awareness - Tools, Applications & Processing Lab -
Space Operations Command**. It is a benchmarking and evaluation platform for Uncorrelated
Track Processing (UCTP) algorithms. The system provides standardized benchmark datasets
derived from real space surveillance observations, evaluates algorithm submissions against
reference truth data using binary, state, and residual metrics, and maintains a leaderboard
for comparative analysis.

**Plain English:**
Imagine a scoring system for satellite-tracking software. Different teams build software
that tries to figure out which blips on a radar screen belong to which satellites. This
project gives every team the *same* test data, runs their software against it, and grades
them all the same way -- so we can fairly compare who does the best job.

The acronym breaks down as:
- **SDA** (Space Domain Awareness) - Understanding what is happening in space
- **TAP** (Tools, Applications & Processing Lab) - The lab that builds the tools
- **SpOC** (Space Operations Command) - The military command overseeing space operations

## 1.2 What Problem Does It Solve?

**Technical:**
There is no industry-standard benchmark for evaluating UCTP algorithms. Different research
groups use different datasets, different metrics, and different evaluation methodologies,
making cross-comparison impossible. SDA-TAP-SpOC implements a Common Task Framework (CTF)
that standardizes:
1. Dataset generation from real UDL observations
2. Decorrelation (stripping satellite IDs to create "uncorrelated" tracks)
3. Submission format (state vectors or TLEs with sourced observation IDs)
4. Evaluation metrics (binary classification, state accuracy, observation residuals)

**Plain English:**
Right now, every team that builds satellite-tracking software tests it on different data
and measures success differently. It is like having a math competition where every student
takes a different test -- you cannot tell who is actually best. This project creates one
standardized test that everyone takes, with one answer key, and one grading rubric.

## 1.3 Who Uses It and Why?

| User Group | Purpose |
|---|---|
| **U.S. Space Force / Military** | Evaluate and select UCTP algorithms for operational use |
| **Defense Contractors** | Benchmark proprietary algorithms against competitors |
| **Academic Researchers** | Validate novel orbit determination methods on real data |
| **AFRL Scholars** | Develop and refine the evaluation methodology itself |

## 1.4 High-Level System Purpose

```
+------------------------------------------------------------------+
|                   SDA-TAP-SpOC UCT Benchmark                     |
|                                                                  |
|   Real Observations -----> Benchmark Dataset -----> UCTP Under   |
|   (from UDL, etc.)        (decorrelated,           Test          |
|                            standardized)                         |
|                                   |                    |         |
|                                   v                    v         |
|                            Answer Key             UCTP Output    |
|                            (reference             (candidate     |
|                             orbits)                orbits)       |
|                                   \                  /           |
|                                    v                v            |
|                              +-----------------+                 |
|                              |   EVALUATION    |                 |
|                              | Binary Metrics  |                 |
|                              | State Metrics   |                 |
|                              | Residual Metrics|                 |
|                              +-----------------+                 |
|                                      |                           |
|                                      v                           |
|                            Score / Leaderboard                   |
+------------------------------------------------------------------+
```

## 1.5 Core Workflow

1. **Configure** - Choose orbital regime, data quality tier, sensor types, object count
2. **Generate** - Pull real observations from UDL, select optimal time windows, apply
   downsampling or simulation as needed
3. **Decorrelate** - Strip satellite IDs from observations, creating "uncorrelated" tracks
4. **Distribute** - Provide decorrelated dataset to UCTP algorithm developers
5. **Process** - Algorithm developers run their UCTP on the dataset
6. **Submit** - Developers upload candidate orbits (state vectors or TLEs)
7. **Evaluate** - System associates candidates with references, computes metrics
8. **Rank** - Results appear on the leaderboard for comparison

---

# 2. The Space Problem - Why This Matters

## 2.1 What is Space Domain Awareness (SDA)?

**Technical:**
Space Domain Awareness (SDA), formerly called Space Situational Awareness (SSA), is the
comprehensive understanding of the space environment. It encompasses:
- Tracking the positions and velocities of all cataloged space objects
- Predicting future positions (orbit propagation)
- Detecting new or unidentified objects
- Assessing collision risk (conjunction assessment)
- Characterizing threats and anomalies (maneuvers, breakups, deployments)

**Plain English:**
SDA is like air traffic control, but for space. Air traffic controllers know where every
airplane is, where it is going, and whether any two planes might get too close. SDA does
the same thing for everything orbiting Earth -- satellites, rocket bodies, debris, and all
the other stuff humans have launched over the decades.

## 2.2 Why Tracking Objects in Space is Hard

**Technical:**
Several factors make space object tracking significantly harder than terrestrial tracking:

1. **Vast volume** - The tracked space extends from 200 km to 36,000+ km altitude,
   representing an enormous 3D volume
2. **Intermittent observations** - Ground-based sensors can only observe objects when they
   pass overhead; objects are unobserved for most of their orbit
3. **No transponders** - Unlike aircraft, most space objects do not broadcast their identity
   or position; passive observation is required
4. **Orbital dynamics** - Objects move at 3-8 km/s; even small errors compound rapidly
5. **Numbers** - There are 30,000+ tracked objects and millions of debris fragments too
   small to track consistently
6. **Perturbations** - Atmospheric drag, solar radiation pressure, lunar/solar gravity, and
   Earth's non-spherical gravity field all alter orbits unpredictably

**Plain English:**
Imagine trying to track thousands of bullets flying around the Earth at 17,000 mph, but:
- You can only look at any particular patch of sky for a few minutes at a time
- The bullets do not have name tags
- The wind keeps changing their paths
- You are trying to do this with telescopes that can only look in one direction at once
- And there are millions more bullets too small to even see

## 2.3 The "Uncorrelated Track" Problem

**Technical:**
An Uncorrelated Track (UCT) is a series of observations that cannot be associated with any
known object in the space catalog. UCTs arise from:
- Newly launched objects not yet cataloged
- Known objects that have maneuvered or been perturbed off their predicted path
- Debris from breakup or collision events
- Sensor artifacts and false detections
- Catalog maintenance failures

The UCT Processing (UCTP) problem is: given a set of decorrelated observations stripped of
all identifying information, can an algorithm:
1. **Cluster** which observations belong together (same object)?
2. **Determine** the orbit of each cluster (Initial Orbit Determination)?
3. **Refine** that orbit estimate for better accuracy?
4. **Correlate** the orbit with known catalog objects?

**Plain English:**
Imagine you are a detective. Someone hands you a box of puzzle pieces from multiple
different puzzles, all mixed together, with no picture on the box. Your job is to:
1. Sort out which pieces belong to which puzzle
2. Figure out what picture each puzzle makes
3. Check if any of those pictures match photos in your database

That is exactly the UCTP problem: sorting mixed-up observations, figuring out orbits, and
matching them to known satellites.

## 2.4 What Happens When We Lose Track

**Technical:**
When space objects become untracked or misidentified:
- **Collision risk assessment fails** - Conjunction warnings cannot be issued for unknown
  objects, leading to potential hypervelocity collisions (relative velocity up to 15 km/s)
- **Kessler Syndrome** - Collisions generate debris, which causes more collisions, in a
  cascading chain reaction
- **Asset protection fails** - High-value satellites (ISS, GPS, communications) cannot
  maneuver to avoid threats they do not know about
- **Treaty verification** - Cannot verify compliance with space behavior norms

**Plain English:**
If we lose track of space junk, satellites can get destroyed. A paint chip moving at
17,000 mph hits like a bullet. A collision between two large objects could create thousands
of new debris fragments, each one a potential bullet aimed at other satellites. In the
worst case, a chain reaction of collisions could make entire orbital regions unusable for
decades -- no more GPS, no more weather satellites, no more satellite internet.

## 2.5 Scale of the Problem

```
                        SPACE OBJECT TRACKING
                        =====================

  Altitude (km)
  36,000+ .......... GEO Belt - Communications, Weather satellites
     |                (~1,500 tracked objects, sparse observation)
     |
  20,200  .......... MEO - GPS/Navigation constellation
     |                (~2,000 objects, moderate observation)
     |
   2,000  .......... Upper LEO boundary
     |                |
     |   LEO          | ~25,000 tracked objects
     |   (most        | Millions of untracked debris
     |    congested)  | ISS, Starlink, imaging sats
     |                |
     400  ..........  ISS altitude
     |                |
     200  .......... Lower LEO boundary (atmospheric decay)
     |
  ------  ========== EARTH SURFACE ==========

  Sensors: Ground-based optical telescopes, radar, space-based sensors
  Coverage: Intermittent - objects observed only during passes
  Speed: 3-8 km/s orbital velocity
  Catalog: ~30,000+ tracked objects (as of 2025)
```

---

# 3. Orbital Mechanics Fundamentals

## 3.1 Orbits and Orbital Regimes

**Technical:**
An orbit is a gravitationally bound trajectory around Earth. Orbits are classified into
regimes based on altitude and shape. The SDA-TAP-SpOC system recognizes four primary
orbital regimes, defined by semi-major axis (a) and eccentricity (e):

| Regime | Full Name | Semi-Major Axis | Altitude Range | Period | Characteristics |
|--------|-----------|-----------------|----------------|--------|-----------------|
| **LEO** | Low Earth Orbit | a <= 8,378 km | 200 - 2,000 km | ~90-127 min | Most congested; atmospheric drag significant; short revisit times |
| **MEO** | Medium Earth Orbit | 8,378 < a < 42,164 km | 2,000 - 35,786 km | ~2-24 hrs | GPS/navigation; moderate drag; longer observation windows |
| **GEO** | Geostationary Earth Orbit | a >= 42,164 km | ~35,786 km | ~24 hrs | Appears stationary; communications/weather; very long track arcs |
| **HEO** | Highly Elliptical Orbit | e >= 0.7 | Variable | Variable | Highly eccentric; dwells at apogee; intelligence/comms |

**Plain English:**
Different satellites orbit at different heights, and each height has its own character:
- **LEO** (Low): Close to Earth, zipping around every 90 minutes. This is where the ISS
  and most imaging satellites live. It is also the most crowded.
- **MEO** (Medium): Where GPS satellites live. They take a few hours to go around.
- **GEO** (Geostationary): So far out that they orbit once per day, matching Earth's
  rotation. They appear to hover over one spot. Weather and TV satellites live here.
- **HEO** (Highly Elliptical): Egg-shaped orbits that swing close to Earth on one side
  and far away on the other. They "hang" over one hemisphere for hours.

```
                              ORBITAL REGIMES

                        .  *  .  GEO (~36,000 km)
                     *           *
                   *    . * .      *
                  *   *       *     *
                 *  *   MEO    *    *
                 * *  (2,000-   *   *
                 * *  36,000km) *   *
                 * *           *    *
                  *  * . _ . *     *
                   *   LEO       *      HEO: Highly elliptical,
                     * (200-   *        extends far from Earth
                      2,000km)          on one side
                        . * .
                       /     \
                      | EARTH |
                       \_____/
```

## 3.2 Keplerian Orbital Elements

**Technical:**
Any orbit in a two-body system can be completely described by six Keplerian orbital
elements. These are the fundamental parameters stored in TLEs and used throughout the
SDA-TAP-SpOC system:

### Semi-Major Axis (a)
- **Technical:** Half the longest diameter of the orbital ellipse, measured in kilometers.
  Determines the orbital energy and period. For circular orbits, equals the orbital radius.
  T = 2*pi * sqrt(a^3 / mu), where mu = 398,600.4418 km^3/s^2 (Earth's gravitational
  parameter).
- **Plain English:** How big the orbit is. A bigger number means a higher, slower orbit.

### Eccentricity (e)
- **Technical:** A dimensionless number between 0 and 1 (for bound orbits) describing how
  elongated the ellipse is. e=0 is a perfect circle; e approaching 1 is extremely
  elongated. In the system, HEO is defined as e >= 0.7.
- **Plain English:** How egg-shaped the orbit is. Zero means a perfect circle; close to 1
  means a very stretched oval.

### Inclination (i)
- **Technical:** The angle between the orbital plane and the equatorial plane, measured in
  degrees (0-180). i=0 is equatorial; i=90 is polar; i>90 is retrograde.
- **Plain English:** How tilted the orbit is relative to the equator. Zero means it goes
  around the equator; 90 means it goes over the poles.

### Right Ascension of the Ascending Node (RAAN / Omega)
- **Technical:** The angle in the equatorial plane from the vernal equinox to the point
  where the orbit crosses the equator going north (ascending node), measured in degrees
  (0-360).
- **Plain English:** Which direction the orbit's tilt faces. If inclination is "how much
  is it tilted," RAAN is "which way is it tilted."

### Argument of Perigee (omega)
- **Technical:** The angle in the orbital plane from the ascending node to the point of
  closest approach (perigee), measured in degrees (0-360). Defines the orientation of the
  ellipse within the orbital plane.
- **Plain English:** Where in the orbit the satellite comes closest to Earth. It is like
  saying "the low point of the oval is at the 3 o'clock position."

### Mean Anomaly (M)
- **Technical:** An angle that increases uniformly with time from 0 to 360 degrees over
  one orbital period. Not a true geometric angle -- it is a mathematical construct that
  parameterizes position along the orbit in a way that is linear in time.
- **Plain English:** Where the satellite is right now along its orbit. It is like a clock
  hand that ticks evenly around the orbit -- 0 degrees means it just passed the closest
  point, 180 means it is at the farthest point.

```
     KEPLERIAN ORBITAL ELEMENTS
     ==========================

                  Ascending Node
                       |
              RAAN     |     Argument of
             angle     |      Perigee angle
               \       |       /
                \      |      /
     Vernal -----*=====X=====*-----> Orbit direction
     Equinox         / | \
      direction     /  |  \       Perigee (closest
                   /   |   \       point to Earth)
                  /    |    \        |
                 /  i  |     \       v
                /  (incl.)    *------*
               /       |    /         \
              /        |   /    a      \
             /         |  / (semi-      \
            /          | /   major       \
           /           |/    axis)        \
          /         EARTH                  \
         /             |         e          \
        /              |     (eccentricity   *  Apogee (farthest
       *               |      = shape)      /    point)
        \              |                   /
         \             |                  /
          \            |                 /
           *-----------+-----------*---*
                       |
                    Orbital Plane
                    (tilted by i from equator)
```

### Summary Table

| Element | Symbol | Unit | What It Controls | Database Column |
|---------|--------|------|------------------|-----------------|
| Semi-Major Axis | a | km | Orbit size & period | `semi_major_axis_km` |
| Eccentricity | e | dimensionless | Orbit shape (circle vs ellipse) | `eccentricity` |
| Inclination | i | degrees | Orbit tilt relative to equator | `inclination` |
| RAAN | Omega | degrees | Orientation of tilt | `raan` |
| Argument of Perigee | omega | degrees | Where closest point is | `arg_perigee` |
| Mean Anomaly | M | degrees | Where satellite is now | `mean_anomaly` |

## 3.3 Apogee & Perigee

**Technical:**
- **Perigee:** The point in an orbit closest to Earth's center.
  Perigee altitude = a(1 - e) - R_Earth, where R_Earth = 6,378.137 km
- **Apogee:** The point in an orbit farthest from Earth's center.
  Apogee altitude = a(1 + e) - R_Earth
- The database stores these as `perigee` and `apogee` fields in element sets.

**Plain English:**
Every elliptical orbit has a high point and a low point. The low point (closest to Earth)
is called perigee. The high point (farthest from Earth) is called apogee. For a perfectly
circular orbit, these are the same. For an egg-shaped orbit, the difference can be
thousands of kilometers.

## 3.4 Orbital Period & Mean Motion

**Technical:**
- **Orbital Period (T):** Time for one complete orbit.
  T = 2*pi * sqrt(a^3 / mu), stored in `period_minutes`.
- **Mean Motion (n):** Number of orbits per day.
  n = 86400 / T (revolutions per day), stored in `mean_motion` (rev/day).
- **Mean Motion Dot (n-dot):** First time derivative of mean motion; indicates orbit decay
  rate. Stored in `meanMotionDot`.
- **Mean Motion Double-Dot (n-double-dot):** Second time derivative. Stored in
  `meanMotionDDot`.

**Plain English:**
The period is how long one lap around Earth takes. Mean motion is how many laps per day.
The ISS does about 15.5 laps per day (period ~92 minutes). A GEO satellite does exactly
1 lap per day (period ~24 hours). "Mean motion dot" tells you if the orbit is getting
smaller (decaying) -- a positive value means it is speeding up and spiraling inward.

## 3.5 Epoch

**Technical:**
The epoch is the reference timestamp at which the orbital elements are valid. Orbital
elements change over time due to perturbations, so they are only accurate at their epoch.
The further you propagate from the epoch, the less accurate the prediction becomes. Stored
as ISO 8601 timestamp (e.g., "2025-06-23T19:45:00.225171Z") in the `epoch` field.

**Plain English:**
The epoch is the "as of" date. Saying "the satellite is here at these coordinates" only
makes sense if you also say "as of this specific moment." The orbital elements are like a
snapshot -- they are only perfectly accurate at the instant they were taken. The further
you try to predict into the future from that snapshot, the less accurate it gets.

## 3.6 B* Drag Term

**Technical:**
B* (B-star) is a modified ballistic coefficient in the SGP4 propagation model that
accounts for atmospheric drag effects. It is defined as:
B* = (1/2) * Cd * A / m * rho_0
where Cd is the drag coefficient, A is the cross-sectional area, m is mass, and rho_0 is
a reference atmospheric density. Stored in the `b_star` field of element sets. Units are
inverse Earth radii. B*=0 means no drag modeled.

**Plain English:**
B-star is a single number that captures how much the atmosphere slows down a satellite.
A big, light satellite (like a solar panel fragment) has a high B-star and gets slowed
down a lot. A small, dense satellite (like a solid metal sphere) has a low B-star and
barely notices the atmosphere. It is crucial for predicting how quickly an orbit decays.

---

# 4. Data Formats

## 4.1 TLE (Two-Line Element Set)

**Technical:**
A Two-Line Element Set (TLE) is a standardized data format encoding orbital elements for
use with the SGP4/SDP4 propagation models. Defined by NORAD, TLEs consist of a title line
(optional) and two 69-character data lines. TLEs are the lingua franca of space tracking --
nearly every space catalog distributes orbital data in TLE format.

**Plain English:**
A TLE is a compact recipe for describing where a satellite is and how it is moving. It
packs all the orbital information into exactly two lines of text, using a format invented
in the 1960s. Every space-tracking organization in the world speaks TLE.

### Line-by-Line Breakdown

**Line 1 Format:**
```
1 NNNNNC NNNNNAAA NNNNN.NNNNNNNN +.NNNNNNNN +NNNNN-N +NNNNN-N N NNNNN
```
```
Example: 1 25544U 98067A   25183.86865372  .00000000  00000+0  00000+0 2 99998
         | |     |        |                |          |        |       | |
         | |     |        Epoch            n-dot/2    n-ddot/6 B*     Eph Set#
         | |     COSPAR ID (Int'l Designator)                          Type
         | Catalog Number + Classification
         Line Number
```

| Field | Columns | Description | Example |
|-------|---------|-------------|---------|
| Line Number | 1 | Always "1" | 1 |
| Catalog Number | 3-7 | NORAD catalog number | 25544 |
| Classification | 8 | U=Unclassified, C=Classified, S=Secret | U |
| Int'l Designator | 10-17 | Launch year + launch number + piece | 98067A |
| Epoch Year | 19-20 | Last 2 digits of year | 25 |
| Epoch Day | 21-32 | Day of year + fractional day | 183.86865372 |
| Mean Motion Dot | 34-43 | First derivative of mean motion / 2 | .00000000 |
| Mean Motion DDot | 45-52 | Second derivative of mean motion / 6 | 00000+0 |
| B* Drag Term | 54-61 | Modified ballistic coefficient | 00000+0 |
| Ephemeris Type | 63 | 0=SGP4, 2=SGP4 (most common) | 2 |
| Element Set Number | 65-68 | Incrementing count of element sets | 9999 |
| Checksum | 69 | Modulo-10 checksum | 8 |

**Line 2 Format:**
```
2 NNNNN NNN.NNNN NNN.NNNN NNNNNNN NNN.NNNN NNN.NNNN NN.NNNNNNNNNNNNNN
```
```
Example: 2 25544  51.6400  247.4627 0006703  130.5360  229.5681 15.54174292    0
         | |      |        |        |        |         |        |
         | |      Incl(deg) RAAN    Ecc      ArgPerigee MeanAnom MeanMotion
         | Catalog Number                                        (rev/day)
         Line Number
```

| Field | Columns | Description | Example |
|-------|---------|-------------|---------|
| Line Number | 1 | Always "2" | 2 |
| Catalog Number | 3-7 | NORAD catalog number (must match Line 1) | 25544 |
| Inclination | 9-16 | Degrees | 51.6400 |
| RAAN | 18-25 | Right Ascension of Ascending Node (degrees) | 247.4627 |
| Eccentricity | 27-33 | Decimal point assumed (e.g., 0006703 = 0.0006703) | 0006703 |
| Arg of Perigee | 35-42 | Degrees | 130.5360 |
| Mean Anomaly | 44-51 | Degrees | 229.5681 |
| Mean Motion | 53-63 | Revolutions per day | 15.54174292 |
| Rev Number at Epoch | 64-68 | Revolution count since launch | 0 |
| Checksum | 69 | Modulo-10 checksum | 0 |

### TLE Limitations

- Accuracy degrades rapidly away from epoch (especially in LEO)
- Only valid with SGP4/SDP4 propagation model (not general-purpose)
- No covariance/uncertainty information
- Fixed format limits precision (especially for eccentricity)
- Assumes specific perturbation model; not compatible with high-fidelity propagators

### TrackTLE (Project-Specific Concept)

**Technical:**
A TrackTLE is a TLE generated by performing Initial Orbit Determination (IOD) on a single
track of observations from a single observatory. TrackTLEs are less accurate than catalog
TLEs because catalog TLEs are refined using multiple observation passes from multiple
sensors. The system generates TrackTLEs using a Modified Gauss Method followed by Orekit's
BatchLSEstimator with SGP4 propagation.

**Plain English:**
A regular TLE is highly refined -- it uses data from many sensors over many passes. A
TrackTLE is a rough first draft, made from just one observing session at one telescope.
It is deliberately crude because that is what a real UCTP would have to work with.

### TLE JSON Format (as used in this system)

The system stores TLEs as JSON objects with parsed fields:
```json
{
  "idElset": "d688d8a2-81d3-4ceb-8032-c945128b5a41",
  "epoch": "2025-07-02T20:50:51.681027Z",
  "meanMotion": 1.0027191749074,
  "eccentricity": 0.00500568344535229,
  "inclination": 6.64966633097932,
  "raan": 15.1408773270208,
  "argOfPerigee": 49.8819406821671,
  "meanAnomaly": 274.278737836812,
  "bStar": 0,
  "semiMajorAxis": 42164.6968714354,
  "period": 1436.09500649369,
  "apogee": 42375.759996543,
  "perigee": 41953.6337463278,
  "line1": "1 99999U 00000A   25183.86865372 ...",
  "line2": "2 99999   6.6497  15.1409 0050057 ...",
  "source": "EXO",
  "dataMode": "REAL"
}
```

## 4.2 State Vectors

**Technical:**
A state vector is a set of six numbers that completely define an object's instantaneous
translational state: three position components (X, Y, Z) and three velocity components
(Vx, Vy, Vz), all relative to a specified reference frame at a given epoch.

Standard representation:
```
State Vector = [x, y, z, vx, vy, vz]
                |-------|  |---------|
                Position   Velocity
                (km)       (km/s)
```

Stored in the database as:
```sql
x_pos DECIMAL(16,6)    -- km, J2000 ECI
y_pos DECIMAL(16,6)    -- km, J2000 ECI
z_pos DECIMAL(16,6)    -- km, J2000 ECI
x_vel DECIMAL(16,9)    -- km/s, J2000 ECI
y_vel DECIMAL(16,9)    -- km/s, J2000 ECI
z_vel DECIMAL(16,9)    -- km/s, J2000 ECI
```

**Plain English:**
A state vector is the simplest way to say "where something is and where it is going."
Six numbers: three for position (left-right, forward-back, up-down) and three for velocity
(how fast in each direction). It is like saying "the car is at coordinates (3, 5, 0) and
moving at (60 mph east, 0 mph north, 0 mph up)."

### UCTP Output Format (State Vector Mode)

When a UCTP outputs state vectors, the expected JSON format is:
```json
{
  "idStateVector": "unique-alphanumeric-string",
  "sourcedData": ["observation-id-1", "observation-id-2", "..."],
  "sourcedDataTypes": ["EO", "EO", "EO"],
  "epoch": "2025-06-23T19:45:00.000000Z",
  "xpos": 12345.678,
  "ypos": -23456.789,
  "zpos": 34567.890,
  "xvel": 1.234567,
  "yvel": -2.345678,
  "zvel": 3.456789,
  "referenceFrame": "J2000",
  "covReferenceFrame": "J2000",
  "cov": [21 values: lower triangular covariance matrix elements]
}
```

The `sourcedData` field is critical -- it lists which observation IDs from the benchmark
dataset this candidate orbit was built from. This is used for binary metric evaluation.

## 4.3 Covariance Matrix

**Technical:**
The covariance matrix is a 6x6 symmetric positive semi-definite matrix representing the
uncertainty in a state vector estimate. Element (i,j) represents the covariance between
state components i and j. The diagonal elements are the variances (squared standard
deviations) of each component.

```
         x      y      z      vx     vy     vz
    x  [sigma_xx  ...   ...    ...    ...    ...  ]
    y  [cov_yx    sigma_yy ... ...    ...    ...  ]
    z  [cov_zx    cov_zy  sigma_zz   ...    ...  ]
    vx [cov_vxx   cov_vxy cov_vxz  sigma_vxvx ... ]
    vy [cov_vyx   cov_vyy cov_vyz  cov_vyvx sigma_vyvy]
    vz [cov_vzx   cov_vzy cov_vzz  cov_vzvx cov_vzvy sigma_vzvz]
```

In the system, covariance is stored as:
- JSON array of 21 values (lower triangular elements) in UCTP output
- Full 6x6 matrix as JSON in the database (`covariance` column)
- Propagated via Monte Carlo simulation (N sample points, default 100)

**Plain English:**
The covariance matrix answers "how confident are we?" about the state vector. If the
position uncertainty is small, we know pretty precisely where the satellite is. If it is
large, we are less sure. The matrix also captures correlations -- for example, if we are
uncertain about the position in one direction, we might be simultaneously uncertain about
the velocity in another direction. Think of it as an "uncertainty cloud" around the
satellite's predicted position.

### Covariance Propagation

The system propagates covariance using Monte Carlo simulation:
1. Sample N points from the multivariate normal distribution defined by the mean state
   vector and covariance matrix
2. Propagate each sample point forward in time using Orekit's numerical integrator
3. Discard any samples that propagate inside Earth's ellipsoid
4. Compute the covariance of the resulting distribution at the target epoch

## 4.4 Ephemeris

**Technical:**
An ephemeris is a time-ordered sequence of state vectors representing the predicted
trajectory of a space object. It is generated by propagating an initial state forward (or
backward) in time using a force model. The system uses Orekit's DormandPrince853 numerical
integrator for high-fidelity ephemeris generation.

**Plain English:**
An ephemeris is a table of predicted positions over time -- "at 1:00 PM the satellite will
be here, at 1:01 PM it will be there, at 1:02 PM it will be over there." It is the output
of running the orbital prediction math forward in time. Think of it as a flight plan for a
satellite.

### Coordinate Frames

State vectors and covariance matrices must be specified in a reference frame. The system
handles multiple frames (detailed in Section 13), converting everything to J2000/EME2000
for evaluation:

| Frame | Full Name | Used By | Fixed To |
|-------|-----------|---------|----------|
| J2000 / EME2000 | Earth Mean Equator 2000 | Primary evaluation frame | Stars (inertial) |
| TEME | True Equator Mean Equinox | TLE/SGP4 native frame | Stars (approx.) |
| GCRF | Geocentric Celestial Reference Frame | High-precision inertial | Stars (precise) |
| ITRF / ECEF | International Terrestrial Reference Frame | Ground-fixed measurements | Earth surface |
| EFG / TDR | Earth-Fixed Greenwich | UDL some data | Earth surface |

---

# 5. Sensors and Observations

## 5.1 How We Observe Space Objects

**Technical:**
Space surveillance sensors detect and measure space objects through three primary
phenomenologies: optical/electro-optical (EO), radar, and radio frequency (RF). Each sensor
type produces different measurement types with different accuracies, coverage patterns, and
limitations.

**Plain English:**
We watch space objects in three ways:
1. **Telescopes** (optical) - Take pictures of the sky and see satellites as points of light
2. **Radar** - Bounce radio waves off objects and listen for the echo
3. **Radio receivers** (RF) - Listen for radio signals that satellites broadcast

```
     SENSOR TYPES AND WHAT THEY MEASURE
     ====================================

     OPTICAL (EO)                RADAR                    RF
     ============                =====                    ==
     Telescope + Camera          Transmit + Receive       Receive only

        /\                        /\     /\                  /\
       /  \  Starlight           /  \   /  \                /  \
      / ** \  + satellite       /    \ /    \  Echo        / ~~ \
     /  **  \  reflection      / Tx   X  Rx  \           / ~~   \
    /________\                /______/ \______\         /________\

    Measures:                 Measures:                 Measures:
    - RA (Right Ascension)   - Range (distance)        - Signal strength
    - Dec (Declination)      - Range Rate (velocity)   - Frequency
    - Magnitude (brightness) - Azimuth (direction)     - Doppler shift
    - Time                   - Elevation               - Time
                             - Time

    Best for:                Best for:                  Best for:
    - Deep space (GEO)       - LEO tracking             - Active satellites
    - Non-radiating objects  - Precise range             - Characterization
    - Large surveys          - All-weather               - Passive detection

    Limitations:             Limitations:               Limitations:
    - Night/clear sky only   - Power-limited range      - Only active sats
    - Angles only (no range) - LEO focus                - Need known freq
    - Weather dependent      - Expensive to operate     - Limited positional
```

## 5.2 What Each Sensor Measures

### Optical/Electro-Optical (EO) Observations

**Technical:**
EO sensors measure the angular position of a space object on the celestial sphere:
- **Right Ascension (RA):** Eastward angle along the celestial equator from the vernal
  equinox, in degrees (0-360). Stored as `ra DECIMAL(12,8)` in the database.
- **Declination (Dec):** Angle north/south of the celestial equator, in degrees (-90 to
  +90). Stored as `declination DECIMAL(12,8)`.
- **Magnitude (mag):** Apparent visual brightness; lower = brighter. A change of 5
  magnitudes equals 100x brightness ratio.
- **Azimuth/Elevation:** Local horizon coordinates of the observation.
- **Sensor position:** Latitude, longitude, altitude of the observatory.

**Plain English:**
A telescope sees a satellite as a dot of light against the stars. It measures where that
dot is on the sky (RA and Dec are like longitude and latitude for the sky) and how bright
it is. It does NOT measure how far away the object is -- just which direction to point.

### Radar Observations

**Technical:**
Radar sensors measure:
- **Range:** Distance to object in km. Stored as `range_km DECIMAL(12,4)`.
- **Range Rate:** Radial velocity (approach/recede speed) in km/s. Stored as
  `range_rate_km_s DECIMAL(10,6)`.
- **Azimuth:** Horizontal pointing angle in degrees. Stored as `azimuth DECIMAL(12,8)`.
- **Elevation:** Vertical pointing angle in degrees. Stored as `elevation DECIMAL(12,8)`.

**Plain English:**
Radar sends out a radio pulse and listens for the echo. From the echo, it knows:
- How far away the object is (from the delay)
- How fast it is approaching or receding (from the frequency shift)
- Which direction it is in (from where the antenna is pointing)

### RF Observations

**Technical:**
RF sensors passively receive electromagnetic signals broadcast by active satellites. They
measure signal characteristics including frequency, power, bandwidth, and modulation. In
the SDA-TAP-SpOC system, RF observations from networks like SatNOGS provide supplementary
data for multi-phenomenology datasets.

**Plain English:**
RF sensors are like radio antennas that listen for signals from satellites. They can only
detect satellites that are actively transmitting (broadcasting their own radio signals).

### Sensor Comparison Table

| Sensor Type | Measurements | Typical Accuracy | Best For | Limitation |
|-------------|-------------|------------------|----------|------------|
| **Optical (EO)** | RA, Dec, magnitude | ~1 arcsecond angular | GEO, deep space | Night/clear sky only; no range |
| **Radar** | Range, range rate, az, el | ~10m range, ~1 cm/s RR | LEO | Power-limited range; expensive |
| **RF** | Frequency, signal strength | Varies widely | Active satellites only | Cannot detect passive debris |

## 5.3 Specific Sensor Systems

### GEODSS (Ground-based Electro-Optical Deep Space Surveillance)

**Technical:**
GEODSS is a network of three optical telescope sites operated by the U.S. Space Force for
tracking objects in deep space (primarily GEO and HEO). Each site has multiple 1-meter
telescopes with CCD sensors. Sites are located in Hawaii, Diego Garcia, and Maui.

**Plain English:**
GEODSS is a set of big military telescopes specifically designed to watch the geostationary
belt where communications and weather satellites live. They photograph the sky repeatedly
and look for dots that move differently from stars.

### SBSS (Space-Based Space Surveillance)

**Technical:**
SBSS is a satellite in LEO carrying an optical sensor to observe objects in GEO and other
high orbits. Being above the atmosphere, it can observe 24/7 without weather or daylight
limitations.

**Plain English:**
SBSS is a spy satellite that watches other satellites. Being in space itself means it does
not have to worry about clouds or daytime, so it can observe all the time.

### Commercial EO

**Technical:**
Commercial electro-optical sensors from companies like ExoAnalytic Solutions (EXO) provide
supplementary observation data. In the system, the `source` field value "EXO" indicates
ExoAnalytic data, and the sensor ID format "EXO7151" identifies specific commercial sensors.

**Plain English:**
Private companies also run telescope networks that track satellites. Their data supplements
the military sensors and provides more observations, especially of the geostationary belt.

## 5.4 Observations vs Tracks

**Technical:**
- **Observation:** A single measurement of a space object at a specific time. In the
  database, each observation has a unique `id` and an `ob_time` timestamp.
- **Track:** A time-ordered series of observations from the same sensor believed to belong
  to the same object during a single pass. Observations are grouped into tracks using a
  time-gap cutoff (default 90 minutes). Each observation has a `track_id` field.
- **Pass:** A single overhead passage of a satellite as seen from a ground station.

The system bins observations into tracks in `dataManipulation.binTracks()` using a temporal
cutoff. Observations separated by more than the cutoff (default 90 minutes for LEO) are
assigned to different tracks.

**Plain English:**
One observation is one snapshot -- a single measurement of where an object was at one
moment. A track is a series of snapshots from the same telescope during one overhead pass.
If you watch a satellite go from horizon to horizon and take a picture every 10 seconds,
all those pictures together form one track.

## 5.5 Observation Quality

### Orbital Coverage

**Technical:**
Orbital coverage quantifies what fraction of an object's orbit is covered by observations.
The system uses a specialized geometric definition:

1. Fit all observations to their nearest approach on the reference orbit
2. Project each fitted observation through the orbit's geometric center onto the
   circumscribing circle of the orbital ellipse
3. Compute the convex hull area of the projected points
4. Normalize by the circumscribing circle's area

This definition avoids periapsis/apoapsis bias from eccentricity and handles the discrete,
non-uniform nature of real observation data.

Coverage thresholds vary by regime:
- LEO: Low coverage < 0.0213%
- MEO: Low coverage < 0.0449%
- GEO: Low coverage < 41.656%

**Plain English:**
Orbital coverage asks: "How much of the satellite's path around Earth did we actually see?"
If we only caught it during one small part of its orbit, coverage is low. If we observed it
throughout most of its orbit, coverage is high. The exact calculation projects all
observations onto a circle and measures how much of that circle they fill up.

### Track Gaps

**Technical:**
Track gap is the longest duration between consecutive observations of an object, measured
in multiples of the orbital period. A "long" track gap is defined as exceeding 2 orbital
periods. Calculated using the `QUERY_TRACK_GAPS` SQL query in the database.

**Plain English:**
Track gap is the biggest hole in your observation timeline. If you saw a satellite at noon
and then not again until the next day, that is a big gap. Measured relative to how long
one orbit takes -- a gap of "2 periods" means you missed 2 full laps.

### Observation Density

**Technical:**
Total number of unique observations per object per 3-day timespan. Low: < 50 observations;
Standard: 50-150 observations. Objects with > 150 observations are either excluded or
downsampled to standard density.

**Plain English:**
How many individual measurements we have for each satellite. More measurements generally
means better data, but we want to test algorithms on realistic data, so we sometimes
deliberately thin the data out.

---

# 6. Data Sources

## 6.1 Overview

The SDA-TAP-SpOC system integrates data from multiple sources, each providing different
types of information. Sources range from restricted government databases to open-access
community data.

```
     DATA SOURCES FLOWING INTO SDA-TAP-SpOC
     ========================================

     RESTRICTED ACCESS               OPEN ACCESS
     =================               ===========

     +--------+    +--------+        +---------+    +------+
     |  UDL   |    | Space  |        | CelesTrak|   | GCAT |
     | (Gov't |    | Track  |        | (Open   |    |(57K+ |
     | Obs DB)|    | (.org) |        |  TLEs)  |    |objs) |
     +---+----+    +---+----+        +----+----+    +--+---+
         |             |                  |            |
         v             v                  v            v
     +----------------------------------------------------+
     |                                                    |
     |            SDA-TAP-SpOC UCT Benchmark              |
     |                                                    |
     |   +----------+  +----------+  +----------+        |
     |   |Satellites|  |Observa-  |  |Element   |        |
     |   |Table     |  |tions     |  |Sets      |        |
     |   |(enriched)|  |Table     |  |Table     |        |
     |   +----------+  +----------+  +----------+        |
     |                                                    |
     +----------------------------------------------------+
         ^             ^                  ^            ^
         |             |                  |            |
     +---+----+    +---+----+        +----+----+   +--+---+
     |  ESA   |    | SatNOGS|        |  ILRS   |   | UCS  |
     |Discoweb|    | (RF    |        | (Laser  |   |(Sat  |
     |(debris)|    |  obs)  |        |  truth) |   | meta)|
     +--------+    +--------+        +---------+   +------+

     RESTRICTED                       OPEN
```

## 6.2 UDL (Unified Data Library) - Primary Source

**Technical:**
The Unified Data Library is the primary observation data source for the SDA-TAP-SpOC
system. It is a U.S. government database providing space surveillance observations,
element sets, and state vectors.

- **Authentication:** Bearer token (Base64-encoded API credentials)
- **Data available:** EO observations (RA/Dec/Az/El/range), element sets (TLEs), state
  vectors, sensor metadata
- **Query method:** REST API with time-windowed batch queries (`asyncUDLBatchQuery`)
- **Rate limit:** Configurable via `dt` parameter (default 0.1 seconds between requests)
- **Data mode:** `REAL` (actual observations) or `SIMULATED`
- **Database record:** `data_sources` table id=1, source_name='UDL', source_type='OBSERVATION'

**Plain English:**
UDL is the main government database of satellite observations. It is like a massive library
of every time a military sensor saw a satellite. You need a special access token to use it.
The system pulls observations from UDL in 10-minute time chunks, searches for good time
windows, and builds datasets from what it finds.

### UDL Observation Fields (EO)

Key fields from a UDL EO observation record:

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Unique observation identifier |
| `obTime` | ISO datetime | Observation timestamp |
| `satNo` | integer | NORAD catalog number (stripped during decorrelation) |
| `idSensor` | string | Sensor identifier (e.g., "EXO7151") |
| `ra` | float (degrees) | Right Ascension |
| `declination` | float (degrees) | Declination |
| `azimuth` | float (degrees) | Azimuth from sensor |
| `elevation` | float (degrees) | Elevation from sensor |
| `range` | float (km) | Range to object (if available) |
| `mag` | float | Apparent magnitude |
| `senx/seny/senz` | float (km) | Sensor position in ECI |
| `senvelx/y/z` | float (km/s) | Sensor velocity in ECI |
| `source` | string | Data source identifier (e.g., "EXO") |
| `dataMode` | string | "REAL" or "SIMULATED" |
| `type` | string | "OPTICAL", "RADAR", etc. |

## 6.3 Space-Track.org

**Technical:**
Space-Track.org is the official public interface to the U.S. Space Surveillance Network
catalog, operated by the 18th Space Defense Squadron. It provides:
- Two-Line Element Sets (TLEs) for all publicly tracked objects
- Historical element sets
- Conjunction Data Messages (CDMs)
- Decay/reentry predictions

- **Authentication:** Username + password (stored in `credentials` table as service
  `spacetrack`, type `username_password`)
- **Database record:** `data_sources` table id=6, source_name='SPACE_TRACK'

**Plain English:**
Space-Track is the official U.S. government website where anyone with an approved account
can download satellite orbit data. It is the main public source for TLEs -- the standard
way satellite orbits are described. You need to create an account and log in.

## 6.4 CelesTrak

**Technical:**
CelesTrak is a service that redistributes TLE data from Space-Track.org in more accessible
formats. Operated by Dr. T.S. Kelso, it provides current TLEs organized by satellite
category (e.g., active, weather, GPS, Starlink).

- **Authentication:** None required
- **Data format:** Two-line element sets, 3-line format, OMM JSON/XML
- **Update frequency:** Multiple times daily
- **Use in project:** Quick TLE access for specific satellite categories

**Plain English:**
CelesTrak is a free, public website that makes satellite orbit data easy to access. While
Space-Track requires a login and has strict usage rules, CelesTrak provides the same basic
TLE data in a simpler, no-login-needed format. Great for quick lookups.

## 6.5 UCS (Union of Concerned Scientists) Satellite Database

**Technical:**
The UCS Satellite Database is a comprehensive listing of operational satellites with
metadata not available in TLE catalogs:
- Purpose (communications, Earth observation, technology development, etc.)
- Operator/owner organization
- Launch date and launch site
- Mass (kg) and power (watts)
- Expected lifetime

- **Authentication:** None (public download)
- **Database record:** `data_sources` table id=4, source_name='UCS'
- **Sync tracking:** `ucs_synced_at` column in `satellites` table
- **Data fields populated:** `purpose`, `operator`, `launch_site`, `power_watts`

**Plain English:**
The UCS database tells us what each satellite actually does and who owns it. TLEs only tell
us where a satellite is -- the UCS database tells us it is a "communications satellite
owned by Intelsat, launched from Cape Canaveral, weighing 3,000 kg." This context helps us
understand what we are tracking.

## 6.6 GCAT (General Catalog of Artificial Space Objects)

**Technical:**
GCAT is a comprehensive catalog maintained by Jonathan McDowell (Harvard-Smithsonian Center
for Astrophysics) containing 57,000+ space objects with detailed metadata:
- Object type (payload, rocket body, debris, etc.)
- COSPAR international designator
- Launch site and launch vehicle
- Mass estimates
- Status (in orbit, decayed, etc.)

- **Authentication:** None (CC-BY license)
- **Database record:** `data_sources` table id=3, source_name='GCAT'
- **Sync tracking:** `gcat_synced_at` column in `satellites` table
- **Data fields populated:** `object_type`, `cospar_id`, `launch_date`, `mass_kg`

**Plain English:**
GCAT is one person's incredibly detailed catalog of everything humans have ever launched
into space. It tells us what type of object something is (working satellite vs. spent
rocket body vs. debris fragment), when and where it was launched, and how heavy it is.
With 57,000+ objects, it is one of the most complete catalogs available.

## 6.7 ESA DiscoWeb

**Technical:**
ESA's DISCOS (Database and Information System Characterising Objects in Space) database,
accessible via DiscoWeb API, provides physical characterization data:
- Mass (kg)
- Cross-sectional area (m^2)
- Drag coefficient (Cd), default 2.5
- Solar radiation pressure coefficient (Cr), default 1.5

- **Authentication:** Bearer token (stored as service `esa` in credentials table)
- **API:** REST with JSON:API format
- **Data fields populated:** `mass_kg`, `cross_section_m2`, `drag_coeff`, `srp_coeff`

These physical properties are essential for orbit propagation -- the force model needs mass
and area to compute atmospheric drag and solar radiation pressure effects.

**Plain English:**
ESA DiscoWeb tells us the physical properties of space objects -- how heavy they are, how
big they are, and how much they are affected by air resistance and sunlight pressure. This
is critical because the orbit prediction math needs to know these properties to make
accurate predictions. A feather-light solar panel fragment and a dense steel ball move very
differently through the thin upper atmosphere.

## 6.8 SatNOGS

**Technical:**
SatNOGS (Satellite Networked Open Ground Station) is an open-source network of amateur
radio ground stations providing RF observations of satellites:
- Telemetry data from active satellite transmissions
- Signal waterfall (frequency vs time) plots
- Doppler curve measurements
- Observation scheduling and results

- **Authentication:** None (CC-BY-SA license)
- **Database record:** `data_sources` table id=2, source_name='SATNOGS'
- **Use in project:** RF observations for multi-phenomenology (MX) sensor mode

**Plain English:**
SatNOGS is a worldwide network of amateur radio enthusiasts who volunteer their antennas
to listen to satellites. When a satellite passes over a ground station, the station
automatically records the radio signals. This gives us RF observations -- a completely
different type of data from what telescopes or radar provide.

## 6.9 ILRS (International Laser Ranging Service)

**Technical:**
ILRS provides satellite laser ranging (SLR) measurements with millimeter-level accuracy.
A ground station fires a short laser pulse at a satellite equipped with retroreflectors,
measures the round-trip time, and computes range with ~1-10mm precision.

- **Authentication:** None (public domain)
- **Database record:** `data_sources` table id=5, source_name='ILRS'
- **Database table:** `validation_measurements` with fields:
  - `range_m` (DECIMAL 15,6) - millimeter precision range
  - `station_code` - ILRS station identifier (e.g., YARL, GRZL)
  - `normal_point_rms_m` - measurement quality metric
  - `num_returns` - number of photon returns
- **Use in project:** Ground truth validation for T1H (highest-confidence) tier datasets

**Plain English:**
ILRS shoots laser beams at special satellites that have mirrors on them. By timing how long
the laser takes to bounce back, they know exactly how far away the satellite is -- down to
millimeters. This is by far the most accurate way to measure a satellite's position, so we
use it as the "gold standard" to verify our other measurements. When a dataset is validated
against ILRS data, it gets the T1H (Tier 1 High-confidence) label.

## 6.10 Data Source Comparison Table

| Source | Auth | Type | Data Provided | Update Freq | License | DB ID |
|--------|------|------|---------------|-------------|---------|-------|
| **UDL** | Bearer token | Observations | RA/Dec, Range/RR, State Vectors, TLEs | Real-time | RESTRICTED | 1 |
| **Space-Track** | User/Pass | Catalog | TLEs, Historical elements, CDMs | Multiple/day | RESTRICTED | 6 |
| **CelesTrak** | None | Catalog | Current TLEs by category | Multiple/day | OPEN | - |
| **UCS** | None | Metadata | Purpose, operator, mass, power | ~Quarterly | OPEN | 4 |
| **GCAT** | None | Catalog | Object type, COSPAR ID, mass, launch info | Weekly | CC-BY | 3 |
| **ESA DiscoWeb** | Bearer token | Physical | Mass, area, drag/SRP coefficients | Periodic | RESTRICTED | - |
| **SatNOGS** | None | Observations | RF observations, telemetry | Real-time | CC-BY-SA | 2 |
| **ILRS** | None | Validation | Laser range (mm accuracy) | Daily | PUBLIC_DOMAIN | 5 |

---

# 7. What is UCTP?

## 7.1 The Core Problem: Uncorrelated Tracks

**Technical:**
An Uncorrelated Track (UCT) is a set of observations that cannot be associated with any
cataloged space object. Uncorrelated Track Processing (UCTP) is the discipline of
analyzing UCTs to:
1. Cluster related observations together
2. Determine orbits from those clusters
3. Identify what the objects are

In the benchmarking context, observations are deliberately **decorrelated** -- satellite IDs
are stripped from real observation data, the observations are shuffled, and only track
groupings (observations from the same sensor pass) are preserved. The UCTP must reconstruct
which observations go together and determine the orbits.

**Plain English:**
Imagine someone takes a finished jigsaw puzzle, removes all the pieces, throws them in a
pile with pieces from 39 other puzzles, and peels off all the labels. Your job is to:
1. Sort out which pieces belong to which puzzle
2. Build each puzzle to see what picture it makes
3. Match each picture to a known photograph

That is exactly the UCTP problem. The "pieces" are observations, the "puzzles" are
satellites, and the "photographs" are known orbits in the catalog.

## 7.2 The UCTP Pipeline

The UCTP pipeline consists of four sequential stages, each independently configurable:

```
  UCTP PIPELINE
  =============

  INPUT: Decorrelated observations
  (satellite IDs removed, only track groupings preserved)
        |
        v
  +------------------+
  | 1. CLUSTERING    |  Group related observations
  | Angular DBSCAN   |  "Which obs belong together?"
  | Stone Soup MHT   |
  | Stone Soup GNN   |
  +--------+---------+
           |
           v
  +------------------+
  | 2. INITIAL ORBIT |  First orbit estimate
  | DETERMINATION    |  "What orbit fits these obs?"
  | Gauss Method     |
  | Laplace Method   |
  | Gooding Method   |
  +--------+---------+
           |
           v
  +------------------+
  | 3. ORBIT         |  Improve the estimate
  | REFINEMENT       |  "How can we make it more accurate?"
  | Batch Least Sq.  |
  | Extended Kalman  |
  | Unscented Kalman |
  +--------+---------+
           |
           v
  +------------------+
  | 4. CATALOG       |  Match to known objects
  | CORRELATION      |  "Is this a known satellite?"
  +--------+---------+
           |
           v
  OUTPUT: Candidate orbits with sourced observation IDs
  (state vectors or TLEs + which obs were used)
```

### Stage 1: Clustering

**Technical:**
Clustering groups decorrelated observations into clusters believed to originate from the
same space object. Available methods:

| Method | Code Value | Description |
|--------|-----------|-------------|
| **Angular DBSCAN** | `angular_dbscan` | Density-Based Spatial Clustering of Applications with Noise, adapted for angular measurements. Groups observations that are close in RA/Dec space and time. |
| **Stone Soup MHT** | `stonesoup_mht` | Multi-Hypothesis Tracking from the Stone Soup framework. Maintains multiple hypotheses about observation-to-track assignments simultaneously. |
| **Stone Soup GNN** | `stonesoup_gnn` | Global Nearest Neighbor from Stone Soup. Assigns each observation to the nearest existing track using a global optimization. |

Configuration parameters (from `ClusteringConfig`):
- `eps_deg` - Maximum angular separation in degrees for DBSCAN neighborhood
- `min_samples` - Minimum observations to form a cluster
- `time_weight` - Weight given to temporal separation vs angular separation
- `max_time_gap_hours` - Maximum time gap within a cluster
- `use_angular_rate` - Whether to use apparent angular velocity in clustering
- `rate_weight` - Weight for angular rate component

**Plain English:**
Clustering is the sorting step. Given a pile of mixed-up observations, the algorithm tries
to figure out which ones came from the same satellite. It looks at how close observations
are on the sky and how close in time they occurred. Observations that are near each other
in both position and time probably came from the same object.

### Stage 2: Initial Orbit Determination (IOD)

**Technical:**
IOD computes a preliminary orbit from a minimum set of observations (typically 3 angular
observations for optical data). This is the most mathematically challenging step -- going
from angles-only measurements to a full 6D state vector.

| Method | Code Value | Description |
|--------|-----------|-------------|
| **Gauss** | `gauss` | Modified Gauss method (Vallado). Uses 3 angular observations to solve the 8th-degree polynomial for range. Tries all valid permutations of triplet observations. |
| **Laplace** | `orbdetpy_laplace` | Laplace's method via orbdetpy library. Alternative angles-only IOD approach. |
| **Gooding** | `orekit_gooding` | Gooding's method via Orekit. Range-angles method that handles more general observation geometries. |

Configuration parameters (from `IODConfig`):
- `min_observations` - Minimum observations needed (typically 3)
- `angular_separation_lower_deg` - Minimum angular separation between used observations
- `angular_separation_upper_deg` - Maximum angular separation between used observations
- `max_iterations` - Maximum iterations for convergence
- `convergence_tol` - Convergence tolerance
- `cull_states` - Whether to discard poor state estimates
- `cull_sigma` - Sigma threshold for state culling

**Plain English:**
IOD is like solving a geometry puzzle. Given three or more direction measurements from
known locations on the ground, figure out the 3D path of the object. It is mathematically
tricky because you only know directions (not distances), so there can be multiple solutions.
The algorithm tries many combinations of observations and keeps the ones that produce
sensible orbits.

### Stage 3: Orbit Refinement

**Technical:**
Orbit refinement improves the initial orbit estimate by incorporating all available
observations using statistical estimation techniques.

| Method | Code Value | Description |
|--------|-----------|-------------|
| **None** | `none` | Skip refinement; use IOD result directly |
| **Batch Least Squares** | `batch_least_squares` | Process all observations simultaneously to find the state that minimizes the sum of squared residuals. Uses Orekit's BatchLSEstimator. |
| **Extended Kalman Filter (EKF)** | `ekf` | Sequential filter that processes observations one at a time, linearizing the dynamics at each step. Better for real-time processing. |
| **Unscented Kalman Filter (UKF)** | `ukf` | Sequential filter that uses sigma points to capture nonlinear dynamics without linearization. More accurate than EKF for highly nonlinear systems. |

Configuration parameters (from `RefinementConfig`):
- `max_iterations` - Maximum iterations for convergence
- `convergence_tol` - Convergence tolerance
- `process_noise_pos_km` - Position process noise (km)
- `process_noise_vel_km_s` - Velocity process noise (km/s)

**Plain English:**
Refinement takes the rough orbit from IOD and polishes it using all available observations.
Batch Least Squares looks at all observations at once and finds the best orbit that fits
them all. Kalman Filters process observations one at a time, updating the orbit estimate
each time. It is like: IOD gives you a rough sketch, and refinement turns it into a
detailed drawing.

### Stage 4: Catalog Correlation

**Technical:**
Catalog correlation matches the refined candidate orbits against the known space object
catalog to determine if the UCT corresponds to a known object. This step uses the same
orbit association algorithm described in Section 9 (Hungarian algorithm / linear sum
assignment).

**Plain English:**
The final step checks: "Is this orbit we figured out actually a known satellite?" It
compares the candidate orbit against every known object in the catalog and finds the best
match. If the match is close enough, the UCT is "correlated" (identified).

## 7.3 Configuration Options

Each pipeline stage is independently configurable through the `UCTPRunCreate` interface:

```typescript
interface UCTPRunCreate {
  dataset_id: number;
  algorithm_name: string;
  clustering: Partial<ClusteringConfig>;
  iod: Partial<IODConfig>;
  refinement: Partial<RefinementConfig>;
}
```

This allows researchers to test different combinations -- for example, Angular DBSCAN
clustering + Gauss IOD + Batch Least Squares refinement, or Stone Soup GNN clustering +
Gooding IOD + UKF refinement.

---

# 8. The Benchmark System

## 8.1 Common Task Framework (CTF)

**Technical:**
The Common Task Framework is a standardized methodology for evaluating competing algorithms:
1. **Shared training/test data** - All participants receive the same benchmark dataset
2. **Defined prediction task** - Produce candidate orbits from decorrelated observations
3. **Standardized metrics** - All submissions evaluated identically
4. **Fair comparison** - Results are directly comparable via the leaderboard

This is the same approach used in machine learning competitions (e.g., ImageNet, COCO) but
applied to astrodynamics.

**Plain English:**
A Common Task Framework is like a standardized test. Everyone takes the same test (same
dataset), answers the same type of questions (produce orbit estimates), and gets graded
the same way (same metrics). This makes it fair to compare results -- unlike having
different teams test on different data, which is comparing apples to oranges.

## 8.2 Dataset Code System

**Technical:**
Each dataset is identified by a 16-character code encoding its characteristics:

```
  Position:  1-2   3-4   5-6   7-8    9-10   11-12  13-14  15-16
  Field:     Type  Pct   Regime Event  Sensor Cvg    Gap    Obs#   Count Fitspan
  Example:   U     UN    LEO    NE     OP     S      A      S      H     07

  U_UN_LEO_NE_OP_S_A_S_H_07

  Decoded: Unspecified object types, unspecified percentage,
           LEO regime, no events, optical sensor, standard coverage,
           all long track gaps, standard obs count, high object count,
           7-day fitspan
```

**Dataset Code Fields:**

| Position | Field | Options |
|----------|-------|---------|
| 1 | Target Object Type | H=HAMR, C=Close, A=Close Apparent, U=Unspecified, N=Calibration |
| 2-3 | Target Percentage | 50, 10, 01, UN=Unspecified |
| 4-6 | Orbital Regime | LEO, MEO, GEO, HEO, ALL, LMO, LMG, etc. |
| 7-8 | Event | MB=Maneuver, BU=Breakup, LL=Long/Low Thrust, NE=No Events |
| 9-10 | Sensor Type | OP=Optical, RA=Radar, RF=RF, FU=Fusion, OR, RO, RR |
| 11 | Orbit Coverage | A=>90% low, S=40-60% low, N=<10% low |
| 12 | Track Gap | A=>90% long, S=40-60% long, N=<10% long |
| 13 | Observation Count | A=>90% low, S=40-60% low, N=<10% low |
| 14 | Object Count | H=80+-2, S=40+-2, L=10+-2 |
| 15-16 | Fitspan | 01-14 (days) |

**Plain English:**
The dataset code is like an order form. It describes exactly what kind of test data you
want: what type of satellites, what orbit, what sensors, how much data, how hard to make
it. Every possible combination has a unique code, so everyone knows exactly what dataset
they are working with.

## 8.3 Dataset Generation Pipeline

```
  DATASET GENERATION PIPELINE
  ============================

  Step 1: CONFIGURE
  User selects: regime, tier, sensors, coverage, object count, fitspan
        |
        v
  Step 2: DATA PULL from UDL
  Query observations in 10-minute chunks within selected time range
        |
        v
  Step 3: WINDOW SELECTION
  Score candidate time windows for quality
  Identify T1/T2/T3/T4/T5 tier
        |
        v
  Step 4: QUALITY SCORING (basicScoring function)
  For each satellite in window:
    - Compute orbital coverage (convex hull method)
    - Count observations
    - Measure track gaps
    - Determine orbital elements
        |
        v
  Step 5: TIER-BASED PROCESSING
    T1: Data meets all criteria -> use as-is
    T1H: T1 + ILRS validation -> highest confidence
    T2: Needs downsampling -> apply 3-stage pipeline
    T3: Needs simulation -> generate synthetic observations
    T4: Needs synthetic objects -> simulate new reference objects
    T5: Criteria cannot be met -> reject window
        |
        v
  Step 6: REFERENCE TRUTH COLLECTION
  Collect state vectors, TLEs, and covariance for reference objects
  Generate TrackTLEs from observation passes
        |
        v
  Step 7: DECORRELATION
  Strip satellite IDs from observations
  Dissociate observations from reference orbits
  Preserve only track groupings (same-pass observations)
  Create answer key (withheld from user)
        |
        v
  Step 8: TRUE NEGATIVES
  Add decoy observations (2 obs per non-dataset satellite)
  Cannot be used for IOD -> tests false positive detection
        |
        v
  Step 9: EXPORT
  Save as decorrelated JSON + answer key
  Record in datasets table with generation_params
```

**Plain English:**
Building a benchmark dataset is like creating a test with an answer key:
1. Decide what kind of test to make (easy LEO? hard GEO with sparse data?)
2. Pull real satellite observations from the database
3. Find a time window where the data quality matches what we want
4. Check the data quality for each satellite
5. If needed, either thin out data (downsampling) or fill gaps (simulation)
6. Collect the "answers" (the true orbits of each satellite)
7. Erase all the satellite names from the observations (decorrelate)
8. Throw in some trick questions (fake observations that don't belong to anything)
9. Package it up and save it

## 8.4 Data Tiers

**Technical:**

| Tier | Name | Description | Downsampling | Simulation | Quality |
|------|------|-------------|-------------|------------|---------|
| **T1** | Pristine Real | All criteria met naturally; no manipulation needed | No | No | Highest (natural) |
| **T1H** | ILRS-Validated | T1 data validated against ILRS laser ranging measurements | No | No | Highest (verified) |
| **T2** | Downsampled | Real data downsampled to target characteristics | Yes | No | High |
| **T3** | Gap-Filled | Real data + simulated observations to fill gaps | Maybe | Yes | Medium |
| **T4** | Synthetic Objects | Entirely new reference objects simulated | Maybe | Yes | Lower |
| **T5** | Unusable | Selected criteria cannot be met for any window | N/A | N/A | Rejected |

**Plain English:**
Tiers are like data quality grades:
- **T1** (A+): Perfect natural data, no manipulation needed
- **T1H** (A+ verified): Same as T1 but independently verified by laser measurements
- **T2** (A): Real data, but we deliberately thinned it out to make it harder
- **T3** (B): Mostly real data, but we filled some gaps with simulated measurements
- **T4** (C): Contains some completely made-up satellites
- **T5** (F): Could not be generated at all; the requirements are impossible

## 8.5 Downsampling (T2 Processing)

**Technical:**
Downsampling is a 3-stage sequential pipeline applied when natural data exceeds desired
quality levels. The stages are applied in order, and objects with simulated data or <= 2
observations are excluded.

**Stage 1: Coverage Reduction**
- Select satellites with lowest coverage above threshold first
- Remove observations that would reduce coverage the most
- Strategy: remove observations with closest temporal neighbors first (within 0.1 period)
- If insufficient, drop the temporal proximity constraint and recompute

**Stage 2: Gap Introduction**
- Select satellites with highest gap (below target) first
- Use a sliding window to find the temporal window of target size with fewest observations
- Remove all observations within that window

**Stage 3: Observation Limiting**
- Select satellites with lowest obs count (above threshold) first
- Bin observations into 10 temporal quantile groups
- Remove equal numbers randomly from each bin (preserving temporal distribution)

**Plain English:**
Downsampling is like an editor cutting a movie to make it harder to follow:
1. First, they cut scenes to reduce how much of the story arc you see (coverage reduction)
2. Then, they insert long gaps of blackscreen (gap introduction)
3. Finally, they remove random frames to reduce total footage (observation limiting)

Each step preserves the temporal distribution of what remains, so it still looks like
realistic data -- just sparser.

## 8.6 Observation Simulation (T3 Processing)

**Technical:**
When real data is insufficient, synthetic observations are generated:

1. Select a common observatory from the real data's sensor distribution
2. Generate a list of needed observation epochs (to achieve target coverage/gap)
3. Propagate the reference orbit to each epoch using Orekit
4. Add uncorrelated Gaussian noise to position components
   (default: `config.positionNoise` meters)
5. Convert position to RA/Dec measurements
6. Add uncorrelated Gaussian noise to RA and Dec
   (default: `config.angularNoise` = 1/3600 degrees = 1 arcsecond)
7. Convert RA/Dec to azimuth/elevation using the observatory location
8. Mark as `dataMode: "SIMULATED"` in the observation metadata

Available sensor models for simulation:
- `GEODSS` - Ground-based EO deep space
- `SBSS` - Space-based surveillance
- `Commercial_EO` - Commercial telescopes

Configuration (from `SimulationOptions`):
- `fillGaps` - Fill temporal gaps with synthetic obs
- `sensorModel` - Which sensor noise model to use
- `applyNoise` - Whether to add measurement noise
- `maxSyntheticRatio` - Maximum fraction of synthetic observations (0.0-0.9)

**Plain English:**
When there is not enough real data, the system generates fake observations that look
realistic. It predicts where the satellite would have been, adds some measurement noise
(because real sensors are not perfect), and creates a synthetic observation record. These
fake observations are clearly labeled as simulated, so everyone knows which data is real
and which is made up.

---

# 9. Evaluation Metrics

## 9.1 Overview

**Technical:**
Algorithm performance is evaluated across three complementary metric categories:
1. **Binary Metrics** - Did you correctly identify which observations belong together?
2. **State Metrics** - How accurate are your orbit estimates compared to truth?
3. **Residual Metrics** - How well do observations fit the estimated orbit?

Each category answers a different question about algorithm performance. A good algorithm
should score well on all three.

**Plain English:**
Think of grading an exam with three sections:
1. **Binary**: Did you sort the puzzle pieces correctly? (right pieces in right groups)
2. **State**: Does your assembled picture match the answer key? (orbit accuracy)
3. **Residual**: When you overlay your picture on the pieces, do they fit? (consistency)

## 9.2 Orbit Association (Pre-Evaluation Step)

**Technical:**
Before computing metrics, each candidate orbit must be matched to a reference orbit. This
is solved as an optimal assignment problem using the modified Jonker-Volgenant algorithm
(scipy.optimize.linear_sum_assignment).

**Cost Matrix Construction:**
1. For every reference/candidate pair, propagate the reference orbit to the candidate's
   epoch using Orekit
2. If TLEs, convert both to 6D state vectors
3. Compute the 6D vector difference between propagated reference and candidate
4. The L2 norm of the difference is the assignment cost

**Assignment Rules:**
- Equal candidates and references: 1:1 optimal matching
- More references than candidates: 1:1 matching; unmatched references become
  "Non-associated References" (FN candidates for binary metrics)
- More candidates than references: 1:1 matching; unmatched candidates become
  "Non-associated Candidates" (FP candidates for binary metrics)

**Plain English:**
Before grading, we need to figure out which student answer matches which question. The
algorithm finds the best possible pairing that minimizes total error. If a student
produced an orbit and the closest real orbit is 50 km away, the "cost" is 50. The system
finds the pairing where the total cost across all orbits is minimized.

## 9.3 Binary Classification Metrics

**Technical:**
Binary metrics classify each observation in the dataset as correctly or incorrectly handled:

| Classification | Definition |
|----------------|-----------|
| **True Positive (TP)** | Observation belongs to both the candidate orbit AND the reference orbit it was associated with |
| **True Negative (TN)** | Observation does not belong to any candidate orbit or reference orbit (true decoy correctly ignored) |
| **False Positive (FP)** | Observation belongs to a candidate orbit but NOT the associated reference orbit (wrong association) |
| **False Negative (FN)** | Observation does NOT belong to any candidate orbit but DOES belong to a reference orbit (missed observation) |

**Derived Metrics:**

| Metric | Formula | What It Measures |
|--------|---------|------------------|
| **Accuracy** | (TP + TN) / (TP + FP + TN + FN) | Overall correctness |
| **Precision** (PPV) | TP / (TP + FP) | Of what you claimed, how much was right |
| **Recall** (Sensitivity) | TP / (TP + FN) | Of what existed, how much did you find |
| **F1 Score** | 2*TP / (2*TP + FN + FP) | Harmonic mean of precision and recall |
| **Balanced Accuracy** | (1/2)[TP/(TP+FN) + TN/(TN+FP)] | Accuracy adjusted for class imbalance |
| **Cohen's Kappa** | (accuracy - expected) / (1 - expected) | Agreement beyond chance |
| **Matthews Corr. Coeff** | (TP*TN - FP*FN) / sqrt[(TP+FP)(TP+FN)(TN+FP)(TN+FN)] | Correlation between predicted and actual |
| **Specificity** | TN / (TN + FP) | Of decoys, how many were correctly ignored |

**Implementation:** Uses scikit-learn's `accuracy_score`, `f1_score`, `cohen_kappa_score`,
`matthews_corrcoef`, `balanced_accuracy_score`, and `recall_score` functions.

**Plain English:**
Binary metrics ask: "Did you sort the observations correctly?"
- **Precision**: Of all the observations you assigned to satellites, what percent were
  correct? (High precision = few wrong assignments)
- **Recall**: Of all the observations that actually belong to satellites, what percent did
  you find? (High recall = few missed observations)
- **F1 Score**: A single number combining precision and recall. 1.0 is perfect; 0.0 is
  terrible. This is the primary ranking metric on the leaderboard.

### Worked Example

```
  Suppose a dataset has 100 observations:
  - 80 real observations belonging to 10 satellites (8 per satellite)
  - 20 true negative (decoy) observations

  The UCTP outputs 9 candidate orbits, claiming:
  - 72 observations correctly assigned to 9 satellites (TP = 72)
  - 3 observations incorrectly assigned to wrong satellites (FP = 3)
  - 8 observations missed entirely (FN = 8)
  - 17 decoys correctly ignored (TN = 17)

  Precision = 72 / (72 + 3) = 0.960
  Recall    = 72 / (72 + 8) = 0.900
  F1 Score  = 2 * 72 / (2*72 + 8 + 3) = 144 / 155 = 0.929
  Accuracy  = (72 + 17) / (72 + 3 + 17 + 8) = 89 / 100 = 0.890
```

## 9.4 State Metrics

**Technical:**
State metrics measure the accuracy of orbit estimation by comparing candidate orbits to
propagated reference orbits at the candidate epoch.

### For State Vector Output:

| Metric | Formula | Unit | Description |
|--------|---------|------|-------------|
| **Position Error Norm** | \|\|pos_cand - pos_ref\|\|_2 | km | Euclidean distance between positions |
| **Velocity Error Norm** | \|\|vel_cand - vel_ref\|\|_2 | km/s | Euclidean difference in velocities |
| **Total Error Norm** | \|\|state_cand - state_ref\|\|_2 | mixed | 6D state difference norm |
| **Position Bias** | (cand - ref) / N per axis | km | Systematic position error per axis |
| **Velocity Bias** | (cand - ref) / N per axis | km/s | Systematic velocity error per axis |
| **Mahalanobis Distance** | d = (x_c - x_r)^T * C^-1 * (x_c - x_r) | dimensionless | Error weighted by combined covariance (C = C_ref + C_cand) |
| **MD P-Score** | 1 - chi2.cdf(MD, df=6) | 0.0-1.0 | Probability that reference and candidate are the same orbit (1.0 = full confidence) |
| **NEES** | (x_c - x_r)^T * C_cand^-1 * (x_c - x_r) | dimensionless | Normalized Estimation Error Squared (uses candidate covariance only) |
| **NEES P-Score** | 1 - chi2.cdf(NEES, df=6) | 0.0-1.0 | < 0.5 = overconfident processor; > 0.5 = underconfident |

### For TLE Output:
Only Position Error Norm, Velocity Error Norm, and Total Error Norm are computed (TLEs
lack covariance, so Mahalanobis Distance and NEES cannot be calculated).

**Database storage:**
```sql
position_rms_km DECIMAL(12,6)
velocity_rms_km_s DECIMAL(12,9)
mahalanobis_distance DECIMAL(12,6)
```

**Plain English:**
State metrics ask: "How close is your orbit estimate to reality?"
- **Position Error**: How many kilometers off is the predicted position? A perfect algorithm
  gets 0 km error. A typical good result might be < 1 km for LEO.
- **Velocity Error**: How wrong is the predicted velocity? Even small velocity errors
  compound rapidly.
- **Mahalanobis Distance**: Error weighted by uncertainty. Getting 10 km off when your
  uncertainty is 100 km is okay. Getting 10 km off when your uncertainty is 1 km is bad.
- **NEES**: Tests whether the algorithm's claimed uncertainty is honest. An overconfident
  algorithm claims small uncertainty but has large errors.

## 9.5 Residual Metrics

**Technical:**
Residual metrics measure how well observations fit the estimated orbit. The system computes
great-circle residuals on the unit sphere:

For each observation associated with a candidate orbit:
1. Propagate the candidate orbit to the observation epoch
2. Convert the propagated position to RA/Dec
3. Compute the great-circle angular distance between observed and propagated RA/Dec:
   ```
   residual = arccos(sin(dec_obs)*sin(dec_est) +
                     cos(dec_obs)*cos(dec_est)*cos(ra_obs - ra_est))
   ```
4. Compute RMS, mean, and standard deviation of residuals across all observations

**Two evaluation modes:**
1. **Reference residuals** (`flag=True`): Compare reference observations with the candidate
   orbit. Measures accuracy -- how well does the candidate orbit fit the truth data?
2. **Candidate residuals** (`flag=False`): Compare the candidate orbit's own sourced
   observations with the candidate orbit. Measures precision -- how self-consistent is the
   solution?

**For TLE residuals:** Instead of angular great-circle distances, residuals are computed
for each Keplerian element: semi-major axis (km), eccentricity, inclination (deg), RAAN
(deg), argument of perigee (deg), mean anomaly (deg).

**Database storage:**
```sql
ra_residual_rms_arcsec DECIMAL(12,6)
dec_residual_rms_arcsec DECIMAL(12,6)
```

**Plain English:**
Residual metrics ask: "When you look back at the observations, how well does your orbit
prediction match what was actually seen?"

Imagine you estimated the orbit, then asked "where would the satellite appear in the sky
at each observation time?" The difference between where you predicted and where it actually
appeared is the residual. Smaller residuals mean the orbit fits the data better.

Two types:
- **Reference residuals** = checking against the answer key (accuracy)
- **Candidate residuals** = checking against your own observations (self-consistency)

---

# 10. System Architecture

## 10.1 Full Stack Overview

**Technical:**
The SDA-TAP-SpOC UCT Benchmark is a full-stack web application:

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend** | React 18 + TypeScript + Vite + TailwindCSS | User interface for dataset management, submission, results, UCTP Lab |
| **State Management** | Zustand | Lightweight reactive state management |
| **Backend API** | FastAPI (Python) | REST API for all data operations |
| **Database** | DuckDB (embedded) / PostgreSQL (production) | Analytical data storage |
| **Auth** | Supabase JWT | Authentication and authorization |
| **Orbit Propagation** | Orekit (Java, via Python bridge) | Orbital mechanics computations |
| **ML Libraries** | Stone Soup, orbdetpy, scikit-learn | Tracking, IOD, evaluation |

**Plain English:**
The system has three main layers: a web interface that users interact with (built with
React), a server that processes requests (built with Python/FastAPI), and a database that
stores everything (DuckDB or PostgreSQL). The web interface talks to the server, which
talks to the database and to external data sources.

## 10.2 System Architecture Diagram

```
  +=================================================================+
  |                         FRONTEND                                 |
  |  React 18 + TypeScript + Vite + TailwindCSS + Zustand           |
  |                                                                  |
  |  Pages:                                                          |
  |  [Dashboard] [Datasets] [Submit] [Results] [Leaderboard]        |
  |  [UCTP Lab]  [Data Sources] [Settings]                          |
  +---------------------------------+--------------------------------+
                                    |
                              HTTPS/REST API
                              (JWT Auth Header)
                                    |
  +---------------------------------v--------------------------------+
  |                         BACKEND API                              |
  |  FastAPI (Python 3.11+)                                          |
  |                                                                  |
  |  Routers:                                                        |
  |  /api/auth/*       - Authentication (signup, login, logout)      |
  |  /api/datasets/*   - Dataset CRUD + generation                   |
  |  /api/submissions/*- Upload + manage submissions                 |
  |  /api/results/*    - View evaluation results                     |
  |  /api/leaderboard/*- Rankings + statistics                       |
  |  /api/jobs/*       - Background job tracking                     |
  |  /api/uctp/*       - UCTP Lab (runs, models, connectivity)      |
  |  /api/credentials/*- Encrypted credential management            |
  +-----------+-------------------+-------------------+--------------+
              |                   |                   |
     +--------v--------+  +------v------+   +--------v--------+
     |   DATABASE       |  | CORE LIBS   |   | EXTERNAL APIs    |
     |   DuckDB /       |  | Orekit      |   | UDL              |
     |   PostgreSQL     |  | Stone Soup  |   | Space-Track      |
     |                  |  | orbdetpy    |   | ESA DiscoWeb     |
     |   20 Tables      |  | scipy       |   | SatNOGS          |
     |   Schema v1.3.0  |  | scikit-learn|   | ILRS             |
     +------------------+  +-------------+   | CelesTrak        |
                                             | UCS/GCAT         |
                                             +------------------+
```

## 10.3 API Endpoints Summary

| Router | Method | Path | Purpose |
|--------|--------|------|---------|
| **Auth** | POST | /api/auth/signup | Create new user account |
| | POST | /api/auth/login | Authenticate with email + password |
| | POST | /api/auth/logout | Log out current session |
| | GET | /api/auth/me | Get current user profile |
| | PATCH | /api/auth/me | Update user profile |
| **Datasets** | GET | /api/datasets/ | List all datasets |
| | GET | /api/datasets/{id} | Get dataset details |
| | POST | /api/datasets/ | Create + generate new dataset |
| | DELETE | /api/datasets/{id} | Delete a dataset |
| | GET | /api/datasets/{id}/observations | Get dataset observations |
| | GET | /api/datasets/{id}/download | Download dataset as JSON |
| | POST | /api/datasets/{id}/link-observations | Link observations manually |
| | PATCH | /api/datasets/{id}/coverage | Update coverage value |
| **Submissions** | GET | /api/submissions/ | List submissions |
| | GET | /api/submissions/{id} | Get submission details |
| | POST | /api/submissions/ | Upload new submission |
| | POST | /api/submissions/{id}/results | Upload results file |
| **Results** | GET | /api/results/ | List all results |
| | GET | /api/results/{id} | Get complete results |
| | GET | /api/results/{id}/metrics | Detailed metrics breakdown |
| | GET | /api/results/{id}/visualization | Visualization data |
| | GET | /api/results/{id}/export | Export results |
| **Leaderboard** | GET | /api/leaderboard/ | Current leaderboard |
| | GET | /api/leaderboard/history | Historical rankings |
| | GET | /api/leaderboard/statistics | Aggregate statistics |
| **Jobs** | GET | /api/jobs/ | List background jobs |
| | GET | /api/jobs/{id} | Get job status |
| **UCTP Lab** | GET | /api/uctp/dashboard/stats | Dashboard overview |
| | GET | /api/uctp/runs/ | List pipeline runs |
| | POST | /api/uctp/runs/ | Start new pipeline run |
| | GET | /api/uctp/runs/{id} | Get run details |
| | DELETE | /api/uctp/runs/{id} | Delete a run |
| | GET | /api/uctp/runs/{id}/logs | Get run logs |
| | GET | /api/uctp/runs/compare/ | Compare multiple runs |
| | GET | /api/uctp/models/ | List ML models |
| | POST | /api/uctp/models/train | Train new model |
| | GET | /api/uctp/models/{id} | Get model details |
| | DELETE | /api/uctp/models/{id} | Delete model |
| | POST | /api/uctp/models/{id}/evaluate | Evaluate model on dataset |
| | GET | /api/uctp/connectivity/ | API connection statuses |
| | POST | /api/uctp/connectivity/test | Test specific connection |
| | POST | /api/uctp/connectivity/test-all | Test all connections |
| | GET | /api/uctp/algorithms/ | Available algorithm options |
| **Credentials** | GET | /api/credentials/ | List credential services |
| | GET | /api/credentials/{service} | Get credential metadata |
| | PUT | /api/credentials/{service} | Store encrypted credentials |
| | DELETE | /api/credentials/{service} | Clear credentials |
| | POST | /api/credentials/{service}/test | Test connectivity |
| | POST | /api/credentials/generate-key | Generate encryption key |

## 10.4 Database Schema Overview

**Technical:**
The database uses 20 tables organized into functional groups. Schema version 1.3.0 supports
both DuckDB (embedded, for development) and PostgreSQL (production).

```
  DATABASE SCHEMA (Entity Relationships)
  =======================================

  data_sources (6 seeded)
       |
       |  source_id
       v
  satellites --------+--------+--------+--------+
   (sat_no PK)       |        |        |        |
       |              |        |        |        |
       |  sat_no      |        |        |        |
       v              v        v        v        v
  observations   state_vectors  element_sets  validation_measurements
   (id PK)        (id PK)       (id PK)       (id PK, ILRS data)
       |                |             |
       |                |             |
       v                v             v
  dataset_observations  dataset_references
   (dataset_id, obs_id)  (dataset_id, sat_no, sv_id, elset_id)
       |                      |
       +----------+-----------+
                  |
                  v
             datasets -----------> submissions --------> submission_results
              (id PK)              (id PK)               (id PK)
                  |
                  v
              jobs (background processing)

  UCTP Lab:
  uctp_runs (pipeline executions)
  uctp_models (trained ML models)
  uctp_api_connections (service health)

  System:
  credentials (encrypted credential storage)
  event_types + events + event_observations (future: event labelling)
  _schema_metadata (version tracking)
```

**Key Tables:**

| Table | Records | Purpose |
|-------|---------|---------|
| `satellites` | Per-object | Satellite catalog with enriched metadata |
| `observations` | Per-measurement | Individual sensor measurements |
| `state_vectors` | Per-epoch | 6D state + covariance at specific times |
| `element_sets` | Per-epoch | TLEs with parsed orbital elements |
| `datasets` | Per-dataset | Generated benchmark datasets |
| `dataset_observations` | Junction | Maps observations to datasets (decorrelated) |
| `dataset_references` | Junction | Maps reference orbits to datasets |
| `submissions` | Per-upload | Algorithm submission tracking |
| `submission_results` | Per-evaluation | Computed metrics for submissions |
| `jobs` | Per-task | Background job status tracking |
| `validation_measurements` | Per-ILRS-obs | Laser ranging ground truth |
| `uctp_runs` | Per-run | UCTP pipeline execution results |
| `uctp_models` | Per-model | Trained ML model metadata |
| `credentials` | Per-service | Encrypted API credentials |
| `data_sources` | Per-source | Data provenance tracking |

---

# 11. Satellite Properties & Classification

## 11.1 Object Types

**Technical:**
Space objects are classified into three primary categories in the `satellites` table
(`object_type` column):

| Type | Description | Typical Count | Tracking Priority |
|------|-------------|---------------|-------------------|
| **PAYLOAD** | Active or inactive satellites | ~7,000 active | Highest |
| **ROCKET BODY** | Spent upper stages from launches | ~2,000 | Medium |
| **DEBRIS** | Fragments from breakups, collisions, operations | ~25,000+ tracked | Varies |

**Plain English:**
Everything in orbit falls into three categories:
- **Payloads** - The actual satellites that do useful things (communications, GPS, imaging)
- **Rocket bodies** - The spent fuel tanks and engines left over from launches
- **Debris** - Broken pieces from explosions, collisions, or just stuff falling off

## 11.2 HAMR (High Area-to-Mass Ratio) Objects

**Technical:**
HAMR objects are space objects with a high ratio of cross-sectional area to mass. They are
significantly affected by solar radiation pressure (SRP), making their orbits harder to
predict. The system defines HAMR as AMR > 0.1 m^2/kg (note: the benchmarking documentation
uses > 1 m^2/kg for dataset target selection).

Calculation:
```
AMR = cross_section_m2 / mass_kg   (m^2/kg)
```

Stored in `amr_m2_kg DECIMAL(12,6)` in the `satellites` table.

**Plain English:**
HAMR objects are like space tumbleweeds -- they are big relative to their weight, so
sunlight pushes them around significantly. A crumpled piece of aluminum foil in orbit has
a high AMR: lots of surface area, very little mass. These objects are especially hard to
track because their orbits change unpredictably due to sunlight pressure.

## 11.3 Physical Properties

The `satellites` table stores physical properties primarily from ESA DiscoWeb:

| Property | Column | Unit | Default | Source |
|----------|--------|------|---------|--------|
| Mass | `mass_kg` | kg | - | ESA DiscoWeb |
| Cross-Section | `cross_section_m2` | m^2 | - | ESA DiscoWeb |
| Drag Coefficient | `drag_coeff` | dimensionless | 2.5 | ESA / default |
| SRP Coefficient | `srp_coeff` | dimensionless | 1.5 | ESA / default |
| Area-to-Mass Ratio | `amr_m2_kg` | m^2/kg | calculated | Derived |
| Power | `power_watts` | W | - | UCS Database |

These properties feed directly into the force model for orbit propagation:
- Mass + area + drag coefficient -> atmospheric drag force
- Mass + area + SRP coefficient -> solar radiation pressure force

## 11.4 Satellite Identification

| Identifier | Format | Example | Source |
|------------|--------|---------|--------|
| **NORAD Catalog Number** | 5-digit integer | 25544 | Space-Track / UDL |
| **COSPAR Designation** | YYYY-NNNXX | 1998-067A | International standard |
| **Sensor-assigned ID** | Varies | "EXO7151" | Observation source |

- `sat_no` (INTEGER) is the primary key in the `satellites` table
- `cospar_id` (VARCHAR 20) provides the international designation
- During decorrelation, all IDs are stripped; observations get anonymous `assigned_track_id`
  and `assigned_object_id` integers

---

# 12. Orbit Propagation

## 12.1 What is Propagation?

**Technical:**
Orbit propagation is the process of computing the future (or past) state of a space object
given its current state and a model of the forces acting on it. It solves the equation of
motion:

```
d^2r/dt^2 = -mu*r/|r|^3 + perturbations(drag, SRP, 3rd body, harmonics, ...)
```

**Plain English:**
Propagation is predicting the future. Given where a satellite is right now and how fast it
is moving, where will it be in an hour? A day? A week? It is like weather forecasting for
satellite positions -- the further into the future you predict, the less accurate it gets.

## 12.2 Orekit

**Technical:**
Orekit (ORbit Extrapolation KIT) is the primary orbit propagation library used in the
system. It is an open-source Java library accessed via Python through the Orekit Python
wrapper.

Key Orekit components used:
- **DormandPrince853 Integrator** - Numerical integration with adaptive step size
  (min step: 0.0001s, max step: 1000s, relative tol: 1e-14, absolute tol: 1e-12)
- **HolmesFeatherstoneAttractionModel** - Earth gravity with spherical harmonics to
  degree and order 120
- **ThirdBodyAttraction** - Sun and Moon gravitational perturbations (point mass)
- **NRLMSISE-00** - Atmospheric density model with CSSI Space Weather data
- **IsotropicDrag** - Atmospheric drag using cross-sectional area and drag coefficient
- **SolarRadiationPressure** - SRP with umbra/penumbra shadow model
- **TLEPropagator** - SGP4/SDP4 propagation for TLEs
- **BatchLSEstimator** - Batch Least Squares orbit determination

Orekit data (Earth orientation parameters, space weather, etc.) must be configured locally.
The credential service `orekit` (type `path`) stores the path to the Orekit data directory.

**Plain English:**
Orekit is the math engine that predicts satellite positions. It is like a very sophisticated
physics simulator that accounts for:
- Earth's gravity (including the fact that Earth is not a perfect sphere)
- The pull from the Sun and Moon
- Atmospheric drag (thin air that slows satellites down)
- Sunlight pressure (photons physically pushing on satellites)

It is extremely accurate for short-term predictions but, like weather forecasting,
accuracy degrades over time.

## 12.3 SGP4/SDP4

**Technical:**
SGP4 (Simplified General Perturbations 4) and SDP4 (Simplified Deep-Space Perturbations 4)
are analytical propagation models specifically designed for TLEs. They are the ONLY valid
propagation models for TLE data -- using TLEs with other propagators produces incorrect
results because TLEs encode mean elements that are only meaningful within the SGP4/SDP4
theory.

Selection criteria (per NORAD):
- **SGP4**: Orbital period < 225 minutes ("near-Earth" objects)
- **SDP4**: Orbital period >= 225 minutes ("deep-space" objects)

In Orekit, `TLEPropagator` automatically selects SGP4 or SDP4 based on the TLE's mean
motion.

**Plain English:**
SGP4 and SDP4 are simplified prediction models created by the U.S. military specifically
for TLE data. They are fast but less accurate than Orekit's full physics model. The key
rule is: if your orbital data is in TLE format, you MUST use SGP4/SDP4. Using anything
else gives wrong answers because TLEs are specially encoded for these specific models.

## 12.4 Force Models

The system uses two tiers of force modeling:

### High-Fidelity (State Vector Propagation)

| Force | Model | Parameters | Source |
|-------|-------|-----------|--------|
| Earth Gravity | Holmes-Featherstone | Degree/Order 120 | Orekit built-in |
| Sun Gravity | Point Mass | - | Orekit CelestialBody |
| Moon Gravity | Point Mass | - | Orekit CelestialBody |
| Atmospheric Drag | NRLMSISE-00 + Isotropic | Cd, A, m | CSSI Weather + ESA |
| Solar Radiation Pressure | Isotropic + Shadow | Cr, A, m | ESA DiscoWeb |

### Simplified (TLE Propagation)

| Force | Model | Parameters |
|-------|-------|-----------|
| All perturbations | SGP4/SDP4 analytical | B* drag term only |

## 12.5 Monte Carlo Propagation

**Technical:**
For covariance propagation, the system uses Monte Carlo simulation:
1. Sample N points (default 100) from the multivariate normal distribution
   N(state_vector, covariance_matrix)
2. Propagate each sample point individually using the high-fidelity force model
3. Discard samples that propagate inside Earth's surface
4. Compute the sample covariance of the surviving propagated points

This approach handles nonlinear dynamics better than linearized covariance propagation
(e.g., state transition matrix methods) but is computationally expensive.

**Plain English:**
To predict how uncertainty grows over time, the system takes the satellite's position and
"fuzzes" it into 100 slightly different positions (within the uncertainty cloud). Then it
predicts where each of those 100 slightly different satellites would end up. The spread of
the 100 final positions tells us how uncertain we are about the future position. Any
predictions that end up inside the Earth are thrown away (satellites cannot be underground).

---

# 13. Coordinate Systems & Reference Frames

## 13.1 Why Multiple Frames Exist

**Technical:**
Different reference frames are optimized for different purposes. Inertial frames (fixed
relative to stars) are best for orbital mechanics. Earth-fixed frames (rotating with Earth)
are best for ground-based observations. TLE-specific frames exist for historical
compatibility. The evaluation framework converts all data to J2000/EME2000 for consistency.

**Plain English:**
There are many ways to set up a coordinate system. You can pin it to the stars (so the
stars never move, but the Earth spins underneath). Or you can pin it to the Earth (so the
ground stays still, but the stars rotate overhead). Each is useful for different things, so
the system has to handle conversions between them.

## 13.2 Reference Frames Used

### J2000 / EME2000 (Primary Evaluation Frame)

**Technical:**
The J2000 frame (EME2000 in Orekit) is an Earth-Centered Inertial (ECI) frame defined by:
- Origin: Earth's center of mass
- X-axis: Mean vernal equinox direction at J2000.0 epoch (January 1, 2000, 12:00 TT)
- Z-axis: Mean celestial pole at J2000.0
- Y-axis: Completes the right-handed system

This is the standard frame for orbital mechanics and the primary frame used for all
evaluation computations in the system. All state vectors are converted to J2000 before
metric computation.

**Plain English:**
J2000 is the "standard" coordinate system for space. It is pinned to the stars as they
were positioned on January 1, 2000. The Earth spins inside this frame. It is the
universal language for satellite positions -- everyone converts to J2000 so their numbers
are comparable.

### TEME (True Equator Mean Equinox)

**Technical:**
TEME is the native reference frame for TLEs and the SGP4/SDP4 propagation model. It
differs from J2000 by accounting for nutation (the "wobble" of Earth's axis) but using
mean equinox. TLE state vectors extracted via SGP4 are in TEME and must be converted to
J2000 for comparison with other data.

**Plain English:**
TEME is the coordinate system that TLEs are written in. It is close to J2000 but slightly
different because of how it handles Earth's wobble. When working with TLEs, you get TEME
coordinates, which must be converted to J2000 before comparing with other data.

### GCRF (Geocentric Celestial Reference Frame)

**Technical:**
GCRF is the most precise realization of an inertial reference frame, defined by distant
quasars. It is nearly identical to J2000/EME2000 (difference < 0.1 arcsecond) but is based
on modern VLBI observations rather than the historical FK5 star catalog.

**Plain English:**
GCRF is the most accurate "star-fixed" coordinate system. It is pinpointed using
ultra-distant galaxies that appear completely motionless. For practical purposes, it is
nearly identical to J2000.

### ITRF / ECEF (Earth-Fixed Frame)

**Technical:**
The International Terrestrial Reference Frame (ITRF), also known as Earth-Centered
Earth-Fixed (ECEF), rotates with the Earth:
- Origin: Earth's center of mass
- X-axis: Points to the prime meridian (0 longitude) at the equator
- Z-axis: Points to the geographic north pole
- Y-axis: Completes the right-handed system (points to 90E longitude)

Ground station positions are naturally expressed in ITRF. Sensor positions
(`senx/seny/senz` in observations) are in ECI but derived from ITRF positions.

**Plain English:**
ITRF is the coordinate system fixed to the Earth's surface. When you give latitude and
longitude, you are using an Earth-fixed frame. The ground does not move in this system,
but the stars rotate overhead. This is natural for describing where sensors are, because
sensors are bolted to the ground.

### EFG / TDR (Earth-Fixed Greenwich)

**Technical:**
An Earth-fixed frame referenced to the Greenwich meridian. Some UDL data uses this frame.
Converted to J2000 using Orekit's `getTransformTo` method.

### PQW (Perifocal Frame)

**Technical:**
An orbit-aligned frame where:
- P-axis: Points from Earth's center toward perigee
- Q-axis: In the orbital plane, 90 degrees ahead of P in the direction of motion
- W-axis: Normal to the orbital plane (along angular momentum vector)

Useful for orbit visualization but not used directly for data storage.

**Plain English:**
PQW is a coordinate system aligned with the orbit itself. The P direction points toward
the closest point of the orbit, and Q points in the direction of travel. It is like having
a coordinate system that "rides along" with the orbit.

## 13.3 Frame Conversions

```
  REFERENCE FRAME CONVERSIONS
  ============================

  All frames are converted to J2000/EME2000 for evaluation

  TEME -----> J2000    (TLE output, via Orekit Frame.getTransformTo)
  GCRF -----> J2000    (near-identity, < 0.1 arcsec difference)
  ITRF -----> J2000    (Earth rotation + polar motion + nutation)
  ECEF -----> J2000    (same as ITRF conversion)
  EFG  -----> J2000    (via Orekit)
  TDR  -----> J2000    (via Orekit)

  Covariance frame conversion uses Orekit StateCovariance.changeCovarianceFrame()
  TLEs do not require frame conversion (standardized in TEME)
```

The `unitConversion` function in the codebase handles converting reference orbit state
vectors and covariance matrices from UDL-provided frames (TEME, GCRF, ITRF, ECEF, TDR)
to J2000 for uniform evaluation.

---

# 14. Glossary

Complete A-Z glossary of technical terms used in the SDA-TAP-SpOC UCT Benchmark system.

| Term | Abbreviation | Technical Definition | Plain English |
|------|-------------|---------------------|---------------|
| **Accuracy** | - | (TP + TN) / (TP + FP + TN + FN); fraction of all classifications that are correct | Overall percentage of correct answers |
| **Apogee** | - | Point in an orbit farthest from Earth's center; altitude = a(1+e) - R_Earth | The highest point of an orbit |
| **Area-to-Mass Ratio** | AMR | Cross-sectional area divided by mass (m^2/kg); indicates susceptibility to SRP | How "sail-like" an object is; higher = more affected by sunlight |
| **Argument of Perigee** | omega | Angle from ascending node to perigee point, measured in the orbital plane (degrees) | Where in the orbit the closest point to Earth is |
| **Ascending Node** | - | Point where an orbit crosses the equatorial plane going from south to north | Where the orbit crosses the equator heading north |
| **Astrodynamics** | - | Study of the motion of rockets, missiles, and space vehicles including forces acting on them | The physics of things moving in space |
| **Atmospheric Drag** | - | Force opposing motion due to interaction with residual atmosphere; dominant perturbation in LEO | Air resistance in the very thin upper atmosphere |
| **B-Star** | B* | Modified ballistic coefficient in SGP4 model capturing atmospheric drag effects (1/Earth radii) | A single number summarizing how much atmosphere slows a satellite |
| **Balanced Accuracy** | - | (1/2)[TP/(TP+FN) + TN/(TN+FP)]; accuracy adjusted for class imbalance | Accuracy score that accounts for unequal group sizes |
| **Batch Least Squares** | BLS | Estimation method processing all observations simultaneously to minimize sum of squared residuals | Finding the best orbit by looking at all data points at once |
| **Benchmark Dataset** | - | Standardized dataset for evaluating and comparing different UCTP algorithms | A standardized test for satellite-tracking software |
| **Binary Metrics** | - | Classification metrics (TP, FP, TN, FN, F1, precision, recall) measuring observation sorting correctness | Scores for whether observations were sorted into correct groups |
| **Candidate Orbit** | - | Output from a UCTP: estimated state vector or TLE with associated observation IDs | The algorithm's answer: "I think these observations form this orbit" |
| **Catalog Correlation** | - | Matching estimated orbits against known objects in the space catalog | Checking if a detected object is already known |
| **CelesTrak** | - | Public service redistributing TLE data from Space-Track in accessible formats | Free website for downloading satellite orbit data |
| **Clustering** | - | Grouping decorrelated observations believed to originate from the same space object | Sorting mixed-up observations into groups by object |
| **Cohen's Kappa** | - | (accuracy - expected) / (1 - expected); measures agreement beyond chance | How much better than random guessing |
| **Common Epoch** | - | The epoch at which the candidate orbit state vector or TLE is valid | The timestamp the algorithm's answer is valid for |
| **Common Task Framework** | CTF | Standardized evaluation methodology: shared data + defined task + standard metrics | Everyone takes the same test with the same grading |
| **Conjunction** | - | A close approach between two space objects | Two objects in space getting dangerously close |
| **COSPAR Designation** | - | International identifier for space objects: YYYY-NNNXX (year-launch#-piece) | International naming system for space objects |
| **Covariance Matrix** | - | 6x6 symmetric matrix representing uncertainty in position and velocity estimates | A mathematical description of "how sure are we?" |
| **DBSCAN** | - | Density-Based Spatial Clustering of Applications with Noise; clustering algorithm used for observation grouping | An algorithm that groups nearby points together |
| **Declination** | Dec | Angular distance north/south of the celestial equator (degrees, -90 to +90) | How far above or below the celestial equator something appears |
| **Decorrelation** | - | Process of stripping satellite IDs from observations to create uncorrelated test data | Removing the answer labels to create a test |
| **Downsampling** | - | Strategic removal of observations to achieve desired data quality characteristics | Deliberately thinning data to make the test harder |
| **DuckDB** | - | Embedded analytical SQL database; used for development and lightweight deployments | A lightweight database that runs inside the application |
| **Earth-Centered Inertial** | ECI | Coordinate system with origin at Earth's center, axes fixed relative to stars | A grid for space that stays fixed while Earth rotates inside it |
| **Eccentricity** | e | Dimensionless measure of orbit shape: 0 = circle, approaching 1 = very elongated | How egg-shaped the orbit is |
| **Element Set** | elset | A set of orbital elements defining an orbit; see TLE | The numbers that describe an orbit's shape and orientation |
| **Ephemeris** | - | Time-ordered sequence of state vectors representing predicted trajectory | A table of predicted positions over time |
| **Epoch** | - | Reference timestamp at which orbital elements or state vectors are valid | The "as of" date for orbital data |
| **Extended Kalman Filter** | EKF | Sequential estimation filter that linearizes dynamics at each step | A method that updates orbit estimates one observation at a time |
| **F1 Score** | F1 | Harmonic mean of precision and recall: 2*TP/(2*TP+FN+FP); primary ranking metric | A single score combining "did you find everything?" and "was everything you found correct?" |
| **False Negative** | FN | Observation belonging to a reference orbit but not assigned to any candidate orbit | A real observation that the algorithm missed |
| **False Positive** | FP | Observation assigned to a candidate orbit but not belonging to its associated reference | An observation incorrectly assigned to the wrong satellite |
| **FastAPI** | - | Modern Python web framework for REST APIs; powers the backend | The technology running the server |
| **Fitspan** | - | Duration of time the dataset spans; configurable 1-14 days | How many days of data the test covers |
| **Gauss Method** | - | Angles-only IOD method using 3 observations; solves 8th-degree polynomial for range | Classic technique for figuring out an orbit from three telescope sightings |
| **GCAT** | - | General Catalog of Artificial Space Objects by J. McDowell; 57K+ objects | A comprehensive catalog of everything in orbit |
| **GEO** | - | Geostationary Earth Orbit; a >= 42,164 km; period ~24 hrs; appears stationary | Very high orbit where satellites hover over one spot |
| **GEODSS** | - | Ground-based Electro-Optical Deep Space Surveillance; military telescope network | Military telescopes for watching distant satellites |
| **Gooding Method** | - | Range-angles IOD method implemented in Orekit; handles diverse observation geometries | An IOD technique that works with a wider variety of observation setups |
| **HAMR** | - | High Area-to-Mass Ratio; objects with AMR > 0.1 m^2/kg significantly affected by SRP | Space objects that are big but lightweight, like space tumbleweeds |
| **HEO** | - | Highly Elliptical Orbit; eccentricity e >= 0.7 | Very egg-shaped orbit with huge altitude swings |
| **Hungarian Algorithm** | - | Optimization algorithm solving the assignment problem; used for orbit association | An algorithm that finds the best way to match candidate and reference orbits |
| **ILRS** | - | International Laser Ranging Service; provides mm-accuracy satellite range measurements | Network that measures satellite distance with lasers, incredibly precisely |
| **Inclination** | i | Angle between orbital plane and equatorial plane (degrees, 0-180) | How tilted the orbit is relative to the equator |
| **Initial Orbit Determination** | IOD | Computing a preliminary orbit from minimum observations (typically 3 angular measurements) | First rough estimate of an orbit from a few observations |
| **J2000** | EME2000 | Standard ECI reference frame defined at January 1, 2000, 12:00 TT | The standard coordinate system for space tracking |
| **Keplerian Elements** | - | Six parameters uniquely defining an orbit: a, e, i, RAAN, omega, M | The six numbers that completely describe an orbit |
| **Kessler Syndrome** | - | Cascading collision scenario where debris generates more debris | Chain reaction of space collisions making orbit unusable |
| **Laplace Method** | - | Alternative angles-only IOD method; implemented via orbdetpy library | Another technique for determining an orbit from telescope angles |
| **Leaderboard** | - | Ranked listing of algorithm submissions sorted by F1 score and other metrics | A scoreboard showing which algorithms perform best |
| **LEO** | - | Low Earth Orbit; a <= 8,378 km; altitude 200-2,000 km; period ~90-127 min | Close orbits where most satellites live |
| **Mahalanobis Distance** | MD | (x_c - x_r)^T * C^-1 * (x_c - x_r); error weighted by combined covariance | How far off the orbit estimate is, accounting for uncertainty |
| **Matthews Correlation Coefficient** | MCC | (TP*TN - FP*FN) / sqrt[(TP+FP)(TP+FN)(TN+FP)(TN+FN)]; balanced binary metric | Correlation between predicted and actual classifications |
| **Mean Anomaly** | M | Angle parameterizing position along orbit, increasing uniformly with time (degrees) | Where the satellite is in its orbit right now |
| **Mean Motion** | n | Number of orbits per day (rev/day) | How many laps per day |
| **MEO** | - | Medium Earth Orbit; 8,378 < a < 42,164 km; period ~2-24 hrs | Middle-height orbits where GPS satellites live |
| **Monte Carlo** | - | Statistical method using random sampling to estimate outcomes; used for covariance propagation | Predicting uncertainty by simulating many possible futures |
| **NEES** | - | Normalized Estimation Error Squared; measures covariance consistency | Tests if the algorithm's claimed uncertainty is honest |
| **NORAD Catalog Number** | - | Unique 5-digit identifier for each tracked space object | A satellite's ID number |
| **NRLMSISE-00** | - | Atmospheric density model used for drag computation | A model of how thick the atmosphere is at different altitudes |
| **Observation** | obs | Single measurement of a space object at a specific time; stored with unique ID and timestamp | One snapshot measurement of a satellite |
| **Orbit Association** | - | Matching candidate orbits to reference orbits via optimal assignment (Hungarian algorithm) | Pairing algorithm answers with correct answers |
| **Orbit Determination** | OD | Estimating an orbit from observations; encompasses IOD and refinement | Figuring out an orbit from measurements |
| **Orbital Coverage** | - | Fraction of orbit covered by observations; computed via convex hull projection method | How much of the satellite's path we actually observed |
| **Orbital Period** | T | Time for one complete orbit: T = 2*pi*sqrt(a^3/mu) | How long one lap around Earth takes |
| **Orbital Regime** | - | Classification of orbits by altitude/shape: LEO, MEO, GEO, HEO | Categories for different orbit types |
| **Orekit** | - | Open-source Java space dynamics library for orbit propagation and determination | The math engine for predicting satellite positions |
| **Perigee** | - | Point in an orbit closest to Earth's center; altitude = a(1-e) - R_Earth | The lowest point of an orbit |
| **Precision** | PPV | TP / (TP + FP); fraction of algorithm outputs that are correct | Of what you found, how much was right |
| **Propagation** | - | Computing future/past positions from current state and force model | Predicting where a satellite will be |
| **RAAN** | Omega | Right Ascension of the Ascending Node; angle from vernal equinox to ascending node (degrees) | Which direction the orbit's tilt faces |
| **React** | - | JavaScript UI library; powers the frontend with TypeScript and Vite build tool | The technology powering the web interface |
| **Recall** | Sensitivity | TP / (TP + FN); fraction of reference objects successfully identified | Of what existed, how much did you find |
| **Reference Frame** | - | Coordinate system defining the orientation and origin for position/velocity measurements | A grid system for measuring positions in space |
| **Reference Object** | - | Satellite with known NORAD ID, state vector, TLE, and observations in the dataset | A satellite we know everything about (the answer key) |
| **Reference Orbit** | - | State vector, TLE, observations, and trackTLEs associated with a reference object | The true orbit of a satellite in the answer key |
| **Residual** | - | Difference between observed and computed measurement (e.g., RA, Dec) | The leftover error between prediction and measurement |
| **Residual Metrics** | - | RMS, mean, std of angular residuals between observations and estimated orbit | Scores for how well the orbit fits the observation data |
| **Right Ascension** | RA | Eastward angle along celestial equator from vernal equinox (degrees, 0-360) | Longitude on the sky |
| **SatNOGS** | - | Satellite Networked Open Ground Station; amateur RF observation network | Network of volunteer radio listeners tracking satellites |
| **SBSS** | - | Space-Based Space Surveillance; satellite with optical sensor for observing space objects | A spy satellite that watches other satellites |
| **SDA** | - | Space Domain Awareness; comprehensive understanding of the space environment | Knowing what is happening in space |
| **Semi-Major Axis** | a | Half the longest diameter of orbital ellipse (km); determines energy and period | How big the orbit is |
| **SGP4/SDP4** | - | Simplified General/Deep-Space Perturbations models; required for TLE propagation | Simplified prediction models made for TLEs |
| **Simulation** | - | Generation of synthetic observations to fill data gaps; marked as "SIMULATED" | Making fake but realistic observation data |
| **Solar Radiation Pressure** | SRP | Force from photon momentum transfer; significant for HAMR objects | Sunlight physically pushing on satellites |
| **Space-Track** | - | Official US Space Force public satellite catalog website | Official government website for satellite orbit data |
| **Specificity** | - | TN / (TN + FP); fraction of decoys correctly ignored | Of the fake observations, how many were correctly rejected |
| **State Metrics** | - | Position/velocity error norms, Mahalanobis distance, NEES comparing estimated to true orbits | Scores for how accurate the orbit estimate is |
| **State Vector** | SV | Six numbers [x, y, z, vx, vy, vz] defining position and velocity at an epoch | Where something is and where it is going |
| **Stone Soup** | - | Open-source tracking framework providing MHT and GNN algorithms | A toolkit for multi-target tracking algorithms |
| **Supabase** | - | Open-source Firebase alternative providing JWT authentication | The authentication service |
| **TEME** | - | True Equator Mean Equinox; native reference frame for TLEs/SGP4 | The coordinate system TLEs are written in |
| **Tier** | T1-T5 | Data quality classification: T1=pristine, T2=downsampled, T3=simulated, T4=synthetic, T5=unusable | Quality grade for a dataset |
| **TLE** | - | Two-Line Element Set; standardized 2-line format encoding orbital elements for SGP4/SDP4 | A compact recipe describing a satellite's orbit |
| **Track** | - | Time-ordered series of observations from same sensor believed to be same object | A series of snapshots of the same object during one pass |
| **Track Gap** | - | Longest time between consecutive observations of an object, measured in orbital periods | The biggest hole in the observation timeline |
| **TrackTLE** | - | TLE generated from single observatory pass via Modified Gauss + Batch Least Squares | A rough orbit estimate from one telescope session |
| **True Negative** | TN | Observation not belonging to any candidate or reference orbit (decoy correctly ignored) | A fake observation correctly identified as fake |
| **True Positive** | TP | Observation correctly assigned to both candidate and associated reference orbit | A real observation correctly matched to its satellite |
| **UCT** | - | Uncorrelated Track; observations that cannot be associated with a known cataloged object | A mystery observation we cannot identify |
| **UCTP** | - | Uncorrelated Track Processing; the discipline of analyzing UCTs to determine orbits | The process of solving the mystery of unidentified observations |
| **UCS** | - | Union of Concerned Scientists; provides satellite metadata (purpose, operator, mass, power) | Database telling us what each satellite does and who owns it |
| **UDL** | - | Unified Data Library; primary US government space observation database | The main government database of satellite observations |
| **Unscented Kalman Filter** | UKF | Sequential estimator using sigma points; captures nonlinear dynamics without linearization | Advanced method for updating orbit estimates that handles complex physics better |
| **Vernal Equinox** | - | Direction from Earth to Sun at the March equinox; defines the X-axis of J2000 | A reference direction in space, based on where the Sun is in March |
| **Vite** | - | Fast build tool and dev server for the React frontend | The tool that builds the web interface |
| **Window Selection** | - | Process of finding optimal time windows meeting quality criteria for dataset generation | Finding the best time period in the data for creating a test |
| **Zustand** | - | Lightweight React state management library used in the frontend | A tool for managing data in the web interface |

---

# Appendix A: Dataset Code Quick Reference

```
  Position:  1    2-3   4-6    7-8    9-10   11   12   13   14   15-16
  Field:     Type Pct   Regime Event  Sensor Cvg  Gap  Obs  Cnt  Fitspan

  Target Types:    H=HAMR  C=Close  A=Close-Apparent  U=Unspecified  N=Calibration
  Percentages:     50  10  01  UN=Unspecified
  Regimes:         LEO  MEO  GEO  HEO  ALL  LMO  LMG  etc.
  Events:          MB=Maneuver  BU=Breakup  LL=Low-Thrust  NE=None
  Sensors:         OP=Optical  RA=Radar  RF  FU=Fusion  OR  RO  RR
  Coverage/Gap/Obs: A=>90% low/long  S=40-60%  N=<10%
  Object Count:    H=80  S=40  L=10  (all +/-2)
  Fitspan:         01-14 (days)
```

# Appendix B: Key File Locations

| Content Area | File Path |
|---|---|
| Database Schema | `UCT-Benchmark-DMR/combined/uct_benchmark/database/schema.py` |
| Frontend Types | `UCT-Benchmark-DMR/combined/frontend/src/types/index.ts` |
| UCTP Lab Types | `UCT-Benchmark-DMR/combined/frontend/src/types/uctp.ts` |
| Binary Metrics | `reference-code/master/uctbenchmark/src/libraries/binaryMetrics.py` |
| State Metrics | `reference-code/master/uctbenchmark/src/libraries/stateMetrics.py` |
| Residual Metrics | `reference-code/master/uctbenchmark/src/libraries/residualMetrics.py` |
| API Routers | `UCT-Benchmark-DMR/combined/backend_api/routers/*.py` |
| Benchmarking Docs | `provided-materials/Benchmarking Documentation.docx.md` |
| Glossary Source | `generated-docs/docs/reference/GLOSSARY.md` |

---

*This document was generated from the SDA-TAP-SpOC UCT Benchmark codebase (schema v1.3.0)
and the AFRL Scholars Benchmarking Documentation. For the most current information,
refer to the source code and API documentation.*
