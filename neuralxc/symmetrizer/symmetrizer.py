from abc import ABC, abstractmethod
from sklearn.base import TransformerMixin
from sklearn.base import BaseEstimator
from ..doc_inherit import doc_inherit
from sympy.physics.quantum.cg import CG
from sympy import N
import numpy as np

class BaseSymmetrizer(ABC):

    def __init__(self):
        pass

    @abstractmethod
    def get_symmetrized(self, C):
        """
        Returns a symmetrized version of the descriptors c (from DensityProjector)

        Parameters
        ----------------
        C , dict of numpy.ndarrays or list of dict of numpy.ndarrays
        	Electronic descriptors

        Returns
        ------------
        D, dict of numpy.ndarrays
        	Symmetrized descriptors
        """
        pass

    @abstractmethod
    def get_gradient(self, dEdD):
        """Uses chain rule to obtain dE/dC from dE/dD (unsymmetrized from symmetrized)

        Parameters
        ------------------
        dEdD : dict of np.ndarrays or list of dict of np.ndarrays
        	dE/dD

        Returns
        -------------
        dEdc: dict of np.ndarrays
        """
        pass

class Symmetrizer(BaseSymmetrizer, BaseEstimator, TransformerMixin):

    def __init__(self, symmetrize_instructions):
        """ Symmetrizer
        Parameters
        ----------
        symmetrize_instructions: dict
            Attributes needed to symmetrize input (such as angular momentum etc.)
        """
        self._attrs = symmetrize_instructions
        self._cgs = 0
        pass

    def get_params(self, *args, **kwargs):
        return {'symmetrize_instructions': self._attrs}

    def fit(self, X=None, y=None):
        return self

    def transform(self, X, y = None):
        # If used in ML-pipeline X might actually contain (X, y)
        if isinstance(X, tuple):
            return self.get_symmetrized(X[0]), X[1]
        else:
            return self.get_symmetrized(X)

    def get_gradient(self):
        raise NotImplementedError('Ooops...')

    # @doc_inherit
    def get_symmetrized(self, C):
        """
        Returns a symmetrized version of the descriptors c (from DensityProjector)

        Parameters
        ----------------
        C , dict of numpy.ndarrays or list of dict of numpy.ndarrays
            Electronic descriptors

        Returns
        ------------
        D, dict of numpy.ndarrays
            Symmetrized descriptors
        """
        made_list = False
        basis = self._attrs['basis']

        # If C is not a list, make it one so that same loop structure can be used.
        # In the end remove this artificial list so that return type is same
        # as input
        if not isinstance(C, list):
            C = [C]
            made_list = True

        results = []
        for dataset in C:
            results_dict = {}
            for spec in dataset:
                results_dict[spec] = self._symmetrize_function(dataset[spec], basis[spec]['l'],
                                                                basis[spec]['n'], self._cgs)
            results.append(results_dict)

        if made_list:
            return results[0]
        else:
            return results

    # @doc_inherit
    def get_gradient(self):
        """Uses chain rule to obtain dE/dC from dE/dD (unsymmetrized from symmetrized)

        Parameters
        ------------------
        dEdD : dict of np.ndarrays or list of dict of np.ndarrays
        	dE/dD

        Returns
        -------------
        dEdc: dict of np.ndarrays
        """
        raise NotImplementedError('Gradient not implemented yet')

class CasimirSymmetrizer(Symmetrizer):


    @staticmethod
    def _symmetrize_function(c, n_l, n, *args):
        """ Returns the casimir invariants of the tensors stored in c

        Parameters:
        -----------

        c: np.ndarray of floats/complex
            Stores the tensor elements in the order (n,l,m)

        n_l: int
            number of angular momenta (not equal to maximum ang. momentum!
                example: if only s-orbitals n_l would be 1)

        n: int
            number of radial functions

        Returns
        -------
        np.ndarray
            Casimir invariants
        """

        c_shape = c.shape

        c = c.reshape(-1,c_shape[-1])
        casimirs = []
        idx = 0

        for n_ in range(0, n):
            for l in range(n_l):
                casimirs.append(np.linalg.norm(c[:,idx:idx+(2*l+1)], axis = 1)**2)
                idx += 2*l + 1
        casimirs = np.array(casimirs).T

        return casimirs.reshape(*c_shape[:-1], -1)

class BispectrumSymmetrizer(Symmetrizer):

    def __init__(self, attrs):
        print('WARNING! This class has not been thoroughly tested yet')
        super().__init__(attrs)

        # Create array with Clebsch-Gordon coefficients
        basis = attrs['basis']

        n_l_max = 0
        for spec in basis:
            n_l_max = max(n_l_max, basis[spec]['l'])

        self._cgs = cg_matrix(n_l_max)

    @staticmethod
    def _symmetrize_function(c, n_l, n, cgs=None):
        """ Returns the bispectrum of the tensors stored in c

        Parameters:
        -----------

        c: np.ndarray of floats/complex
            Stores the tensor elements in the order (n,l,m)

        n_l: int
            number of angular momenta (not equal to maximum ang. momentum!
                example: if only s-orbitals n_l would be 1)

        n: int
            number of radial functions

        cgs: np.ndarray, optional
            Clebsch-Gordan coefficients, if not provided, calculated on-the-fly

        Returns
        -------
        np.ndarray
            Bispectrum
        """
        casimirs = CasimirSymmetrizer._symmetrize_function(c,n_l,n)

        c_shape = c.shape

        c = c.reshape(-1,c_shape[-1])
        c = c.reshape(len(c),n,-1)
        bispectrum = []
        idx = 0

        start = {}
        for l in range(0, n_l):
            start[l] = idx
            idx += 2*l + 1

        if not isinstance(cgs, np.ndarray):
            cgs = cg_matrix(n_l)

        for n in range(0, n):
            print('n = {}'.format(n))
            for l1 in range(n_l):
                for l2 in range(n_l):
                    for l in range(abs(l2-l1),min(l1+l2+1, n_l)):
                        b = 0
                        if np.linalg.norm(cgs[l1,:,l2,:,l,:]) < 1e-15:
                            continue

                        for m in range(-l,l+1):
                            for m1 in range(-l1,l1+1):
                                for m2 in range(-l2,l2+1):
                                    b +=\
                                     np.conj(c[:,n,start[l] + m + l])*\
                                     c[:,n,start[l1] + m1 + l1]*\
                                     c[:,n,start[l2] + m2 + l2]*\
                                     cgs[l1,m1,l2,m2,l,m]
                                     # cgs[l1,l2,l,m1,m2,m]
                        if np.any(abs(b.imag) > 1e-5):
                            raise Exception('Not real')
                        bispectrum.append(b.real.round(5))

        bispectrum = np.array(bispectrum).T

        bispectrum =  bispectrum.reshape(*c_shape[:-1], -1)
        bispectrum = np.concatenate([casimirs, bispectrum], axis = -1)
        return bispectrum

def symmetrizer_factory(symmetrize_instructions):
    """
    Factory for various Symmetrizers (Casimir, Bispectrum etc.).

    Parameters:
    ------------
    symmetrize_instructions : dict
        Should specify 'symmetrizer_type' ('casimir','bispectrum') and
        basis set information (angular momentum, no. radial basis functions)

    Returns:
    --------
    Symmetrizer

    """
    sym_ins = symmetrize_instructions
    symmetrizer_dict = dict(casimir = CasimirSymmetrizer,
                        bispectrum = BispectrumSymmetrizer)

    # symmetrizer_dict = dict(casimir = CasimirSymmetrizer)
    if not 'symmetrizer_type' in sym_ins:
        raise Exception('symmetrize_instructions must contain symmetrizer_type key')

    return symmetrizer_dict[sym_ins['symmetrizer_type'].lower()](sym_ins)


def cg_matrix(n_l):
    """ Returns the Clebsch-Gordan coefficients for maximum angular momentum n_l-1
    """
    lmax = n_l - 1
    cgs = np.zeros([n_l, 2*lmax+1, n_l, 2*lmax+1, n_l, 2*lmax+1], dtype=complex)

    for l in range(n_l):
        for l1 in range(n_l):
            for l2 in range(n_l):
                for m in range(-n_l, n_l+1):
                    for m1 in range(-n_l,n_l+1):
                        for m2 in range(-n_l,n_l+1):
                            # cgs[l1,l2,l,m1,m2,m] = N(CG(l1,l2,l,m1,m2,m).doit())
                            cgs[l1,m1,l2,m2,l,m] = N(CG(l1,m1,l2,m2,l,m).doit())
    return cgs

# def to_casimirs_mixn(c, n_l, n):
#     """ Returns the casimir invariants with mixed radial channels
#     of the tensors stored in c
#
#     Parameters:
#     -----------
#
#     c: np.ndarray of floats/complex
#         Stores the tensor elements in the order (n,l,m)
#
#     n_l: int
#         number of angular momenta (not equal to maximum ang. momentum!
#             example: if only s-orbitals n_l would be 1)
#
#     n: int
#         number of radial functions
#
#     Returns
#     -------
#     np.ndarray
#         Casimir invariants
#     """
#     c_shape = c.shape
#
#     c = c.reshape(-1,c_shape[-1])
#     c = c.reshape(len(c),n,-1)
#     casimirs = []
#
#     for n1 in range(0, n):
#         for n2 in range(n1,n):
#             idx = 0
#             for l in range(n_l):
#                 casimirs.append(np.sum(c[:,n1,idx:idx+(2*l+1)]*\
#                                        np.conj(c[:,n2,idx:idx+(2*l+1)]), axis = -1).real)
#                 idx += 2*l + 1
#
#     casimirs = np.array(casimirs).T
#
#     return casimirs.reshape(*c_shape[:-1], -1)
