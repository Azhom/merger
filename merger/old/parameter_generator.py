import numpy as np
import astropy.units as units
import astropy.constants as constants

import matplotlib.pyplot as plt
import numba as nb

from scipy.integrate import quad

COLOR_FILTERS = {
	'red_E':{'mag':'red_E', 'err': 'rederr_E'},
	'red_M':{'mag':'red_M', 'err': 'rederr_M'},
	'blue_E':{'mag':'blue_E', 'err': 'blueerr_E'},
	'blue_M':{'mag':'blue_M', 'err': 'blueerr_M'}
}

a=5000
rho_0=0.0079
d_sol = 8500
l_lmc, b_lmc = 280.4652/180.*np.pi, -32.8884/180.*np.pi
r_lmc = 55000
r_earth = (150*1e6*units.km).to(units.pc).value
t_obs = ((52697 - 48928) << units.d).to(units.s).value

pc_to_km = (units.pc.to(units.km))
kms_to_pcd = (units.km/units.s).to(units.pc/units.d)

cosb_lmc = np.cos(b_lmc)
cosl_lmc = np.cos(l_lmc)
A = d_sol ** 2 + a ** 2
B = d_sol * cosb_lmc * cosl_lmc
r_0 = np.sqrt(4*constants.G/(constants.c**2)*r_lmc*units.pc).decompose([units.Msun, units.pc]).value

@nb.njit
def r(mass):
	R_0 = r_0*np.sqrt(mass)
	return r_earth/R_0

@nb.njit
def R_E(x, mass):
	return r_0*np.sqrt(mass*x*(1-x))

@nb.njit
def rho_halo(x):
	return rho_0*A/((x*r_lmc)**2-2*x*r_lmc*B+A)

@nb.njit
def f_vt(v_T, v0=220):
	return (2*v_T/(v0**2))*np.exp(-v_T**2/(v0**2))

@nb.njit
def p_xvt(x, v_T, mass):
	return rho_halo(x)/mass*r_lmc*(2*r_0*np.sqrt(mass*x*(1-x))*t_obs*v_T)

@nb.njit
def pdf_xvt(x, vt, mass):
	if x<0 or x>1 or vt<0:
		return 0
	return p_xvt(x, vt, mass)*rho_halo(x)/mass*x*x*f_vt(vt)

@nb.njit
def x_from_delta_u(delta_u, mass):
	return r(mass)**2/(r(mass)**2+delta_u**2)

@nb.njit
def v_T_from_tEdu(delta_u, t_E, mass):
	R_0 = r_0*np.sqrt(mass)*pc_to_km
	ri = r(mass)
	return R_0/(t_E*86400) * ri*delta_u/(ri**2+delta_u**2)

@nb.njit
def delta_u_from_x(x, mass):
	return r(mass)*np.sqrt((1-x)/x)

@nb.njit
def tE_from_xvt(x, vt, mass):
	return r_0 * np.sqrt(mass*x*(1-x)) / (vt*kms_to_pcd)

@nb.njit
def jacobian(delta_u, t_E, mass):
	R_0 = r_0*np.sqrt(mass)*pc_to_km
	ri = r(mass)
	h1 = -2*ri**2*delta_u/(ri**2+delta_u**2)**2
	sqrth2 = ri*delta_u/(ri**2+delta_u**2)
	return -h1*sqrth2*R_0/(t_E*86400)**2


def pdf_tEdu(t_E, delta_u, mass):
	x = x_from_delta_u(delta_u, mass)
	vt = v_T_from_tEdu(delta_u, t_E, mass)
	return p_xvt(x, vt, mass)*rho_halo(x)/mass*x*x*f_vt(vt)*np.abs(jacobian(delta_u, t_E, mass))

@nb.njit
def randomizer(x, vt):
	return np.array([np.random.triangular(x-0.1, x, x+0.1), np.random.triangular(vt-100, vt, vt + 100)])

@nb.njit
def randomizer_gauss(x, vt):
	return np.array([np.random.normal(loc=x, scale=0.1), np.random.normal(loc=vt, scale=300)])

def metropolis_hastings(func, g, nb_samples, start, kwargs={}):
	samples = []
	current_x = start
	accepted=0
	while nb_samples > len(samples):
		proposed_x = g(*current_x)
		tmp = func(*current_x, **kwargs)
		if tmp!=0:
			threshold = min(1., func(*proposed_x, **kwargs) / tmp)
		else:
			threshold = 1
		if np.random.uniform() < threshold:
			current_x = proposed_x
			accepted+=1
		samples.append(current_x)
	print(accepted, accepted/nb_samples)
	return np.array(samples)

def generate_parameters(mass, seed=None, blending=False, parallax=False):
	"""
	Parameters to generate : u0, tE, 𝛅u, theta, t0, blends factors
	:param mass:
	:param seed:
	:param blending:
	:return:
	"""
	tmin = 48928
	tmax = 52697
	u_max = 1.
	max_blend=0.7

	if seed:
		seed = int(seed.replace('lm0', '').replace('k', '0').replace('l', '1').replace('m', '2').replace('n', '3'))
		np.random.seed(seed)

	u0 = np.random.uniform(0,u_max)
	s = np.load('xvt_samples.npy')
	x , vt = np.random.choice(s, 1)
	delta_u = delta_u_from_x(x, mass=mass)
	tE = tE_from_xvt(x, vt, mass=mass)
	t0 = np.random.uniform(tmin - tE / 2., tmax + tE / 2.)
	blend_factors = {}
	for key in COLOR_FILTERS.keys():
		if blending:
			blend_factors[key] = np.random.uniform(0, max_blend)
		else:
			blend_factors[key] = 0
	theta = np.random.uniform(0, 2 * np.pi)
	params = {
		'blend':blend_factors,
		'u0':u0,
		't0':t0,
		'tE':tE,
		'delta_u':delta_u,
		'theta':theta,
	}
	return params