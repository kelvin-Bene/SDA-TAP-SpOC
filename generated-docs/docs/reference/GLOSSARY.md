# Glossary

Definitions of terms used in the UCT Benchmark project and space domain awareness field.

---

## A

### Astrodynamics
The study of the motion of rockets, missiles, and space vehicles, including the forces that act upon them.

---

## B

### Benchmark Dataset
A standardized dataset used to evaluate and compare the performance of different algorithms.

---

## C

### CelesTrak
A website and service providing space object catalog data, TLEs, and other space surveillance information.

### Conjunction
A close approach between two space objects.

### Common Task Framework (CTF)
A methodology for evaluating algorithms where:
1. Training data is provided
2. A prediction task is defined
3. Benchmark metrics evaluate submissions

### Covariance Matrix
A 6x6 matrix representing the uncertainty in a satellite's state (position and velocity).

---

## D

### Declination (Dec)
Angular distance of a celestial object north or south of the celestial equator, measured in degrees.

### DuckDB
An analytical SQL database used for data storage in this project. Zero-configuration, embedded database optimized for OLAP workloads.

---

## E

### ECI (Earth-Centered Inertial)
A coordinate system with origin at Earth's center, with axes fixed relative to the stars.

### Element Set
See TLE.

### Epoch
A specific moment in time used as a reference for orbital elements or state vectors.

---

## F

### F1 Score
Harmonic mean of precision and recall: F1 = 2 * (P * R) / (P + R)

### False Negative (FN)
A reference object that was not successfully identified by the algorithm.

### False Positive (FP)
An algorithm output that does not correspond to a real object.

### FastAPI
A modern Python web framework used for building the UCT Benchmark backend REST API. Known for automatic OpenAPI documentation and type validation.

---

## G

### GEO (Geostationary Earth Orbit)
Circular orbit at ~35,786 km altitude with a 24-hour period, appearing stationary relative to Earth.

---

## H

### HAMR (High Area-to-Mass Ratio)
Space objects with high area relative to their mass, significantly affected by solar radiation pressure.

### HEO (Highly Elliptical Orbit)
Orbits with high eccentricity, providing extended coverage over specific regions.

### Hungarian Algorithm
An optimization algorithm used to solve the assignment problem for orbit association.

---

## I

### Initial Orbit Determination (IOD)
The process of computing a preliminary orbit from a small number of observations.

---

## J

### J2000
A standard inertial reference frame with origin at Earth's center and axes defined by the mean equator and equinox at January 1, 2000, 12:00 TT.

---

## K

### Keplerian Elements
Six orbital elements that uniquely define an orbit: semi-major axis, eccentricity, inclination, RAAN, argument of perigee, and mean anomaly.

---

## L

### LEO (Low Earth Orbit)
Orbits between 200-2,000 km altitude, with periods of approximately 90-120 minutes.

---

## M

### Mahalanobis Distance
A measure of distance between a point and a distribution, accounting for correlation. Used to assess covariance realism.

### MEO (Medium Earth Orbit)
Orbits between 2,000 km and geostationary altitude (~35,786 km).

---

## N

### NORAD Catalog Number
A unique 5-digit identifier assigned to each tracked space object by NORAD.

---

## O

### Observation
A measurement of a space object's position at a specific time, typically including right ascension and declination.

### Orbit Determination
The process of estimating the orbit of a space object from observations.

### Orekit
An open-source space dynamics library written in Java, used for orbit propagation.

---

## P

### Propagator
Software that predicts future or past satellite positions based on current state and force models.

### Precision
The fraction of algorithm outputs that are correct: TP / (TP + FP)

---

## R

### RAAN (Right Ascension of the Ascending Node)
The angle from the vernal equinox to the ascending node of an orbit, measured in the equatorial plane.

### React
A JavaScript library for building user interfaces. Used for the UCT Benchmark web frontend with Vite as the build tool.

### Recall
The fraction of reference objects successfully identified: TP / (TP + FN)

### Residual
The difference between an observed and computed measurement (e.g., RA or Dec).

### Right Ascension (RA)
Angular distance of a celestial object measured eastward along the celestial equator from the vernal equinox, typically in degrees or hours.

---

## S

### SDA (Space Domain Awareness)
Understanding the space environment, including tracking of space objects, prediction of conjunctions, and characterization of threats.

### SGP4/SDP4
Standard propagation models used with TLEs. SGP4 is for near-Earth objects, SDP4 for deep space.

### Space-Track
The official U.S. Space Force website providing space catalog data and TLEs.

### SSA (Space Situational Awareness)
See SDA. An older term for the same concept.

### State Vector (SV)
A set of six numbers (position and velocity in 3D) defining a satellite's state at a given epoch.

---

## T

### TLE (Two-Line Element Set)
A standardized format for encoding orbital elements, used with SGP4/SDP4 propagators.

### Track
A series of observations believed to belong to the same object.

### True Positive (TP)
An algorithm output that correctly matches a reference object.

---

## U

### UCT (Uncorrelated Track)
A track of observations that cannot be associated with any known space object in the catalog.

### UCTP (Uncorrelated Track Processing)
The process of analyzing UCTs to determine their orbits and identify the objects.

### UDL (Unified Data Library)
A data repository providing access to space surveillance observations and catalog data.

---

## V

### Validation
The process of verifying that an algorithm implementation meets specifications and produces correct results.

### Vite
A fast build tool and development server for modern web projects. Used with React for the UCT Benchmark frontend.

---

## W

### Window Selection
The process of finding optimal time windows in observation data that meet quality criteria.

### Zustand
A lightweight state management library for React used in the UCT Benchmark frontend.

---

## Related Documentation

- [Architecture](../technical/ARCHITECTURE.md)
- [Evaluation Metrics](../technical/EVALUATION_METRICS.md)
- [Data Sources](../technical/DATA_SOURCES.md)
