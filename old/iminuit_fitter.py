import pandas as pd
import numpy as np
from iminuit import Minuit
import time
import matplotlib.pyplot as plt

GLOBAL_COUNTER=0

def microlensing_event(t, u0, t0, tE, mag1):
	u = np.sqrt(u0*u0 + ((t-t0)**2)/tE/tE)
	return -2.5*np.log10((u**2+2)/(u*np.sqrt(u**2+4)))+mag1 

def parallax(t, mag, u0, t0, tE, delta_u, beta, psi, alpha0):
	phi = 2*np.pi/365.25 * (t-t0) + alpha0
	t1 = u0*u0
	t2 = ((t-t0)/tE)**2
	t3 = delta_u**2 * (np.cos(phi)**2 + (np.sin(phi) * np.cos(beta))**2)
	t4 = -delta_u * (t-t0)/tE * (np.cos(psi) * np.cos(phi) + np.cos(beta) * np.sin(psi) * np.sin(phi))
	t5 = u0 * delta_u * (np.sin(psi) * np.cos(phi) - np.cos(psi) * np.sin(phi) * np.cos(beta))
	u = np.sqrt(t1+t2+t3+t4+t5)
	return (u**2+2)/(u*np.sqrt(u**2+4))

def parallax_microlensing_event(t, mag, u0, t0, tE, delta_u, beta, psi, alpha0):
	return mag - 2.5*np.log10(parallax(t, mag, u0, t0, tE, delta_u, beta, psi, alpha0))

def fit_ml(subdf):

	#sélection des données, pas plus de 10% du temps de calcul en moyenne (0.01s vs 0.1s)
	#le fit peut durer jusqu'à 0.7s ou aussi rapide que 0.04s (en général False)
	
	subdf.drop(subdf.red_E.nsmallest(5).index, inplace=True)
	subdf.drop(subdf.blue_E.nsmallest(5).index, inplace=True)
	subdf.drop(subdf.red_M.nsmallest(5).index, inplace=True)
	subdf.drop(subdf.blue_M.nsmallest(5).index, inplace=True)

	maskRE = subdf.red_E.notnull() & subdf.rederr_E.notnull()
	maskBE = subdf.blue_E.notnull() & subdf.blueerr_E.notnull()
	maskRM = subdf.red_M.notnull() & subdf.rederr_M.notnull()
	maskBM = subdf.blue_M.notnull() & subdf.blueerr_M.notnull()

	errRE = subdf[maskRE].rederr_E.values
	errBE = subdf[maskBE].blueerr_E.values
	errRM = subdf[maskRM].rederr_M.values
	errBM = subdf[maskBM].blueerr_M.values

	min_err = 0.0
	cre = (errRE>min_err) & (errRE<9.999)
	cbe = (errBE>min_err) & (errBE<9.999)
	crm = (errRM>min_err) & (errRM<9.999)
	cbm = (errBM>min_err) & (errBM<9.999)

	# magRE = subdf[maskRE][cre].ampli_red_E.values
	# magBE = subdf[maskBE][cbe].ampli_blue_E.values
	# magRM = subdf[maskRM][crm].ampli_red_M.values
	# magBM = subdf[maskBM][cbm].ampli_blue_M.values

	magRE = subdf[maskRE][cre].red_E.values
	magBE = subdf[maskBE][cbe].blue_E.values
	magRM = subdf[maskRM][crm].red_M.values
	magBM = subdf[maskBM][cbm].blue_M.values

	timeRE = subdf[maskRE][cre].time.values
	timeBE = subdf[maskBE][cbe].time.values
	timeRM = subdf[maskRM][crm].time.values
	timeBM = subdf[maskBM][cbm].time.values

	errRE = errRE[cre]
	errBE = errBE[cbe]
	errRM = errRM[crm]
	errBM = errBM[cbm]

	def least_squares_microlens(u0, t0, tE, magStarRE, magStarBE, magStarRM, magStarBM):
		lsq1 = np.sum(((magRE - microlensing_event(timeRE, u0, t0, tE, magStarRE))/ errRE)**2)
		lsq2 = np.sum(((magBE - microlensing_event(timeBE, u0, t0, tE, magStarBE))/ errBE)**2)
		lsq3 = np.sum(((magRM - microlensing_event(timeRM, u0, t0, tE, magStarRM))/ errRM)**2)
		lsq4 = np.sum(((magBM - microlensing_event(timeBM, u0, t0, tE, magStarBM))/ errBM)**2)
		return lsq1+lsq2+lsq3+lsq4

	def least_squares_flat(f_magStarRE, f_magStarBE, f_magStarRM, f_magStarBM):
		return np.sum(((magRE - f_magStarRE)/errRE)**2) + np.sum(((magRM - f_magStarRM)/errRM)**2) + np.sum(((magBE - f_magStarBE)/errBE)**2) + np.sum(((magBM - f_magStarBM)/errBM)**2)

	# def ls_parallax(params):
	# 	u0, t0, tE, magStarRE, magStarBE, magStarRM, magStarBM, delta_u, beta, psi, alpha0 = params
	# 	lsq1 = np.sum(((magRE - parallax_microlensing_event(timeRE, magStarRE, u0, t0, tE, delta_u, beta, psi, alpha0))/ errRE)**2)
	# 	lsq2 = np.sum(((magBE - parallax_microlensing_event(timeBE, magStarBE, u0, t0, tE, delta_u, beta, psi, alpha0))/ errBE)**2)
	# 	lsq3 = np.sum(((magRM - parallax_microlensing_event(timeRM, magStarRM, u0, t0, tE, delta_u, beta, psi, alpha0))/ errRM)**2)
	# 	lsq4 = np.sum(((magBM - parallax_microlensing_event(timeBM, magStarBM, u0, t0, tE, delta_u, beta, psi, alpha0))/ errBM)**2)
	# 	return lsq1+lsq2+lsq3+lsq4

	m_micro = Minuit(least_squares_microlens, 
		u0=0.5, 
		t0=50000, 
		tE=1000, 
		magStarRE=20, 
		magStarBE=20, 
		magStarRM=-4, 
		magStarBM=-4, 
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

	"""
	params_names = ["u0", "t0", "tE", "magStarRE", "magStarBE", "magStarRM", "magStarBM", "delta_u", "beta", "psi", "alpha0"]
	params_init = {
		"u0":0.5, 
		"t0":50000, 
		"tE":1000, 
		"magStarRE":20, 
		"magStarBE":20, 
		"magStarRM":-4, 
		"magStarBM":-4, 
		"delta_u":0,
		"beta":0,
		"psi":0,
		"error_u0":0.1, 
		"error_t0":5000, 
		"error_tE":100, 
		"error_magStarRE":2, 
		"error_magStarBE":2., 
		"error_magStarRM":2., 
		"error_magStarBM":2., 
		"limit_u0":(0,2), 
		"limit_tE":(300, 10000),
		"limit_t0":(40000, 60000),
		"limit_beta":(0,np.pi),
		"limit_delta_u":(0, None),
		"limit_psi":(0, 2*np.pi),
		"limit_alpha0":(0, 2*np.pi)
	}
	m_micro = Minuit(ls_parallax, forced_parameters=params_names, print_level=1, errordef=1, use_array_call=True, **params_init)
	"""
	m_flat = Minuit(least_squares_flat, 
		f_magStarRE=20, 
		f_magStarBE=20, 
		f_magStarRM=-4, 
		f_magStarBM=-4, 
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
	print(str(GLOBAL_COUNTER)+" : "+subdf.id_M.iloc[0]+" "+str(m_micro.get_fmin().is_valid)+"     ", end='\r')
	return pd.Series(

		m_micro.values.values()+[m_micro.get_fmin().is_valid, m_micro.fval] 
		+ 
		m_flat.values.values()+[m_flat.get_fmin().is_valid, m_flat.fval]
		+[len(errRE)+len(errBE)+len(errRM)+len(errBM)], 

		index=m_micro.values.keys()+['micro_valid', 'micro_fval']
		+
		m_flat.values.keys()+['flat_valid', 'flat_fval']
		+["dof"]

		)

WORKING_DIR_PATH = "/Volumes/DisqueSauvegarde/working_dir/"
merged = pd.read_pickle(WORKING_DIR_PATH+'8_lm0213.pkl')
merged.replace(to_replace=[99.999,-99.], value=np.nan, inplace=True)
merged.dropna(axis=0, how='all', subset=['blue_E', 'red_E', 'blue_M', 'red_M'], inplace=True)
print(merged)

print("FILES LOADED")

start = time.time()
res= merged.groupby("id_E").apply(fit_ml)
end= time.time()
res.to_pickle(WORKING_DIR_PATH+'res_8_lm0213_cut5.pkl')
print(str(end-start)+" seconds elapsed.")
print(str(len(res))+" stars fitted.")