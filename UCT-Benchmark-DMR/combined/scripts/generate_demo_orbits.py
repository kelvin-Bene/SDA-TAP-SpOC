"""One-off generator for frontend/public/demo-orbits.json.

Produces a four-satellite demo scene (ISS LEO, GPS MEO, GOES-16 GEO, Molniya HEO)
for the public LandingPage 3D globe. Uses pure two-body Keplerian propagation —
no Orekit dependency — because the landing page is marketing, not science, and
visual accuracy of a few km is fine.

Run with: python scripts/generate_demo_orbits.py
Output:   frontend/public/demo-orbits.json (~20KB)
"""

from __future__ import annotations

import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path

MU_EARTH = 398600.4418  # km^3/s^2


def _rotate_x(v: tuple[float, float, float], angle: float) -> tuple[float, float, float]:
    c, s = math.cos(angle), math.sin(angle)
    x, y, z = v
    return (x, c * y - s * z, s * y + c * z)


def _rotate_z(v: tuple[float, float, float], angle: float) -> tuple[float, float, float]:
    c, s = math.cos(angle), math.sin(angle)
    x, y, z = v
    return (c * x - s * y, s * x + c * y, z)


def _eccentric_anomaly(M: float, e: float, tol: float = 1e-10) -> float:
    """Solve Kepler's equation M = E - e sin E for E."""
    E = M if e < 0.8 else math.pi
    for _ in range(50):
        f = E - e * math.sin(E) - M
        fp = 1.0 - e * math.cos(E)
        dE = f / fp
        E -= dE
        if abs(dE) < tol:
            break
    return E


def propagate_kepler(
    sma_km: float,
    ecc: float,
    inc_deg: float,
    raan_deg: float,
    argp_deg: float,
    mean_anom0_deg: float,
    epoch: datetime,
    duration_s: float,
    samples: int,
) -> list[dict]:
    """Sample a Keplerian orbit over a time window.

    Returns a list of {time, x, y, z} with positions in km in an Earth-centered
    inertial frame (EME2000-ish; exact axis orientation is unimportant for the
    demo). Units: km, seconds.
    """
    n = math.sqrt(MU_EARTH / sma_km ** 3)  # mean motion rad/s
    inc = math.radians(inc_deg)
    raan = math.radians(raan_deg)
    argp = math.radians(argp_deg)
    M0 = math.radians(mean_anom0_deg)

    positions: list[dict] = []
    for i in range(samples):
        t = duration_s * i / (samples - 1)
        M = M0 + n * t
        E = _eccentric_anomaly(M, ecc)
        cos_nu = (math.cos(E) - ecc) / (1.0 - ecc * math.cos(E))
        sin_nu = (math.sqrt(1.0 - ecc * ecc) * math.sin(E)) / (1.0 - ecc * math.cos(E))
        r = sma_km * (1.0 - ecc * math.cos(E))
        x_orb = r * cos_nu
        y_orb = r * sin_nu
        z_orb = 0.0
        # Rotate from orbital frame to inertial: Rz(-argp) -> Rx(-inc) -> Rz(-raan)
        p = _rotate_z((x_orb, y_orb, z_orb), argp)
        p = _rotate_x(p, inc)
        p = _rotate_z(p, raan)
        positions.append(
            {
                "time": (epoch + timedelta(seconds=t)).isoformat(),
                "x": p[0],
                "y": p[1],
                "z": p[2],
            }
        )
    return positions


def orbital_period_s(sma_km: float) -> float:
    return 2 * math.pi * math.sqrt(sma_km ** 3 / MU_EARTH)


def main() -> None:
    epoch = datetime(2026, 4, 16, 0, 0, 0, tzinfo=timezone.utc)
    samples = 60

    # Each satellite's time window = 2 orbital periods so the track visually
    # closes on itself once and a bit (helps communicate "this is an orbit").
    scene = [
        {
            "name": "ISS",
            "regime": "LEO",
            "color": "#8AD7FF",
            "sma": 6798.0,  # km, ~420 km altitude
            "ecc": 0.0003,
            "inc": 51.64,
            "raan": 120.0,
            "argp": 0.0,
            "m0": 0.0,
        },
        {
            "name": "GPS IIF-10",
            "regime": "MEO",
            "color": "#C4B6FF",
            "sma": 26560.0,
            "ecc": 0.01,
            "inc": 55.0,
            "raan": 30.0,
            "argp": 90.0,
            "m0": 45.0,
        },
        {
            "name": "GOES-16",
            "regime": "GEO",
            "color": "#FFD28A",
            "sma": 42164.0,
            "ecc": 0.0001,
            "inc": 0.1,
            "raan": 0.0,
            "argp": 0.0,
            "m0": 180.0,
        },
        {
            "name": "Molniya",
            "regime": "HEO",
            "color": "#FF9E8A",
            "sma": 26600.0,
            "ecc": 0.74,
            "inc": 63.4,
            "raan": 240.0,
            "argp": 270.0,
            "m0": 20.0,
        },
    ]

    satellites = []
    for i, s in enumerate(scene):
        period = orbital_period_s(s["sma"])
        duration = 2.0 * period
        positions = propagate_kepler(
            sma_km=s["sma"],
            ecc=s["ecc"],
            inc_deg=s["inc"],
            raan_deg=s["raan"],
            argp_deg=s["argp"],
            mean_anom0_deg=s["m0"],
            epoch=epoch,
            duration_s=duration,
            samples=samples,
        )
        satellites.append(
            {
                "id": f"demo-{i + 1}",
                "name": s["name"],
                "regime": s["regime"],
                "color": s["color"],
                "positions": positions,
            }
        )

    # Pick a global time window that all four tracks share a point for
    # (start is common; end is each track's own).
    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "start_time": epoch.isoformat(),
        "end_time": (epoch + timedelta(seconds=2 * orbital_period_s(scene[2]["sma"]))).isoformat(),
        "satellites": satellites,
    }

    repo_root = Path(__file__).resolve().parent.parent
    out_path = repo_root / "frontend" / "public" / "demo-orbits.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output, indent=2))
    size_kb = out_path.stat().st_size / 1024
    print(f"Wrote {out_path} ({size_kb:.1f} KB)")


if __name__ == "__main__":
    main()
