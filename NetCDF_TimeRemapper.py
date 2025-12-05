#
# Code by Felicia Brisc (University of Hamburg)
# NetCDF TimeRemapper for ParaView
# Copyright (c) 2025 Felicia Brisc
# License: BSD 3-Clause (see LICENSE file for details)
#
# If you use this tool in publications or presentations, please cite:
# Felicia Brisc (2025). NetCDF TimeRemapper for ParaView.
# https://github.com/FeliciaBrisc/ParaView_NetCDF_TimeRemapper
#
#
# Modifies the time values of a NetCDF file with values read from an external text file and brings them to the same units.
# This could be for example useful if you have two or more NetCDF file with the same number of time steps, but with different values of the time variable.
# For example, between two data sets might be a difference of 30 minutes, or they might have additionally different time units.
# In such cases, due to the single time line of ParaView, the files cannot be animated simultaneously.
# Bringing all time steps to the same values, will make it possible to visualize their temporal progress simultaneously.
#
# This script will also be useful when handling dates that are BCE. i.e. have a negative value. 
#
# I saved this as a single Python script to have everything in one file.
# However, this file is divided into 3 parts and should not be run as a single script: 
# 1. RequestInformation Script 
# 2. RequestUpdateExtent Script
# 3. Script (aka "RequestData")
# Please copy and paste each of these parts into the box with the corresponding title in the Programmable Filter.
#
# Version 1.0
#
# Developed and tested on ParaView 6.0.1
#
#----------------------------------------------------------------------------------------------------------------------------
#----------------------------------------------------------------------------------------------------------------------------

# 1. RequestInformation Script 
# The "RequestInformation Script" field overrides the "RequestInformation" ParaView/VTK pipeline function, which is called in the 1st pass,
# setting up metadata about the output produced by the filter, before any data is requested (without allocating data yet)

import vtk
import re
import numpy as np

# This file will contain the new custom times in this format: -4000-01-01T00:00:00, each time on a new row
# Modify this path according to the location of your time file
time_file = r"F:\CLEMENS\PARAVIEW_DATETIME_LIST_BCE.txt"

if hasattr(self, "custom_times"):    
    delattr(self, "custom_times")
  
if hasattr(self, "orig_times"):    
    delattr(self, "orig_times")

if not hasattr(self, "custom_times"):
    with open(time_file, "r") as f:
        lines = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    if not lines:
        raise RuntimeError("TXT file empty!")

    # Splits a string like '-4000-01-01T00:00:00' into date and time parts.
    # Returns a tuple (date_part, time_part)
    def parse_date(s):
        str = s.strip()
        if 'T' not in s:
            raise ValueError(f"Invalid format, no 'T' separator: {str!r}")
        
        date_part, time_part = s.split('T', 1)   # split only on 'T'
        if not date_part or not time_part:
            raise ValueError(f"Incomplete date-time string: {s!r} ? date={date_part!r}, time={time_part!r}")
            
        return date_part, time_part

    # Reference: the first date/time listed in the text file (time_file) becomes the reference date/time
    ref_date = np.datetime64(lines[0])
    
    ref_date_str, ref_time_str = parse_date(lines[0])      
    self.new_units = f"seconds since {ref_date_str} {ref_time_str}"

    # Store the time_file lines for later annotation in the '-4000-01-01 00:00:00' format - 
    # modify below if you wish a different format. 
    # We will use the array we create here, self.custom_times_annotation, later in the "Script" field, where we will add it to the output arrays
    # so that it will become an attribute of the data and if desired it can be displayed with the help of an AnnotateAttributeData in the 3D viewport
    custom_times_annotation = []
    for line in lines:
        date, time = parse_date(line)
        custom_times_annotation.append(date+" "+time)
       
    self.custom_times_annotation = custom_times_annotation    
    

    # Compute custom times: seconds since reference (works with BCE as well)
    custom_times = []
    for line in lines:
        current_date = np.datetime64(line)
        delta = current_date - ref_date
        seconds_since_ref = delta.astype('timedelta64[s]').astype(int)
        custom_times.append(float(seconds_since_ref))        

    # Get original times from input (for mapping)
    inInfo = self.GetInputInformation(0, 0)
    ts_key = vtk.vtkStreamingDemandDrivenPipeline.TIME_STEPS()

    
    num_ts = inInfo.Length(ts_key)
    if num_ts != len(custom_times):
        raise ValueError(f"Number of dates in file ({len(custom_times)}) doesn't match time steps in data ({num_ts})!")
    orig_times = [inInfo.Get(ts_key, i) for i in range(num_ts)]

    # Store everything for other passes
    self.custom_times = custom_times
    self.orig_times = orig_times
    self.initialized  = True

# Provide custom times to the pipeline
outInfo = self.GetOutputInformation(0)
#ts_key = vtk.vtkStreamingDemandDrivenPipeline.TIME_STEPS()
tr_key = vtk.vtkStreamingDemandDrivenPipeline.TIME_RANGE()


if outInfo.Has(ts_key):
    outInfo.Remove(ts_key)
if outInfo.Has(tr_key):
    outInfo.Remove(tr_key)

# Append custom times to output
for t in self.custom_times:
    outInfo.Append(ts_key, t)

# Set up the custom times range
if self.custom_times:
    outInfo.Set(tr_key, [self.custom_times[0], self.custom_times[-1]], 2)
    

#----------------------------------------------------------------------------------------------------------------------------
#----------------------------------------------------------------------------------------------------------------------------

# 2. RequestUpdateExtent Script
# The "RequestUpdateExtent Script" field overrides the "RequestUpdateExtent" function of the ParaView/VTK pipeline, which is called in the second pass, after RequestInformation 
# Manages/modifies the update extent/time that will be requested from the upstream inputs based on what the filter is asking downstream for on the output

# Get requested custom time
upd_key = vtk.vtkStreamingDemandDrivenPipeline.UPDATE_TIME_STEP()
requested_time = self.GetOutputInformation(0).Get(upd_key)

# Map to original time index
if requested_time is not None:
    try:
        idx = self.custom_times.index(requested_time)
    except ValueError:
        idx = 0  # fallback to first
else:
    idx = 0
  

# Request the corresponding original time from upstream
inInfo = self.GetInputInformation(0, 0)
if inInfo.Has(upd_key):
    inInfo.Remove(upd_key)
inInfo.Set(upd_key, self.orig_times[idx])

self.current_requested_custom_time = self.GetOutputInformation(0).Get(vtk.vtkStreamingDemandDrivenPipeline.UPDATE_TIME_STEP())


#----------------------------------------------------------------------------------------------------------------------------
#----------------------------------------------------------------------------------------------------------------------------

# 3.Script (aka "RequestData")
# The "Script" field overrides the "RequestData" ParaView/VTK pipeline function, which is called for the 
# initial data loading (ie. loading the 1st time step) and also whenever advancing the timesteps
# Allocates outputs data objects and fills them with data

# Use self.GetInputDataObject(0, 0) for raw VTK input
inputData = self.GetInputDataObject(0, 0)

# This copies everything (variables included) to the pipeline output
output.ShallowCopy(inputData)  

# Fix the time:units attribute
fieldData = output.GetFieldData()

arrays_to_remove = []
for i in range(fieldData.GetNumberOfArrays()):
    name = fieldData.GetArrayName(i)
    if name is not None and ("time" in name.lower() and "units" in name.lower()):
        arrays_to_remove.append(name)

for name in arrays_to_remove:
    fieldData.RemoveArray(name)

# Add new units to the output arrays
# - this will show up in the "Properties" tab, under the Data Arrays list
str_array = vtk.vtkStringArray()
str_array.SetName("time_units")
str_array.SetNumberOfValues(1)
str_array.SetValue(0, self.new_units)
fieldData.AddArray(str_array)
             

# Use the value we saved in RequestUpdateExtent 
if hasattr(self, "current_requested_custom_time"):
    current_custom_time = self.current_requested_custom_time
else:
    # fallback for the first frame
    current_custom_time = self.custom_times[0]   

# Find index
try:
    idx = self.custom_times.index(current_custom_time)
except ValueError:
    idx = 0

# Add the array with the date/time read from the text file (ie. self.custom_times_annotation) as the "current date" array to the output arrays 
# - this will show up as an attribute in the "Properties" tab,under the Data Arrays list
# This will also make it possible to apply an AnnotateAttributeData filter to our Programmable Filter,
# so that the date/time will be displayed in the 3D viewport corresponding to the current time step
date_array = vtk.vtkStringArray()
date_array.SetName("current_date")
#We created in RequestInformation the self.custom_times_annotation list with dates in the '-4000-01-01 00:00:00' format
date_array.InsertNextValue(self.custom_times_annotation[idx])
output.GetFieldData().AddArray(date_array)

