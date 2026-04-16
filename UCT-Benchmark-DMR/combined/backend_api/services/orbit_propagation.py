"""Orbit propagation service for 3D globe visualization.

Wraps `uct_benchmark.simulation.propagator.ephemerisPropagator` with disk
caching and Orekit JVM warm-up. Produces time-sampled position tracks
suitable for the frontend `OrbitViewer` Cesium component.

Coordinate frame: EME2000 (J2000 ECI), positions in km.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

CACHE_ROOT = Path("cache/orbit_viz")
DEFAULT_MAX_SAMPLES = 2000
DEFAULT_PER_SAT_SAMPLES = 120
DEFAULT_WINDOW_HOURS = 24.0
EARTH_MU_KM3_S2 = 398600.4418

_JVM_WARMED = False


@dataclass
class OrbitPosition:
    time: str  # ISO8601 UTC
    x: float  # km (EME2000 ECI)
    y: float
    z: float


@dataclass
class SatelliteTrack:
    id: str
    name: str
    regime: str  # 'LEO' | 'MEO' | 'GEO' | 'HEO'
    positions: list[dict] = field(default_factory=list)
    color: Optional[str] = None


def _cache_path(dataset_id: int, start: datetime, end: datetime, max_samples: int) -> Path:
    key = f"dataset_{dataset_id}_{int(start.timestamp())}_{int(end.timestamp())}_{max_samples}.json"
    return CACHE_ROOT / key


def _submission_cache_path(submission_id: int, max_samples: int) -> Path:
    return CACHE_ROOT / f"submission_{submission_id}_{max_samples}.json"


def _sma_eccentricity(state_km: np.ndarray) -> tuple[float, float]:
    """Compute SMA (km) and eccentricity from a Cartesian state [x,y,z,vx,vy,vz] in km, km/s."""
    r = state_km[:3]
    v = state_km[3:]
    r_mag = float(np.linalg.norm(r))
    v_mag = float(np.linalg.norm(v))
    if r_mag == 0:
        return float("inf"), 1.0
    specific_energy = v_mag * v_mag / 2.0 - EARTH_MU_KM3_S2 / r_mag
    if specific_energy >= 0:
        return float("inf"), 1.0
    sma = -EARTH_MU_KM3_S2 / (2.0 * specific_energy)
    h = np.cross(r, v)
    ecc_vec = np.cross(v, h) / EARTH_MU_KM3_S2 - r / r_mag
    ecc = float(np.linalg.norm(ecc_vec))
    return float(sma), ecc


def _orbital_period_s(sma_km: float) -> float:
    """Kepler's third law: T = 2*pi*sqrt(a^3/mu)."""
    if not np.isfinite(sma_km) or sma_km <= 0:
        return 3600.0 * DEFAULT_WINDOW_HOURS
    return float(2 * np.pi * np.sqrt(sma_km ** 3 / EARTH_MU_KM3_S2))


def warm_jvm() -> None:
    """Pay the Orekit JVM cold-start cost once. Safe to call multiple times."""
    global _JVM_WARMED
    if _JVM_WARMED:
        return
    try:
        from uct_benchmark.simulation.propagator import ephemerisPropagator

        state = np.array([7000.0, 0.0, 0.0, 0.0, 7.5, 0.0], dtype=float)
        epoch = datetime(2026, 1, 1, tzinfo=timezone.utc)
        ephemerisPropagator(state, epoch, [epoch + timedelta(seconds=60)])
        _JVM_WARMED = True
        logger.info("Orekit JVM warmed up for orbit_propagation service")
    except Exception as e:  # pragma: no cover - infrastructure warm-up
        logger.warning("Orekit JVM warm-up failed (will lazy-init on first request): %s", e)


def _read_cache(path: Path) -> Optional[list[SatelliteTrack]]:
    if not path.exists():
        return None
    try:
        raw = json.loads(path.read_text())
        return [SatelliteTrack(**d) for d in raw]
    except Exception as e:
        logger.warning("Cache read failed for %s: %s", path, e)
        return None


def _write_cache(path: Path, tracks: list[SatelliteTrack]) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps([asdict(t) for t in tracks]))
    except Exception as e:
        logger.warning("Cache write failed for %s: %s", path, e)


def _propagate_single(
    state_km: np.ndarray,
    epoch: datetime,
    sample_times: list[datetime],
    mass: float,
    cross_section: float,
    drag_coeff: float,
    srp_coeff: float,
) -> list[dict]:
    """Propagate one state vector to each sample time. Returns [{time, x, y, z}] in km."""
    from uct_benchmark.simulation.propagator import ephemerisPropagator

    propagated = ephemerisPropagator(
        state_km,
        epoch,
        sample_times,
        satelliteParameters=[mass, cross_section, drag_coeff, srp_coeff],
    )
    positions: list[dict] = []
    for t, sv in zip(sample_times, propagated):
        positions.append(
            {
                "time": t.astimezone(timezone.utc).isoformat(),
                "x": float(sv[0]),
                "y": float(sv[1]),
                "z": float(sv[2]),
            }
        )
    return positions


def propagate_reference_orbits(
    dataset_id: int,
    db,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    max_samples: int = DEFAULT_MAX_SAMPLES,
) -> list[SatelliteTrack]:
    """Return time-sampled reference orbits for a dataset's satellites.

    Reads reference state vectors from `state_vectors` joined with
    `dataset_references` and `satellites`, then propagates each forward using
    `ephemerisPropagator`. Results are cached on disk keyed by
    (dataset_id, start, end, max_samples).
    """
    from uct_benchmark.utils.orbital import determine_orbital_regime

    ref_sv = db.adapter.fetchdf(
        """
        SELECT
            sv.sat_no,
            s.name AS sat_name,
            s.orbital_regime AS sat_regime,
            sv.epoch,
            sv.x_pos AS xpos, sv.y_pos AS ypos, sv.z_pos AS zpos,
            sv.x_vel AS xvel, sv.y_vel AS yvel, sv.z_vel AS zvel,
            COALESCE(s.mass_kg,         1000.0) AS mass,
            COALESCE(s.cross_section_m2,  10.0) AS cross_section,
            COALESCE(s.drag_coeff,         2.2) AS drag_coeff,
            COALESCE(s.srp_coeff,          1.3) AS srp_coeff
        FROM state_vectors sv
        JOIN dataset_references dr ON sv.id = dr.state_vector_id
        LEFT JOIN satellites s ON sv.sat_no = s.sat_no
        WHERE dr.dataset_id = ?
        ORDER BY sv.sat_no
        """,
        (dataset_id,),
    )

    if ref_sv.empty:
        return []

    ref_sv["epoch"] = pd.to_datetime(ref_sv["epoch"], utc=True)

    if start is None:
        start = ref_sv["epoch"].min().to_pydatetime()
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    if end is None:
        end = start + timedelta(hours=DEFAULT_WINDOW_HOURS)
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)

    cache_path = _cache_path(dataset_id, start, end, max_samples)
    cached = _read_cache(cache_path)
    if cached is not None:
        return cached

    warm_jvm()

    sat_count = len(ref_sv)
    per_sat = max(10, min(DEFAULT_PER_SAT_SAMPLES, max_samples // max(sat_count, 1)))
    total_seconds = (end - start).total_seconds()
    sample_times = [
        start + timedelta(seconds=total_seconds * i / (per_sat - 1))
        for i in range(per_sat)
    ]

    tracks: list[SatelliteTrack] = []
    for _, row in ref_sv.iterrows():
        state = np.array(
            [row["xpos"], row["ypos"], row["zpos"], row["xvel"], row["yvel"], row["zvel"]],
            dtype=float,
        )
        # Prefer stored regime on satellites table; fall back to computation.
        regime = row.get("sat_regime")
        if not regime or regime not in ("LEO", "MEO", "GEO", "HEO"):
            sma, ecc = _sma_eccentricity(state)
            regime = determine_orbital_regime(sma, ecc)

        try:
            epoch_dt = row["epoch"].to_pydatetime() if hasattr(row["epoch"], "to_pydatetime") else row["epoch"]
            positions = _propagate_single(
                state,
                epoch_dt,
                sample_times,
                mass=float(row["mass"]),
                cross_section=float(row["cross_section"]),
                drag_coeff=float(row["drag_coeff"]),
                srp_coeff=float(row["srp_coeff"]),
            )
        except Exception as e:
            logger.warning("Propagation failed for sat %s: %s", row["sat_no"], e)
            continue

        tracks.append(
            SatelliteTrack(
                id=str(row["sat_no"]),
                name=row["sat_name"] or f"SAT-{row['sat_no']}",
                regime=regime,
                positions=positions,
            )
        )

    _write_cache(cache_path, tracks)
    return tracks


def propagate_predictions(
    uctp_path: Path,
    submission_id: Optional[int] = None,
    max_samples: int = DEFAULT_MAX_SAMPLES,
) -> list[SatelliteTrack]:
    """Return time-sampled predicted orbits from a UCTP output file.

    UCTP files contain a list of state vectors per satellite. If a satellite has
    >=2 state vectors, those are used directly as sample points. Otherwise the
    single state vector is propagated forward one orbital period.
    """
    from uct_benchmark.utils.orbital import determine_orbital_regime

    if submission_id is not None:
        cached = _read_cache(_submission_cache_path(submission_id, max_samples))
        if cached is not None:
            return cached

    raw = json.loads(Path(uctp_path).read_text())
    # UCTP is typically a list of {idStateVector | satelliteId, epoch, xpos, ypos, zpos, xvel, yvel, zvel, ...}
    entries = raw if isinstance(raw, list) else raw.get("stateVectors", [])

    by_sat: dict[str, list[dict]] = {}
    for entry in entries:
        sat_id = str(
            entry.get("idStateVector")
            or entry.get("satelliteId")
            or entry.get("satNo")
            or entry.get("sat_no")
            or "unknown"
        )
        by_sat.setdefault(sat_id, []).append(entry)

    warm_jvm_needed = any(len(v) < 2 for v in by_sat.values())
    if warm_jvm_needed:
        warm_jvm()

    tracks: list[SatelliteTrack] = []
    sat_count = max(len(by_sat), 1)
    per_sat_target = max(10, min(DEFAULT_PER_SAT_SAMPLES, max_samples // sat_count))

    for sat_id, states in by_sat.items():
        states_sorted = sorted(states, key=lambda s: s.get("epoch", ""))
        try:
            first_state = np.array(
                [
                    float(states_sorted[0]["xpos"]),
                    float(states_sorted[0]["ypos"]),
                    float(states_sorted[0]["zpos"]),
                    float(states_sorted[0]["xvel"]),
                    float(states_sorted[0]["yvel"]),
                    float(states_sorted[0]["zvel"]),
                ],
                dtype=float,
            )
        except (KeyError, ValueError, TypeError) as e:
            logger.warning("Could not parse UCTP state for sat %s: %s", sat_id, e)
            continue

        sma, ecc = _sma_eccentricity(first_state)
        regime = determine_orbital_regime(sma, ecc)

        if len(states_sorted) >= 2:
            positions = []
            for entry in states_sorted:
                try:
                    positions.append(
                        {
                            "time": datetime.fromisoformat(
                                entry["epoch"].replace("Z", "+00:00")
                            ).isoformat(),
                            "x": float(entry["xpos"]),
                            "y": float(entry["ypos"]),
                            "z": float(entry["zpos"]),
                        }
                    )
                except Exception as e:
                    logger.debug("Skipping unparseable UCTP row: %s", e)
                    continue
        else:
            epoch_str = states_sorted[0]["epoch"].replace("Z", "+00:00")
            epoch_dt = datetime.fromisoformat(epoch_str)
            if epoch_dt.tzinfo is None:
                epoch_dt = epoch_dt.replace(tzinfo=timezone.utc)
            period_s = _orbital_period_s(sma)
            sample_times = [
                epoch_dt + timedelta(seconds=period_s * i / (per_sat_target - 1))
                for i in range(per_sat_target)
            ]
            try:
                positions = _propagate_single(
                    first_state,
                    epoch_dt,
                    sample_times,
                    mass=1000.0,
                    cross_section=10.0,
                    drag_coeff=2.2,
                    srp_coeff=1.3,
                )
            except Exception as e:
                logger.warning("UCTP propagation failed for sat %s: %s", sat_id, e)
                continue

        tracks.append(
            SatelliteTrack(
                id=sat_id,
                name=f"SAT-{sat_id}",
                regime=regime,
                positions=positions,
            )
        )

    if submission_id is not None:
        _write_cache(_submission_cache_path(submission_id, max_samples), tracks)

    return tracks
