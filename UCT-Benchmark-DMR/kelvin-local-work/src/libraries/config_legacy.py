# -*- coding: utf-8 -*-
"""
Created on Fri Jul 25 2025

@author: Louis Caves
"""

## Congiuration file to define variables used elsewhere in the product

# Calibration Satellites
satIDs = [1328, 5398, 7646, 8820, 16908, 19751, 20026, 22195, 22314, 22824, 23613, 24876, 25544, 26360, 27566, 27944, 32711, 36508, 39070, 39086, 39504, 40730, 41240, 41335, 42915, 43476, 43477, 43873, 46826, 48859]


## --- Dataset Codes: Define thresholds --- ##
# Define size of orbital regime by semimajor axis in km
semiMajorAxis_LEO = 8378 # LEO is less than this (correponds to mean altitude <2000km)
semiMajorAxis_GEO = 42164 # GEO is greater than or equal to this
# MEO is defined as not LEO or GEO

# Define highly eccentric orbit (HEO) threshold
eccentricity_HEO = 0.7 # a HEO object has eccentricity greater than or equal to this value

# percentage thresholds for what is high (A), standard (S), and low (N) percentage for orbital coverage, observation count, and track gap
# lower, taget, and upper bounds in acending order
# (set arbitrarily) #
highPercentage = (0.9,0.95,1.0)
standardPercentage = (0.4,0.5,0.6)
lowPercentage = (0.0,0.05,0.1)

# What is considered low orbital coverage (percentage), defined differently for LEO, MEO, and GEO
# Orbit coverage is taken over a timespan of 3 orbital periods
# Determined from taking bottom 25 percentile of orbit coverage from real observation data over a 10 day window
lowCoverage_LEO = 0.0213
lowCoverage_MEO = 0.0449
lowCoverage_GEO = 41.656
# orbital coverage below which is too small to include in datasets
# (set arbitrarily, arbitrarily assumed to be the same for all regimes) #
tooLowtoInclude = 0.001 

# What is considered a long track gap (longest duration between tracks in units of orbital period)
# This value was specified by Major Allen
longTrackGap = 2

# What is considered a low or high obervation count (number of observations per 3 days)
# Link to paper providing justification for these values in documentation
lowObsCount = 50
highObsCount = 150

# Define high (H), standard (S), and low (L) object count to put in each dataset
# Values determined from conversation with LSAS regarding expected number of objects fit for real UCT data
highObjectCount = 80
standardObjectCount = 40
lowObjectCount = 10

## --- Window Selection: Batch Size for pulling data --- ##
# (set arbitrarily) #
batchSizeMultiplier = 5
batchSizeDecayRate = 0.01

# Set slide resolution to zero if point by point (slow) window selection is desired
slide_resolution = .1

# Create target thresholds list of arbitrary length for dataset checking of a specific iteration
thresholds = ["T1", "T2", "T2", "T3", "T3", "T3", "T4", "T4", "T4", "T4"]

## --- Propagator Model --- ##
#  Define default parameters for solar radiation pressure and atmospheric drag
# (set arbitrarily, need to alter with justification) #
solarRadPresCoef = 1.5
dragCoef = 2.5

# Define default number of monte carlo sample points used to propagate covariance
# (set arbitrarily, can also change propagation function to propagate covariance with STM to not need MC)
monteCarloPoints = 100


## --- Simulation Parameters --- ##
# Noise added to simulated observations is gaussian in position and nagular position (RA/dec)
# Covariance for each is identity scaled by the factor below. Position is in units of km and angular position is in units of radians
# (set arbitrrily)
positionNoise = 0.01
arcseconds2radians = 3600
angularNoise = (1)*arcseconds2radians

