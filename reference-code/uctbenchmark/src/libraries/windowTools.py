
"""
Created on Thu Jul 30 2025

@author: Cameron Smith
"""
#imports
import pandas as pd
import numpy as np
import ast
from itertools import product
import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import sys

#create dataset code class object
class DatasetCode:
    regime_ranges = { #in kilometers
        'LEO':'<2000',
        'MEO':'2000..35786',
        'GEO':'>35786'
    }
    
    #dict of regime and all regimes containing that regime
    regime_superiors = {
        'LEO':['LMO','LGO','LHO','LMG','LMH','LGH','ALL'],
        'MEO':['LMO','MGO','MHO','LMG','LMH','MGH','ALL'],
        'GEO':['LGO','MGO','GHO','LMG','LGH','MGH','ALL'],
        'HEO':['LHO','MHO','GHO','LMH','LGH','MGH','ALL'],
        'LMO':['LMG','LMH','ALL'],
        'LGO':['LMG','LGH','ALL'],
        'LHO':['LMH','LGH','ALL'],
        'MGO':['LMG','MGH','ALL'],
        'MHO':['LMH','MGH','ALL'],
        'GHO':['LGH','MGH','ALL'],
        'ALL':[]}
    
    #sensor param and sensor param that contains them
    sensor_superiors = {
        'OP': ['OR','RO','FU','OP'],
        'RA': ['RR','RO','FU','RA'],
        'RF': ['OR','RR','RF','FU'],}
    
    #UDL service names
    sensor_type_queries = {
        'OP': 'eoobservation',
        'RA': 'radarobservation',
        'RF': 'rfobservation'
    }
    
    #dicts of params in order of least to most data required
    obs_count_hierarchy = {'A':0,'S':1,'N':2}

    coverage_hierarchy = {'A':0,'S':1,'N':2}

    obj_count_hierarchy = {'L':0,'S':1,'H':2}

    track_gap_hierarchy = {'A':0,'S':1,'N':2}

    #less than function that compares two dataset codes for if one could be recycled from another
    def __lt__(self, other):
        if ((self.ObjType==other.ObjType or self.ObjType=='U')
        and (self.ObjDist<=other.ObjDist or self.ObjDist=='UN')
        and (self.Regime==other.Regime or other.Regime in self.regime_superiors[self.Regime])
        and (self.Event==other.Event or self.Event=='NE')
        and (self.SensorType==other.SensorType or other.SensorType=='FU' or other.SensorType in self.sensor_superiors[self.SensorType])
        and (self.coverage_hierarchy[self.PercentOrb] <= self.coverage_hierarchy[other.PercentOrb])
        and (self.track_gap_hierarchy[self.TrackGapPer] <= self.track_gap_hierarchy[other.TrackGapPer])
        and (self.obs_count_hierarchy[self.ObsCount]<=self.obs_count_hierarchy[other.ObsCount])
        and (self.obj_count_hierarchy[self.ObjCount] <= self.obj_count_hierarchy[other.ObjCount])
        and (self.TimeWindow <= other.TimeWindow)):
            return True
        else: return False
        
    '''def __init__(self,ObjType,ObjDist,Regime,Event,SensorType,PercentOrb,TrackGapPer,
                ObsCount,ObjCount,TimeWindow):
        self.ObjType = ObjType
        self.ObjDist = ObjDist
        self.Regime = Regime
        self.Event = Event
        self.SensorType = SensorType
        self.PercentOrb = PercentOrb
        self.TrackGapPer = TrackGapPer
        self.ObsCount = ObsCount
        self.ObjCount = ObjCount
        self.TimeWindow = TimeWindow'''
    def __init__(self,dscode):
        # Assign each field based on slice of code
        self.ObjType = dscode[0]
        self.ObjDist = dscode[1:3]
        self.Regime = dscode[3:6]
        self.Event = dscode[6:8]
        self.SensorType = dscode[8:10]
        self.PercentOrb = dscode[10]
        self.TrackGapPer = dscode[11]
        self.ObsCount = dscode[12]
        self.ObjCount = dscode[13]
        self.TimeWindow = dscode[14:16]        
    def __str__(self):
        return f"{self.ObjType}{self.ObjDist}{self.Regime}{self.Event}{self.SensorType}" \
            f"{self.PercentOrb}{self.TrackGapPer}{self.ObsCount}{self.ObjCount}{self.TimeWindow}"
    def __repr__(self):
        return self.__str__()

def createDatasetCodeGUI():
    """
    Launches a GUI for editing dataset parameters using customtkinter.

    Functionality:
    - Presents categorized dataset parameters as checkboxes or entry fields.
    - Allows users to modify selections for target objects, distributions, regimes, events, sensors, etc.
    - Validates inputs and saves updates to a pandas DataFrame.
    - Shows success message and automatically closes the GUI after saving.

    Inputs:
    - None (default dataset parameters are hardcoded inside the function).

    Outputs:
    - Returns a pandas DataFrame with columns ["Parameter", "Value"] reflecting user selections.
    """

    # Set theme and appearance for the GUI using customtkinter
    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("blue")

    # Define default dataset parameters for each category

    target_objects = {
        'HAMR': 0,
        'Close Relative Objects': 0,
        'Close Apparent Objects': 0,
        'Unspecified': 0,
        'Calibration': 1,
    }

    object_distribution = [20]

    orbital_regime = {
        'LEO': 0,
        'MEO': 0,
        'GEO': 1,
        'HEO': 0,
        'ALL': 0,
        'LMO': 0,
        'LGO': 0,
        'LHO': 0,
        'MGO': 0,
        'MHO': 0,
        'GHO': 0,
        'LMG': 0,
        'LMH': 0,
        'LGH': 0,
        'MGH': 0,
    }

    events = {
        'Maneuvers Between Observations': 0,
        'Breakup': 0,
        'Long Duration Low Thrust': 0,
        'No Events': 1
    }

    sensor_type = {
        'Optical': 1,
        'Radar': 0,
        'RF': 0,
        'Fusion': 0,
        'Optical and RF': 0,
        'Optical and Radar': 0,
        'Radar and RF': 0,
    }

    percent_orbit = {
        'All Low Coverage': 0,
        'Some Low Coverage': 0,
        'No Low Coverage': 1,
    }

    period_between_tracks = {
        'All Long Track Gap': 0,
        'Some Long Trap Gap': 0,
        'No Long Track Gap': 1,
    }

    observation_count = {
        'All Low Obs Count': 0,
        'Some Low Obs Count': 0,
        'No Low Obs Count': 1,
    }

    total_object_count = {
        'High Object Count': 0,
        'Standard Object Count': 1,
        'Low Object Count': 0
    }

    time_window = ['02']

    # Combine all parameters into one dictionary for easier iteration
    dataset_parameters = {
        'Target Objects': target_objects,
        'Object Distribution': object_distribution,
        'Orbital Regime': orbital_regime,
        'Events': events,
        'Sensor Type': sensor_type,
        'Percent Orbit': percent_orbit,
        'Period Between Tracks': period_between_tracks,
        'Observation Count': observation_count,
        'Total Object Count': total_object_count,
        'Time Window': time_window
    }

    # Define a custom window class that displays and edits these parameters
    class ParameterEditor(ctk.CTk):
        def __init__(self):
            super().__init__()
            # Set window title and size
            self.title("Dataset Parameter Editor")
            self.geometry("850x700")

            # Create a scrollable frame inside the window to hold all widgets
            self.scroll_frame = ctk.CTkScrollableFrame(self)
            self.scroll_frame.pack(expand=True, fill="both", padx=20, pady=20)

            self.entries = {}  # To store references to input widgets for each parameter
            self.parameter_df = None  # Will hold the resulting DataFrame after saving

            # Iterate over each parameter category and create UI elements accordingly
            for group_name, group_data in dataset_parameters.items():
                # Add a bold label for the category
                label = ctk.CTkLabel(self.scroll_frame, text=group_name, font=ctk.CTkFont(weight="bold", size=16))
                label.pack(pady=(15, 5))

                # For dict type parameters, create a checkbox for each option
                if isinstance(group_data, dict):
                    self.entries[group_name] = {}
                    for key, value in group_data.items():
                        var = tk.IntVar(value=value)  # Tkinter variable to track checkbox state
                        checkbox = ctk.CTkCheckBox(self.scroll_frame, text=key, variable=var)
                        checkbox.pack(anchor='w', padx=20)
                        self.entries[group_name][key] = var  # Store variable for later retrieval

                # For list of ints, create entry widgets labeled "Value 1", "Value 2", etc.
                elif isinstance(group_data, list) and all(isinstance(x, int) for x in group_data):
                    self.entries[group_name] = []
                    for i, val in enumerate(group_data):
                        frame = ctk.CTkFrame(self.scroll_frame)  # Frame for layout
                        frame.pack(pady=2, padx=20, fill="x")
                        label = ctk.CTkLabel(frame, text=f"Value {i+1}")
                        label.pack(side="left", padx=(0, 10))
                        entry = ctk.CTkEntry(frame)  # Entry box for user input
                        entry.insert(0, str(val))
                        entry.pack(side="left")
                        self.entries[group_name].append(entry)  # Store entry widget

                # For other lists (assumed like ['02']), just one entry widget
                elif isinstance(group_data, list):
                    self.entries[group_name] = ctk.CTkEntry(self.scroll_frame)
                    self.entries[group_name].insert(0, group_data[0])
                    self.entries[group_name].pack(padx=20, pady=5)

            # Add a save button at the bottom
            save_button = ctk.CTkButton(self.scroll_frame, text="Save Changes", command=self.save_parameters)
            save_button.pack(pady=20)

        def save_parameters(self):
            updated = {}
            # Collect user inputs from the widgets
            for group, controls in self.entries.items():
                if isinstance(controls, dict):  # For checkbox groups, get 0/1 values
                    updated[group] = {k: v.get() for k, v in controls.items()}
                elif isinstance(controls, list):  # For numeric entry lists, convert to int
                    try:
                        updated[group] = [int(entry.get()) for entry in controls]
                    except ValueError:
                        # Show error if user entered non-integers
                        messagebox.showerror("Invalid Input", f"Non-integer in {group}")
                        return
                else:  # For single entries like Time Window, get the string
                    updated[group] = [controls.get()]

            # Create a DataFrame from the updated dictionary
            self.parameter_df = pd.DataFrame(updated.items(), columns=["Parameter", "Value"])
            #print("\n✅ Updated DataFrame:\n", self.parameter_df)

            # Show success message to user
            messagebox.showinfo("Success", "Parameters saved to DataFrame!")

            # Close the GUI window automatically
            self.destroy()

    # Create and run the GUI window
    app = ParameterEditor()
    app.mainloop()

    # Return the DataFrame with updated parameters after window closes
    return app.parameter_df

def codeGenerator(parameters):
    '''
    Generate a list of dataset codes representing all combinations of selected parameters.

    Input:
        parameters (DataFrame): A 10-row DataFrame where each row corresponds to a parameter category.
            - Each 'Value' field should be a dictionary or list representing selected values.
            - Boolean dictionaries indicate selected options (True/False for each key).
            - Lists are treated as directly selected values (e.g., ['1', '2']).

    Output:
        List[DatasetCode]: A list of DatasetCode objects, each created by concatenating
        one value from each selected parameter category.
    '''
    # --- Target Object Types ---
    target_mask = []
    targ_ob_dict = parameters.at[0, 'Value']  # Dictionary of object type flags (e.g., {'H': True, 'C': False, ...})
    for key in targ_ob_dict:
        target_mask.append(bool(targ_ob_dict[key]))  # Build a boolean mask
    target_objects = ["H", "C", "A", "U", "N"]
    targ_ob_comb = np.array(target_objects)[target_mask]  # Select object types that are True
    print(targ_ob_comb)

    # --- Object Distributions ---
    obj_dist_comb = [str(x) for x in parameters.at[1, 'Value']]  # List of object distribution codes
    print(obj_dist_comb)

    # --- Orbital Regimes ---
    regime_dict = parameters.at[2, 'Value']
    regime_mask = [bool(regime_dict[key]) for key in regime_dict]
    regimes = ['LEO', 'MEO', 'GEO', 'HEO', 'ALL', 'LMO', 'LGO', 'LHO', 'MGO', 'MHO', 'GHO', 'LMG', 'LMH', 'LGH', 'MGH']
    regime_comb = np.array(regimes)[regime_mask]
    print(regime_comb)

    # --- Event Types ---
    event_dict = parameters.at[3, 'Value']
    event_mask = [bool(event_dict[key]) for key in event_dict]
    events = ['MB', 'BU', 'LL', 'NE']
    event_comb = np.array(events)[event_mask]
    print(event_comb)

    # --- Sensor Types ---
    sensor_dict = parameters.at[4, 'Value']
    sensor_mask = [bool(sensor_dict[key]) for key in sensor_dict]
    sensor_types = ['OP', 'RA', 'RF', 'FU', 'OR', 'RO', 'RR']
    sensor_comb = np.array(sensor_types)[sensor_mask]
    print(sensor_comb)

    # --- Percent of Orbit Tracked ---
    percent_dict = parameters.at[5, 'Value']
    percent_mask = [bool(percent_dict[key]) for key in percent_dict]
    percents = ['A', 'S', 'N']  # All, Some, Low
    percent_comb = np.array(percents)[percent_mask]
    print(percent_comb)

    # --- Track Gap Periods ---
    period_dict = parameters.at[6, 'Value']
    period_mask = [bool(period_dict[key]) for key in period_dict]
    periods = ['A', 'S', 'N']
    period_comb = np.array(periods)[period_mask]
    print(period_comb)

    # --- Observation Counts ---
    obs_count_dict = parameters.at[7, 'Value']
    obs_count_mask = [bool(obs_count_dict[key]) for key in obs_count_dict]
    obs_counts = ['A', 'S', 'N']
    obs_count_comb = np.array(obs_counts)[obs_count_mask]
    print(obs_count_comb)

    # --- Total Object Counts ---
    total_obj_count_dict = parameters.at[8, 'Value']
    total_obj_count_mask = [bool(total_obj_count_dict[key]) for key in total_obj_count_dict]
    total_obj_counts = ['H', 'S', 'L']
    total_obj_count_comb = np.array(total_obj_counts)[total_obj_count_mask]
    print(total_obj_count_comb)

    # --- Time Windows ---
    time_comb = [str(x) for x in parameters.at[9, 'Value']]  # List of time window strings
    print(time_comb)

    # --- Combine All Selected Parameters ---
    dataset_codes = []
    for combo in product(targ_ob_comb, obj_dist_comb, regime_comb, event_comb, sensor_comb,
                         percent_comb, period_comb, obs_count_comb, total_obj_count_comb, time_comb):
        code = ''.join(str(part) for part in combo)  # Concatenate parts into a single code string
        dataset_codes.append(DatasetCode(code))  # Wrap in DatasetCode object

    return dataset_codes  # Return the full list of generated dataset codes

def setRecycler(desired_sets, existing_sets):
        
    

    #create dataset code class object
    
        
        #turn list into DatasetCode objects
    # existing_sets = [DatasetCode(set) for set in existing_sets]
    #return redundant sets and remove redundancies from desired sets
    redundant_sets = [x for x in desired_sets if x in existing_sets]
    desired_sets = [x for x in desired_sets if x not in redundant_sets]
        
    #return dict of downsampleable sets
    recyclable_sets = dict()
    for dscode in desired_sets:
        for existing_dscode in existing_sets:
            if dscode < existing_dscode:
                print(f"Dataset Code {dscode} can be recycled from {existing_dscode}")
                recyclable_sets[dscode] = existing_dscode
                break

    desired_DatasetCodes = [code for code in desired_sets if code not in recyclable_sets]

    #return list of remaining sets that cannot be downsampled internally, socre by whar can be recycled from the most other sets
    unrecyclable_sets = []
    scores_dict = dict()
    for dscode in desired_DatasetCodes:
        score = -1
        for dscode2 in desired_DatasetCodes:
            if dscode < dscode2:
                score += 1
        scores_dict[dscode] = score

    #sort by lowest score
    scores_sorted = np.array(sorted(scores_dict.items(), key=lambda x: x[1]))

    #unrecyclable sets are those with score of zero
    unrecyclable_sets = []
    for s in np.unique(scores_sorted[:,1]):
        
        unrecyclable_sets.extend(scores_sorted[scores_sorted[:,1]==s,0])
        desired_DatasetCodes = [code for code in desired_DatasetCodes if code not in unrecyclable_sets]

        #check if all others can be generated if unrecyclable set can be
        internal_recyclable_sets = dict()
        for dscode in desired_DatasetCodes:
            for unrec_dscode in unrecyclable_sets:
                if dscode < unrec_dscode:
                    print(f"Dataset Code {dscode} can be recycled from {unrec_dscode} internally")
                    internal_recyclable_sets[dscode] = unrec_dscode
                    break
        
        if len(internal_recyclable_sets) == len(desired_DatasetCodes):
            break

    #return redundant sets, internally recyclable sets, and unrecyclable sets, also save for debugging
    return(redundant_sets, internal_recyclable_sets, unrecyclable_sets,recyclable_sets)

if __name__ == '__main__':
    datasetCodeDataframe = createDatasetCodeGUI()
    datasetCodes = codeGenerator(datasetCodeDataframe)
    print(datasetCodes)

