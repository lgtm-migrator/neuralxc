# Code adapted from https://github.com/BachiLi/redner/blob/master/pyredner/utils.py #
# Spherical harmonics utility functions
import numpy as np
import math
from numba import jit

# @jit(nopython=True)
def associated_legendre_polynomial(l, m, x, pmm, pll):
    if m > 0:
        somx2 = np.sqrt((1 - x) * (1 + x))
        fact = 1.0
        for i in range(1, m + 1):
            pmm = pmm * (-fact) * somx2
            fact += 2.0
    if l == m:
        return pmm
    pmmp1 = x * (2.0 * m + 1.0) * pmm
    if l == m + 1:
        return pmmp1
    for ll in range(m + 2, l + 1):
        pll = ((2.0 * ll - 1.0) * x * pmmp1 - (ll + m - 1.0) * pmm) / (ll - m)
        pmm = pmmp1
        pmmp1 = pll
    return pll

# @jit
def SH_renormalization(l, m):
    return math.sqrt((2.0 * l + 1.0) * math.factorial(l - m) / \
        (4 * math.pi * math.factorial(l + m)))

# @jit
def SH(l, m, theta, phi):
    pmm = np.ones_like(theta)
    pll = np.zeros_like(theta)
    if m == 0:
        return SH_renormalization(l, m) * associated_legendre_polynomial(l, m, np.cos(theta), pmm, pll)
    elif m > 0:
        return math.sqrt(2.0) * SH_renormalization(l, m) * \
            np.cos(m * phi) * associated_legendre_polynomial(l, m, np.cos(theta), pmm, pll)
    else:
        return math.sqrt(2.0) * SH_renormalization(l, -m) * \
            np.sin(-m * phi) * associated_legendre_polynomial(l, -m, np.cos(theta), pmm, pll)