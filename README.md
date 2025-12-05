NetCDF TimeRemapper for ParaView:
A Python Programmable Filter for ParaView that replaces the original time axis of a NetCDF dataset with custom time values read from an external text file.

ParaView uses a single global timeline. When multiple NetCDF files have the same number of time steps but different time values or units, they cannot be animated in sync.
E.g., one uses “days since 2000-01-01”, another “seconds since 2001-12-31”. Or they use the same units but with shifted (offset) timestamps relative to each other.
 
This tool remaps all datasets to the exact same time values from a user-defined list, enabling simultaneous animation.
It supports BCE dates (negative years).
It also adds a human-readable "current_date" array for easy timestamp display in the 3D viewport.

The example NetCDF files used in this tutorial are courtesy Clemens Schannwell (Max-Planck-Institut für Meteorologie, Hamburg).
Many thanks to Clemens, who answered the community questionnaire I sent out this summer, kindly shared his datasets and processing shell script, so I could understand the real-world scenario that motivated this tool.

A video tutorial that follows the PDF (NetCDF_TimeRemapper_Tutorial.pdf) step-by-step is available on YouTube: 
https://youtu.be/hl2EThO77Ec




