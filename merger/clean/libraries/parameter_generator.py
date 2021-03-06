import numpy as np
import astropy.units as units
import astropy.constants as constants
import numba as nb
import logging

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
	return p_xvt(x, vt, mass)*f_vt(vt)

@nb.njit
def delta_u_from_x(x, mass):
	return r(mass)*np.sqrt((1-x)/x)

@nb.njit
def tE_from_xvt(x, vt, mass):
	return r_0 * np.sqrt(mass*x*(1-x)) / (vt*kms_to_pcd)

@nb.njit
def randomizer_gauss(x, vt):
	return np.array([np.random.normal(loc=x, scale=0.1), np.random.normal(loc=vt, scale=300)])

def metropolis_hastings(func, g, nb_samples, start, **kwargs):
	"""
	Metropolis-Hasting algorithm to pick random value following the joint probability distribution func

	Parameters
	----------
	func : function
		 Joint probability distribution
	g : function
		Randomizer. Choose it wisely to converge quickly and have a smooth distribution
	nb_samples : int
		Number of points to return. Need to be large so that the output distribution is smooth
	start : array-like
		Initial point
	kwargs :
		arguments to pass to *func*


	Returns
	-------
	np.array
		Array containing all the points
	"""
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
		if current_x[0]>0 and current_x[0]<1:
			samples.append(current_x)
	print(accepted, accepted/nb_samples)
	return np.array(samples)

class Microlensing_generator():
	"""
	Class to generate microlensing paramters

	Parameters
	----------
	xvt_file : str
		File containing x - v_T pairs generated through the Hasting-Metropolis algorithm
	seed : int
		Seed used for numpy.seed
	tmin : int
		test
	tmax : int
		Defines the limits of t_0
	"""
	def __init__(self, xvt_file=None, seed=None, tmin=48928., tmax=52697., u_max=2., mass=30.,  max_blend=0.7, enable_blending=False):
		self.seed = seed
		self.xvt_file = xvt_file

		self.tmin = tmin
		self.tmax = tmax
		self.u_max = u_max
		self.max_blend = max_blend
		self.blending = enable_blending
		self.blend_pdf = None
		self.generate_mass = False
		self.mass = mass

		if self.seed:
			np.random.seed(self.seed)

		if self.xvt_file:
			try:
				self.xvts = np.load(self.xvt_file)
			except FileNotFoundError:
				logging.error(f"xvt file not found : {self.xvt_file}")
		else:
			logging.info("Generating 10.000.000 x-vt pairs... ")
			self.xvts = metropolis_hastings(pdf_xvt, randomizer_gauss, 10000000, np.array([0.5, 100]), mass=self.mass)


	def generate_parameters(self, seed):
		"""
		Generate a set of microlensing parameters, including parallax and blending

		Parameters
		----------
		seed : str
			Seed used for parameter generation (EROS id)
		Returns
		-------
		dict
			Dictionnary containing the parameters set
		"""
		if seed:
			seed = int(seed.replace('lm0', '').replace('k', '0').replace('l', '1').replace('m', '2').replace('n', '3'))
			np.random.seed(seed)
		if self.generate_mass:
			mass = np.random.uniform(0, 200)
		else:
			mass = self.mass
		u0 = np.random.uniform(0, self.u_max)
		x, vt = self.xvts[np.random.randint(0, self.xvts.shape[0])]
		vt *= np.random.choice([-1., 1.])
		delta_u = delta_u_from_x(x, mass=mass)
		tE = tE_from_xvt(x, vt, mass=mass)
		t0 = np.random.uniform(self.tmin - tE / 2., self.tmax + tE / 2.)
		blend_factors = {}
		for key in COLOR_FILTERS.keys():
			if self.blending:
				blend_factors[key] = np.random.uniform(0, self.max_blend)
			else:
				blend_factors[key] = 0
		theta = np.random.uniform(0, 2 * np.pi)
		params = {
			'blend': blend_factors,
			'u0': u0,
			't0': t0,
			'tE': tE,
			'delta_u': delta_u,
			'theta': theta,
			'mass': mass,
			'x': x,
			'vt': vt,
		}
		return params