#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Script to load lightcuvres from EROS and MACHO database and save the merged result

Load lightcurves from EROS and MACHO databases, load association file, that should be already computed, merge the lightcurves and save it in a pandas pickle file
"""

import argparse
import numpy as np
import logging
import os

from merger.clean.libraries import merger_library, iminuit_fitter

def dir_path_check(dirpath):
	if not os.path.isdir(dirpath):
		raise Exception("This directory doesn't exist : "+dirpath)


if __name__ == '__main__':
	parser = argparse.ArgumentParser()
	parser.add_argument('--EROS-field', '-fE', type=str, required=True, help="something like lmXXX")
	parser.add_argument('--EROS-CCD', '-ccdE', type=int, default=None, choices=np.arange(8), required=False)
	parser.add_argument('--MACHO-field', '-fM', type=int, required=True)
	parser.add_argument('--output-directory', '-odir', type=str, default=merger_library.OUTPUT_DIR_PATH)
	parser.add_argument('-fit', action='store_true')
	parser.add_argument('--EROS-path', '-pE', type=str, default="/Volumes/DisqueSauvegarde/EROS/lightcurves/lm/", help="'irods' for laoding from CC-IN2P3 irods")
	parser.add_argument('--MACHO-path', '-pM', type=str, default="/Volumes/DisqueSauvegarde/MACHO/lightcurves/", help="'url' for loading from NCI")
	parser.add_argument('--correspondance-path', '-pC', type=str, default="/Users/tristanblaineau/")
	parser.add_argument('--quart', type=str, default="", choices=["k", "l", "m", "n"])
	parser.add_argument('--verbose', '-v', action='store_true', help='Debug logging level')
	parser.add_argument('--MACHO-tile', '-tM', type=int)

	#Retrieve arguments
	args = parser.parse_args()

	MACHO_field = args.MACHO_field
	MACHO_tile = args.MACHO_tile
	EROS_field = args.EROS_field
	EROS_CCD = args.EROS_CCD
	fit = args.fit
	EROS_files_path = args.EROS_path
	MACHO_files_path = args.MACHO_path
	correspondance_files_path = args.correspondance_path
	output_directory = args.output_directory
	quart = args.quart
	verbose = args.verbose

	if verbose:
		logging.basicConfig(level=logging.INFO)

	if (quart != "") and EROS_CCD is None:
		logging.warning("Quart value will not be taken into account as the whole field will be scanned.")

	#Check if input paths exist
	dir_path_check(output_directory)
	dir_path_check(correspondance_files_path)
	if not MACHO_files_path=="url":
		dir_path_check(MACHO_files_path)
	if not EROS_files_path=='irods':
		dir_path_check(EROS_files_path)

	print(fit)

	#Main
	if not MACHO_tile:
		if not EROS_CCD is None:
			eros_ccd = "lm"+EROS_field+str(EROS_CCD)
			merged = merger_library.merger_eros_first(output_directory, MACHO_field, eros_ccd, EROS_files_path, correspondance_files_path, MACHO_files_path, quart=quart, save=False)
			if fit:
				iminuit_fitter.fit_all(merged=merged, filename=str(MACHO_field)+"_"+str(eros_ccd)+quart+".pkl", input_dir_path=output_directory, output_dir_path=output_directory)
		else:
			for i in range(0,8):
				eros_ccd = "lm"+EROS_field+str(i)
				merged = merger_library.merger_eros_first(output_directory, MACHO_field, eros_ccd, EROS_files_path, correspondance_files_path, MACHO_files_path, save=False)
				if fit:
					iminuit_fitter.fit_all(merged=merged, filename= str(MACHO_field)+"_"+str(eros_ccd)+".pkl", input_dir_path=output_directory, output_dir_path=output_directory)
	else:
		merged = merger_library.merger_macho_first(output_directory, MACHO_field, EROS_files_path, correspondance_files_path, MACHO_files_path, save=False, MACHO_tile=MACHO_tile)
		if fit:
			iminuit_fitter.fit_all(merged=merged, filename=str(MACHO_field) + "_" + str(MACHO_tile) + ".pkl", input_dir_path=output_directory, output_dir_path=output_directory)