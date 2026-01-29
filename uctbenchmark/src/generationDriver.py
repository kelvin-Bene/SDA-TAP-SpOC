'''Author: Cameron Smith'''

#imports
import pandas as pd
import os
from uctbenchmark.src.libraries.windowTools import setRecycler,codeGenerator, createDatasetCodeGUI, DatasetCode
import itertools as it
import ast
import uctbenchmark.src.libraries.apiIntegration as UDL
from batchPull import batchPull

db_csv = os.getenv("DB_CSV")
sat_data = os.getenv("SAT_DATA")
dummy_data = os.getenv('DUMMY_DATA')

#run file name combinator
parameters = createDatasetCodeGUI()
#generate codes
dataset_codes = codeGenerator(parameters)

#check for conflicts involving track gap and short time window
conflicted_codes = [code for code in dataset_codes
                    if code.TrackGapPer != 'N' and code.Regime == 'GEO' and int(code.TimeWindow)<3]
if len(conflicted_codes) != 0:
    print ('The following datasets cannot be generated due to regime/timewindow/period between obs parameter conflicts:')
    print (conflicted_codes)

#remove conflicted codes from list
deconflicted_codes = []
deconflicted_codes = list(set(dataset_codes)-set(conflicted_codes))

possible_conflicted_codes = [code for code in dataset_codes
                             if code.TrackGapPer != 'N' and code.Regime == 'MEO' and int(code.TimeWindow)<2
                             or code.TrackGapPer != 'N' and code.Regime == 'HEO' and int(code.TimeWindow)<2
                             or code.TrackGapPer != 'N' and code.Regime == 'MGO' and int(code.TimeWindow)<2
                             or code.TrackGapPer != 'N' and code.Regime == 'GHO' and int(code.TimeWindow)<2
                             or code.TrackGapPer != 'N' and code.Regime == 'MHO' and int(code.TimeWindow)<2
                             or code.TrackGapPer != 'N' and code.Regime == 'MGH' and int(code.TimeWindow)<2]
if len(possible_conflicted_codes) != 0:
    print ('Due to parameter conflicts, the following datasets may be difficult to generate and likely require simulation')
    print (possible_conflicted_codes)

    #feed list to recycler
#recycler returns list of codes and recyclable candidates
existing_sets = [DatasetCode(set) for set in pd.read_csv(dummy_data)]

(redundant_sets, internal_recyclable_sets, unrecyclable_sets, recyclable_sets) = setRecycler(deconflicted_codes,existing_sets)

##window selection or unrecyclable sets
#divide by event and nonevent codes
event_spec_codes = []

nonevent_codes = []
event_spec_codes = [code for code in unrecyclable_sets if code.Event != 'NE']
nonevent_codes = [code for code in unrecyclable_sets if code.Event == 'NE']
print('Nonevent Codes',nonevent_codes)
print('Event Specific Codes',event_spec_codes)

#read satellite object type info
candidate_objects = pd.read_csv(sat_data)  

UDL_token=UDL.UDLTokenGen('username','Password')

from libraries.windowCheck import windowMain
# window selection
df=windowMain(nonevent_codes,UDL_token)