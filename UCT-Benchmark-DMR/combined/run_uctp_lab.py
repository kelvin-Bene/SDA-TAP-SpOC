"""
UCTP Algorithm Lab - Standalone CLI entry point.

Usage:
    python run_uctp_lab.py --input data/output_dataset.json
    python run_uctp_lab.py --dataset-id 1
    python run_uctp_lab.py --input data/output_dataset.json --clustering angular_dbscan --iod gauss
"""

import argparse
import json
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(
        description="UCTP Algorithm Lab - Run UCT processing pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_uctp_lab.py --input data/output_dataset.json
  python run_uctp_lab.py --dataset-id 1 --output results/uctp_output.json
  python run_uctp_lab.py --input data/obs.json --clustering angular_dbscan --iod gauss --refinement none
        """,
    )

    # Input source (mutually exclusive)
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--input", "-i", type=str, help="Path to input observation JSON file")
    input_group.add_argument("--dataset-id", type=int, help="Database dataset ID to process")

    # Output
    parser.add_argument(
        "--output", "-o", type=str, default="data/uctp_output.json",
        help="Path to save output JSON (default: data/uctp_output.json)",
    )

    # Clustering config
    parser.add_argument(
        "--clustering", type=str, default="angular_dbscan",
        choices=["angular_dbscan", "stonesoup_mht", "stonesoup_gnn"],
        help="Clustering method (default: angular_dbscan)",
    )
    parser.add_argument("--eps-deg", type=float, default=0.5, help="DBSCAN epsilon in degrees")
    parser.add_argument("--min-samples", type=int, default=3, help="DBSCAN minimum samples")

    # IOD config
    parser.add_argument(
        "--iod", type=str, default="gauss",
        choices=["gauss", "orbdetpy_laplace", "orekit_gooding"],
        help="IOD method (default: gauss)",
    )

    # Refinement config
    parser.add_argument(
        "--refinement", type=str, default="none",
        choices=["none", "batch_least_squares", "ekf", "ukf"],
        help="Refinement method (default: none)",
    )

    # Pipeline options
    parser.add_argument("--name", type=str, default="cli_run", help="Run name")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()

    # Configure logging
    from loguru import logger
    if not args.verbose:
        logger.remove()
        logger.add(sys.stderr, level="INFO")

    # Build config
    from uct_benchmark.uctp_lab.config import (
        ClusteringConfig,
        ClusteringMethod,
        IODConfig,
        IODMethod,
        RefinementConfig,
        RefinementMethod,
        UCTPConfig,
    )

    config = UCTPConfig(
        name=args.name,
        input_path=args.input,
        dataset_id=args.dataset_id,
        output_path=args.output,
        clustering=ClusteringConfig(
            method=ClusteringMethod(args.clustering),
            eps_deg=args.eps_deg,
            min_samples=args.min_samples,
        ),
        iod=IODConfig(
            method=IODMethod(args.iod),
        ),
        refinement=RefinementConfig(
            method=RefinementMethod(args.refinement),
        ),
    )

    # Run pipeline
    from uct_benchmark.uctp_lab.pipeline import UCTPPipeline

    def print_progress(stage: str, fraction: float):
        bar_len = 30
        filled = int(bar_len * fraction)
        bar = "=" * filled + "-" * (bar_len - filled)
        print(f"\r  [{bar}] {stage}: {fraction*100:.0f}%", end="", flush=True)
        if fraction >= 1.0:
            print()

    pipeline = UCTPPipeline(config, progress_callback=print_progress)
    result = pipeline.run()

    # Print summary
    print("\n" + "=" * 60)
    print("UCTP Pipeline Results")
    print("=" * 60)
    m = result.metrics
    print(f"  Observations:     {m.total_observations}")
    print(f"  Clusters found:   {m.clusters_found}")
    print(f"  Noise points:     {m.noise_observations}")
    print(f"  IOD success:      {m.iod_succeeded}/{m.iod_attempted}")
    print(f"  Objects resolved: {m.objects_resolved}")
    print(f"  Elapsed time:     {m.elapsed_seconds:.2f}s")

    if result.error:
        print(f"\n  ERROR: {result.error}")
        sys.exit(1)

    if result.output_path:
        print(f"\n  Output saved to: {result.output_path}")

    print("=" * 60)


if __name__ == "__main__":
    main()
