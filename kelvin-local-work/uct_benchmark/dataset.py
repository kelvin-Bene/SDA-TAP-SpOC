"""Dataset creation and management module."""

from pathlib import Path

from loguru import logger
import typer

from uct_benchmark.config import PROCESSED_DATA_DIR, RAW_DATA_DIR

app = typer.Typer()


@app.command()
def scrape_satellite_data():
    """Scrape and save satellite data from external sources."""
    logger.info("Starting satellite data scraping...")
    # Import here to avoid circular imports
    from uct_benchmark.utils.scrape_satellite_data import main as scrape_and_save_satellite_data

    scrape_and_save_satellite_data()
    logger.success("Satellite data scraping complete.")


@app.command()
def create():
    """Create a new benchmark dataset."""
    logger.info("Starting dataset creation...")
    # Import here to avoid circular imports
    from uct_benchmark.Create_Dataset import main as create_main

    create_main()


@app.command()
def evaluate():
    """Evaluate UCTP algorithm performance."""
    logger.info("Starting evaluation...")
    # Import here to avoid circular imports
    from uct_benchmark.Evaluation import main as eval_main

    eval_main()


@app.command()
def pipeline():
    """Run the complete pipeline (create dataset, run UCTP, evaluate)."""
    logger.info("Starting full pipeline...")
    # Import here to avoid circular imports
    from uct_benchmark.MainMVP import main as pipeline_main

    pipeline_main()


@app.command()
def process(
    # ---- REPLACE DEFAULT PATHS AS APPROPRIATE ----
    input_path: Path = RAW_DATA_DIR / "dataset.csv",
    output_path: Path = PROCESSED_DATA_DIR / "dataset.csv",
    # ----------------------------------------------
):
    """Process raw dataset files."""
    logger.info(f"Processing dataset from {input_path} to {output_path}...")
    # Add actual processing logic here
    logger.success("Processing dataset complete.")


if __name__ == "__main__":
    app()
