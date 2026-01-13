# -*- coding: utf-8 -*-
"""
Created on Fri Jun 20 15:41:21 2025

@author: Gabriel Lundin
"""

import os


def main():
    """Main pipeline function."""
    # Change the working directory in case it was messed up
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    # Generate dataset
    # print("Generating sample dataset")
    # subprocess.run([sys.executable, "Create_Dataset.py"], check=True)

    # Run dummy UCTP
    from uct_benchmark.uctp.dummyUCTP import dummy as UCTP

    print("Running dummy UCTP")
    UCTP("./data/ref_obs.csv", "")

    # Run evaluation
    # print("Beginning Eval")
    # subprocess.run([sys.executable, "Evaluation.py"], check=True)


if __name__ == "__main__":
    main()
