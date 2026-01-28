# -*- coding: utf-8 -*-
"""
Created on Fri Jun 20 15:41:21 2025
Last Edit: October 11 2025 (Jovan Bergh)

@author: Gabriel Lundin
"""

import os, sys, subprocess, time
from dotenv import load_dotenv
from libraries.dummyUCTP import dummy as UCTP
import Create_Dataset


load_dotenv() #Loading environment variables

home_dir = os.getenv("HOME_DIR")
src_dir = os.getenv("SRC_DIR")
ref_obs = os.getenv("REF_OBS")


# Change the working directory 
os.chdir(src_dir)

# Generate dataset
print("Running sample dataset GUI")
time.sleep(2)
Create_Dataset()

# Run dummy UCTP
print("Running dummy UCTP")
UCTP(ref_obs, "")

# Run evaluation
#print("Beginning Eval")
#subprocess.run([sys.executable, "Evaluation.py"], check=True)