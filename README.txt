clean/	
directory with theorically functional scripts
	libraries/
		"merger_library" module for loading MACO and EROS data into pandas df
		"iminuit_fitter" mdule for fitting lightcurves, writing a new file with evaluated parameters
	"merger" load and merge EROS and MACHO data with association file and save to pandas pickle, and fit


old/
sort of working directory
	"merger_library" contains functions to load data from original MACHO and EROS database
	"merger_pandas2" is used to merge data from MACHO and EROS
	"simulator" add simulated events to a part of the lightcurves
	"iminuit_fitter" loop through a file containing merged lc and estimate parameters for a microlensing event
	"sigma-mag-histo" lopp through merged lc and save a dataframe containing their mean magnitude and standard deviation for use in creation of simulated eventss

utils/
other useful scripts
	"toy_simulator" interactive microlensing simulator
	"en_masse_fit_visualizer" visualize lightcurves with corresponding fitted microlensing event (WIP)
	"physical_params_generator_testing" testing ppf generator of x and v_T

python_associator/
code to fuse EROS and MACHO astrometry using quads
	"new_nnd" ...