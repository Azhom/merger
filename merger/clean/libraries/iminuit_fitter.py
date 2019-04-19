import time
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from iminuit import Minuit

GLOBAL_COUNTER = 0


def microlensing_event(t, u0, t0, tE, mag1):
	u = np.sqrt(u0*u0 + ((t-t0)**2)/tE/tE)
	return -2.5*np.log10((u**2+2)/(u*np.sqrt(u**2+4)))+mag1 


def fit_ml(subdf, cut5=False):
	"""Fit on one star
	
	[description]
	
	Arguments:
		subdf {dataframe} -- Lightcurves data
	
	Keyword Arguments:
		cut5 {bool} -- If True, clean aberrant points using distance from median of 5 points (default: {False})
	
	Returns:
		series -- Contains parameters for the microlensing and flat curve fits, their chi2, informations on the fitter (fmin) and dof.
	"""

	#sélection des données, pas plus de 10% du temps de calcul en moyenne (0.01s vs 0.1s)
	#le fit peut durer jusqu'à 0.7s ou aussi rapide que 0.04s (en général False)

	maskRE = subdf.red_E.notnull() & subdf.rederr_E.notnull()
	maskBE = subdf.blue_E.notnull() & subdf.blueerr_E.notnull()
	maskRM = subdf.red_M.notnull() & subdf.rederr_M.notnull()
	maskBM = subdf.blue_M.notnull() & subdf.blueerr_M.notnull()

	errRE = subdf[maskRE].rederr_E
	errBE = subdf[maskBE].blueerr_E
	errRM = subdf[maskRM].rederr_M
	errBM = subdf[maskBM].blueerr_M

	min_err = 0.01
	cre = errRE.between(min_err,9.999)
	cbe = errBE.between(min_err,9.999)
	crm = errRM.between(min_err,9.999)
	cbm = errBM.between(min_err,9.999)

	# magRE = subdf[maskRE][cre].ampli_red_E
	# magBE = subdf[maskBE][cbe].ampli_blue_E
	# magRM = subdf[maskRM][crm].ampli_red_M
	# magBM = subdf[maskBM][cbm].ampli_blue_M

	magRE = subdf[maskRE][cre].red_E
	magBE = subdf[maskBE][cbe].blue_E
	magRM = subdf[maskRM][crm].red_M
	magBM = subdf[maskBM][cbm].blue_M

	errRE = errRE[cre]
	errBE = errBE[cbe]
	errRM = errRM[crm]
	errBM = errBM[cbm]

	cut5RE = np.abs((magRE.rolling(5, center=True).median()-magRE[2:-2]))/errRE[2:-2]<5
	cut5BE = np.abs((magBE.rolling(5, center=True).median()-magBE[2:-2]))/errBE[2:-2]<5
	cut5RM = np.abs((magRM.rolling(5, center=True).median()-magRM[2:-2]))/errRM[2:-2]<5
	cut5BM = np.abs((magBM.rolling(5, center=True).median()-magBM[2:-2]))/errBM[2:-2]<5

	tolerance_ratio = 0.9
	if cut5 and not ((cut5RE.sum()/len(cut5RE)<tolerance_ratio and cut5BE.sum()/len(cut5BE)<tolerance_ratio) 
		or (cut5BM.sum()/len(cut5BM)<tolerance_ratio and cut5RM.sum()/len(cut5RM)<tolerance_ratio)):
		timeRE = subdf[maskRE][cre][cut5RE].time.values
		timeBE = subdf[maskBE][cbe][cut5BE].time.values
		timeRM = subdf[maskRM][crm][cut5RM].time.values
		timeBM = subdf[maskBM][cbm][cut5BM].time.values

		errRE = errRE[cut5RE].values
		errBE = errBE[cut5BE].values
		errRM = errRM[cut5RM].values
		errBM = errBM[cut5BM].values

		magRE = magRE[cut5RE].values
		magBE = magBE[cut5BE].values
		magRM = magRM[cut5RM].values
		magBM = magBM[cut5BM].values

	else:
		timeRE = subdf[maskRE][cre].time.values
		timeBE = subdf[maskBE][cbe].time.values
		timeRM = subdf[maskRM][crm].time.values
		timeBM = subdf[maskBM][cbm].time.values

		errRE = errRE.values
		errBE = errBE.values
		errRM = errRM.values
		errBM = errBM.values

		magRE = magRE.values
		magBE = magBE.values
		magRM = magRM.values
		magBM = magBM.values

	def least_squares_microlens(u0, t0, tE, magStarRE, magStarBE, magStarRM, magStarBM):
		lsq1 = np.sum(((magRE - microlensing_event(timeRE, u0, t0, tE, magStarRE))/ errRE)**2)
		lsq2 = np.sum(((magBE - microlensing_event(timeBE, u0, t0, tE, magStarBE))/ errBE)**2)
		lsq3 = np.sum(((magRM - microlensing_event(timeRM, u0, t0, tE, magStarRM))/ errRM)**2)
		lsq4 = np.sum(((magBM - microlensing_event(timeBM, u0, t0, tE, magStarBM))/ errBM)**2)
		return lsq1+lsq2+lsq3+lsq4

	def least_squares_flat(f_magStarRE, f_magStarBE, f_magStarRM, f_magStarBM):
		return np.sum(((magRE - f_magStarRE)/errRE)**2) + np.sum(((magRM - f_magStarRM)/errRM)**2) + np.sum(((magBE - f_magStarBE)/errBE)**2) + np.sum(((magBM - f_magStarBM)/errBM)**2)

	m_micro = Minuit(least_squares_microlens, 
		u0=1., 
		t0=50000, 
		tE=500, 
		magStarRE=magRE.mean(), 
		magStarBE=magBE.mean(), 
		magStarRM=magRM.mean(), 
		magStarBM=magBM.mean(), 
		error_u0=0.1, 
		error_t0=5000, 
		error_tE=100, 
		error_magStarRE=2, 
		error_magStarBE=2., 
		error_magStarRM=2., 
		error_magStarBM=2., 
		limit_u0=(0,2), 
		limit_tE=(300, 10000),
		limit_t0=(40000, 60000),#(48927, 52698)
		errordef=1,
		print_level=0)

	m_flat = Minuit(least_squares_flat, 
		f_magStarRE=magRE.mean(), 
		f_magStarBE=magBE.mean(), 
		f_magStarRM=magRM.mean(), 
		f_magStarBM=magBM.mean(), 
		error_f_magStarRE=2, 
		error_f_magStarBE=2., 
		error_f_magStarRM=2., 
		error_f_magStarBM=2., 
		errordef=1,
		print_level=0
		)

	m_micro.migrad()
	m_flat.migrad()
	global GLOBAL_COUNTER
	GLOBAL_COUNTER+=1
	#print(str(GLOBAL_COUNTER)+" : "+subdf.id_M.iloc[0]+" "+str(m_micro.get_fmin().is_valid)+"     ", end='\r')
	return pd.Series(

		m_micro.values.values()+[m_micro.get_fmin(), m_micro.fval]
		+
		m_flat.values.values()+[m_flat.get_fmin(), m_flat.fval]
		+ [len(errRE)+len(errBE)+len(errRM)+len(errBM)],

		index=m_micro.values.keys()+['micro_fmin', 'micro_fval']
		+
		m_flat.values.keys()+['flat_fmin', 'flat_fval']
		+ ["dof"]
		)


WORKING_DIR_PATH = "/Volumes/DisqueSauvegarde/working_dir/"


def fit_all(filename, input_dir_path=WORKING_DIR_PATH, output_dir_path=WORKING_DIR_PATH, time_mask=None):
	"""Fit all curves in filename
   
	[description]
   
	Arguments:
		filename {str} -- Name of the file containing the merged curves.
	"""
	if filename[-4:] != '.pkl':
		filename += '.pkl'
	print("Loading "+filename)
	merged = pd.read_pickle(os.path.join(input_dir_path, filename))
	merged.replace(to_replace=[99.999, -99.], value=np.nan, inplace=True)
	merged.dropna(axis=0, how='all', subset=['blue_E', 'red_E', 'blue_M', 'red_M'], inplace=True)
	if time_mask:
		merged = merged[merged['time'].isin(time_mask)]
	print("FILES LOADED")
	start = time.time()
	res = merged.groupby("id_E").apply(fit_ml)
	end = time.time()
	res.to_pickle(os.path.join(output_dir_path, 'res_'+filename))
	print(str(end-start)+" seconds elapsed.")
	print(str(len(res))+" stars fitted.")