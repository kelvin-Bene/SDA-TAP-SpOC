# uct-benchmark

<a target="_blank" href="https://cookiecutter-data-science.drivendata.org/">
    <img src="https://img.shields.io/badge/CCDS-Project%20template-328F97?logo=cookiecutter" />
</a>

A framework for UCT benchmark dataset generation and UCTP evaluation

## Getting Started
First review the overall [Project Organization](#project-organization).

Next, follow the [Installation Instructions](INSTALLATION.md) to set up your development environment.

## Project Organization

```
├── LICENSE            <- Open-source license if one is chosen
├── Makefile           <- Makefile with convenience commands like `make data` or `make train`
├── README.md          <- The top-level README for developers using this project.
├── data
│   ├── external       <- Data from third party sources.
│   ├── interim        <- Intermediate data that has been transformed.
│   ├── processed      <- The final, canonical data sets for modeling.
│   └── raw            <- The original, immutable data dump.
│
├── docs               <- A default mkdocs project; see www.mkdocs.org for details
│
├── notebooks          <- Jupyter notebooks. Naming convention is a number (for ordering),
│                         the creator's initials, and a short `-` delimited description, e.g.
│                         `1.0-jqp-initial-data-exploration`.
│
├── pyproject.toml     <- Project configuration file with package metadata for 
│                         uct_benchmark and configuration for tools like black
│
├── references         <- Data dictionaries, manuals, and all other explanatory materials.
│
├── reports            <- Generated analysis as HTML, PDF, LaTeX, etc.
│   └── figures        <- Generated graphics and figures to be used in reporting
│
├── requirements.txt   <- The requirements file for reproducing the analysis environment, e.g.
│                         generated with `pip freeze > requirements.txt`
│
├── setup.cfg          <- Configuration file for flake8
│
├── src/               <- Original source code for use in this project (legacy; see uct_benchmark/)
│
└── uct_benchmark   <- Source code for use in this project.
    │
    ├── __init__.py             <- Makes uct_benchmark a Python module
    │
    ├── api/                    <- api submodule to handle external API calls
    │
    ├── batchPull.py            <- Scripts for batch pulling observation data from APIs
    │    
    ├── config.py               <- Store useful variables and configuration
    │
    ├── Create_Dataset.py       <- Scripts to create benchmark datasets
    │
    ├── data/                   <- Dataset creation, windowing, and scoring logic
    │
    ├── dataset.py              <- Dataset generation scripts
    │
    ├── evaluation/             <- Metrics and performance assessment
    │
    ├── Evaluation.py           <- Evaluation scripts
    │
    ├── MainMVP.py              <- Main script to run end-to-end benchmark
    │
    ├── simulation/             <- Orbit propagation and observation simulation
    │
    ├── uctp/                   <- UCTP algorithm implementations
    │
    └── utils/                  <- Utility functions and helpers
```

--------

