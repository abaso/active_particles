"""
Module maths provides useful mathematic tools.
"""

import numpy as np

import math

from operator import itemgetter

from scipy import interpolate

from copy import deepcopy

from itertools import product
from functools import partial

from multiprocessing import Pool

def relative_positions(positions, point, box_size):
    """
    Returns relative positions to point in box of extent
    (-box_size/2, box_size) in both dimensions of space.

    Parameters
    ----------
    positions : float array
        Position of single point or array of positions.
    point : float array
        Position of the new centre.
    box_size : float or array
        Length of the box in one dimension or all dimensions.

    Returns
    -------
    rel_positions : float array
        Relative positions.
    """

    return (np.array(positions) - np.array(point)
        + np.array(box_size)/2)%np.array(box_size) - np.array(box_size)/2

def wo_mean(arr):
    """
    Returns deviation of values in array with respect to mean of array.

    Parameters
    ----------
    arr : array like
        Array of values.

    Returns
    -------
    dev_arr : array like
        Deviations from mean of array.
    """

    return np.array(arr) - np.mean(arr, axis=0)

class DictList(dict):
    """
    Custom hash table class to give value [] to uninitialised keys.
    """
    def __init__(self):
        super().__init__()
    def __getitem__(self, key):
        try:
            return super().__getitem__(key)
        except KeyError:
            return []

def g2Dto1D(g2D, L):
    """
    Returns cylindrical average of 2D grid.

    Parameters
    ----------
    g2D : 2D array
        2D grid.
        NOTE: g2D[0, 0] is considered the r=0 point on the grid, and we
        consider periodic boundaries.
    L : float or float array
        Length of the box represented by the grid in one dimension or all
        dimensions.

    Returns
    -------
    g1D : Numpy array
        Array of (r, g1D(r)) with g1D(r) the averaged 2D grid at radius r.
    """

    g2D = np.array(g2D)
    dL = np.array(L)/np.array(g2D.shape)    # boxes separation in each direction
    r_max = np.min(L)/2                     # maximum radius to be calculated in number of boxes

    g1D_dic = DictList()    # hash table of radii and values at radii

    for i in range(g2D.shape[0]):
        for j in range(g2D.shape[1]):
            radius = np.sqrt(np.sum((np.array((i, j))*dL)**2))  # radius corresponding to coordinates [i, j], [-i, j], [i, -j], [-i, -j]
            if radius <= r_max:
                g1D_dic[radius] += [g2D[i, j], g2D[-i, j], g2D[i, -j],
                    g2D[-i, -j]]

    return np.array(list(map(
        lambda radius: [radius, np.mean(g1D_dic[radius])],
        sorted(g1D_dic))))

def g2Dto1Dsquare(g2D, L):
    """
    Returns cylindrical average of square 2D grid.

    Parameters
    ----------
    g2D : 2D array
        Square 2D grid.
        NOTE: g2D[0, 0] is considered the r=0 point on the grid, and we
        consider periodid boundaries.
    L : float
        Length of the box represented by the grid in one dimension.

    Returns
    -------
    g1D : Numpy array
        Array of (r, g1D(r)) with g1D(r) the averaged 2D grid at radius r.
    """

    g2D = np.array(g2D)
    dL = L/g2D.shape[0]             # boxes separation in each direction
    sq_r_max = (g2D.shape[0]/2)**2  # maximum radius to be calculated in number of boxes

    g1D_dic = DictList()    # hash table of radii and values at radii

    for i in range(g2D.shape[0]):
        for j in range(g2D.shape[1]):
            sqradius = i**2 + j**2  # radius corresponding to coordinates [i, j], [-i, j], [i, -j], [-i, -j]
            if sqradius <= sq_r_max:
                g1D_dic[sqradius] += [g2D[i, j], g2D[-i, j], g2D[i, -j],
                    g2D[-i, -j]]

    return np.array(list(map(
        lambda sqradius: [dL*np.sqrt(sqradius), np.mean(g1D_dic[sqradius])],
        sorted(g1D_dic))))

def g2Dto1Dgrid(g2D, grid, average_grid=False):
    """
    Returns cylindrical average of square 2D grid with values of radius given
    by other parameter grid.

    Parameters
    ----------
    g2D : 2D array
        Square 2D grid.
    grid : 2D array
        Array of radii.
    average_grid : bool
        Return g2D grid with cylindrically averaged values.

    Returns
    -------
    g1D : Numpy array
        Array of (r, g1D(r)) with g1D(r) the averaged 2D grid at radius r.
    g2D_cylindrical [average_grid] : Numpy array
        Cylindrically averaged g2D.
    """

    g2D = np.array(g2D)
    grid = np.array(grid)

    g1D_dic = DictList()    # hash table of radii and values at radii

    for i in range(g2D.shape[0]):
        for j in range(g2D.shape[1]):
            g1D_dic[grid[i, j]] += [g2D[i, j]]

    g1D = np.array(list(map(
        lambda radius: [radius, np.mean(g1D_dic[radius])],
        sorted(g1D_dic))))

    if not(average_grid): return g1D

    g2D_cylindrical = np.zeros(grid.shape)
    for radius, mean_g in zip(*np.transpose(g1D)):
        for i, j in zip(*np.where(grid == radius)):
            g2D_cylindrical[i, j] = mean_g

    return g1D, g2D_cylindrical

def normalise1D(*vector):
    """
    Returs 1D vector of unitary norm with same direction.

    Parameters
    ----------
    vector : 1D array-like or coordinates as positional arguments
        Vector to normalise.

    Returns
    -------
    u_vector : 1D Numpy array
        Unitary vector with same direction.
    """

    vector = np.array(vector).flatten() # 1D vector

    norm = np.linalg.norm(vector)   # vector norm
    if norm == 0: return vector     # vector is 0
    return vector/norm

def amplogwidth(arr, factor=2):
    """
    Calculates the amplitudes of elements in array arr and, excluding the
    zeros, returns the mean of the logarithms of these amplitudes plus and
    minus factor times their standard deviation.

    Parameters
    ----------
    arr : array like
        Array.
    factor : float
        Width factor. (default: 2)

    Returns
    -------
    min : float
        E(log(||arr||)) - factor*V(log(||arr||))
    max : float
        E(log(||arr||)) + factor*V(log(||arr||))
    """

    log = np.ma.log10(np.sqrt(np.sum(arr**2, axis=-1))) # logarithms of amplitudes
    mean = log.mean()                                   # means of logarithms of amplitudes
    std = log.std()                                     # standard deviation of logarithms of amplitudes

    return mean - factor*std, mean + factor*std

def mean_sterr(values):
    """
    Returns mean and standard error of values.

    Parameters
    ----------
    values : float array
        Values.

    Returns
    -------
    mean : float
        Mean of values.
    sterr : float
        Standard error of values.
    """

    values = np.array(values)
    if values.size == 0: return None, None

    return np.mean(values), np.std(values)/np.sqrt(np.prod(values.shape))

class Grid:
    """
    Manipulate 2D grids, in which we consider the values to correspond to a
    variable at uniformly distributed positions in space.
    """

    def __init__(self, grid, extent=(-1, 1, -1, 1)):
        """
        Sets the grid.

        Parameters
        ----------
        grid : array-like
            2D grid.
        extent : scalars (left, right, bottom, top)
            Values of space variables at corners. (default: (-1, 1, -1, 1))
        """

        self.grid = np.array(grid)
        self.shape = self.grid.shape    # shape of the grid

        self.extent = extent
        self.box_size = np.array([
            self.extent[1] - self.extent[0],
            self.extent[-1] - self.extent[-2]])
        self.sep_boxes = self.sep_boxes_x, self.sep_boxes_y =\
            self.box_size/self.shape[:2]    # distance between consecutive boxes in each direction

    def __getitem__(self, *key):
        """
        Associates Grid[key] to Grid.grid[key].

        Parameters
        ----------
        key : *
            Key to access.

        Returns
        -------
        value : *
            Grid.grid[key]
        """

        return self.grid.__getitem__(*key)

    def get_grid_indexes(self):
        """
        Returns grid of self.grid indexes and saves them in attributes
        self.grid_indexes.

        Returns
        -------
        grid_index : Numpy array
            Grid of self.grid indexes.
        """

        self.grid_indexes = vector_vector_grid(
            range(self.shape[0]), range(self.shape[1]), dtype=int)
        return self.grid_indexes

    def get_grid_coordinates(self):
        """
        Returns grid of self.grid cartesiancoordinates and saves them in
        attributes self.grid_coordinates.

        Returns
        -------
        grid_coordinates : Numpy array
            Grid of self.grid cartesian coordinates.
        """

        self.grid_coordinates = np.transpose(vector_vector_grid(
            self.extent[0] + self.sep_boxes_x/2
                + np.arange(self.sep_boxes_x*self.shape[0],
                    step=self.sep_boxes_x),
            (self.extent[-2] + self.sep_boxes_y/2
                + np.arange(self.sep_boxes_y*self.shape[0],
                    step=self.sep_boxes_y))[::-1]),
            (1, 0, 2))
        return self.grid_coordinates

    def get_grid_coordinates_polar(self):
        """
        Returns grid of self.grid cartesiancoordinates and saves them in
        attributes self.grid_coordinates.

        Returns
        -------
        grid_coordinates_polar : Numpy array
            Grid of self.grid cartesian coordinates.
        """

        self.get_grid_coordinates()

        radii = np.sqrt(np.sum(self.grid_coordinates**2, axis=-1))
        angles = np.reshape(list(map(lambda x, y: math.atan2(y, x),
            *np.transpose(np.reshape(self.grid_coordinates,
                (np.prod(self.grid_coordinates.shape[:2]), 2))))),
            self.grid_coordinates.shape[:2])

        self.grid_coordinates_polar = np.concatenate((
            np.reshape(radii, (*radii.shape, 1)),
            np.reshape(angles, (*angles.shape, 1))
        ), axis=-1)
        return self.grid_coordinates_polar

    def in_grid(self, x, y):
        """
        Indicates if point (x, y) in cartesian coordinates is in grid.

        Parameters
        ----------
        x : float
            x-coordinate
        y : float
            y-coordinate

        Returns
        -------
        is_in_grid : bool
            (x, y) in grid.
        """

        return (x >= self.extent[0] and x <= self.extent[1]
            and y >= self.extent[2] and y <= self.extent[3])

    def get_value_cartesian(self, x, y, linear_interpolation=False):
        """
        Get value of grid at position in cartesian coordinates.

        Parameters
        ----------
        x : float
            x-coordinate
        y : float
            y-coordinate
        linear_interpolation : bool
            Get value by linear interpolation of neighbouring grid boxes.
            (default: False)

        Returns
        -------
        value : *
            Value at (x, y) with or without linear interpolation.
        """

        if not(self.in_grid(x, y)): return None # point not on grid

        index_y = int((x - self.extent[0])//self.sep_boxes_x)%self.shape[0]     # index correponding to second axis of grid
        index_x = -1-int((y - self.extent[2])//self.sep_boxes_y)%self.shape[1]  # index correponding to first axis of grid

        if not(linear_interpolation): return self.grid[index_x, index_y]

        try:
            nearest_box_pos = self.grid_coordinates[index_x, index_y]       # nearest box position
        except AttributeError:
            nearest_box_pos = self.get_grid_coordinates()[index_x, index_y] # nearest box position

        neighbouring_boxes = neighbouring_boxes_2D(
            (index_x, index_y), self.shape)
        neighbours_values = itemgetter(*neighbouring_boxes)(self.grid)
        neighbours_relative_positions = (nearest_box_pos[::-1] +
            (np.array(neighbouring_boxes_2D((1, 1), 3)) - 1)
            *self.sep_boxes[::-1])[:, ::-1]  # positions of neighbouring boxes

        return interpolate.interp2d(
            *np.transpose(neighbours_relative_positions), neighbours_values,
            kind='linear')(x, y)[0]

    def get_value_polar(self, r, angle, centre=(0, 0),
        linear_interpolation=False):
        """
        Get value of grid at position in polar coordinates.

        Parameters
        ----------
        r : float
            Radius from centre.
        angle : float
            Angle from x-direction.
        centre : float tuple
            Origin for calculation. (default: (0, 0))
        linear_interpolation : bool
            Get value by linear interpolation of neighbouring grid boxes.
            (default: False)

        Returns
        -------
        value : *
            Value at (r, angle) from centre with or without linear
            interpolation.
        """

        x = centre[0] + r*np.cos(angle) # corresponding cartesian x-coordinate
        y = centre[1] + r*np.sin(angle) # corresponding cartesian y-coordinate

        return self.get_value_cartesian(x, y,
            linear_interpolation=linear_interpolation)

class GridFFT(Grid):
    """
    Manipulate 2D grids, in which we consider the values to correspond to a
    variable at uniformly distributed positions in space, and their fast Fourier
    transforms.
    """

    def __init__(self, grid, d=1):
        """
        Sets the grid and its Fourier transform.

        Parameters
        ----------
        grid : array-like
            2D grid.
        d : float
            Sample spacing. (default: 1)
        """

        self.d = d
        self.shape = np.array(grid).shape
        super().__init__(grid, extent=
            (-self.d*self.shape[0]/2, self.d*self.shape[0]/2,
            -self.d*self.shape[1]/2, self.d*self.shape[1]/2))   # initialises superclass

        self.gridFFT = np.fft.fft2(self.grid, axes=(0, 1))      # grid FFT
        self.FFT2Dfilter = FFT2Dfilter(self.gridFFT, d=self.d)  # signal filter

    def gaussian_filter(self, sigma):
        """
        Apply a Gaussian filter on the 2D grid.
        (see active_particles.maths.FFT2Dfilter.gaussian_filter)

        Parameters
        ----------
        sigma : float
            Standard deviation \\sigma of the convoluting Gaussian function.

        Returns
        -------
        filteredGrid : Numpy array
            Filtered grid.
        """

        return self.FFT2Dfilter.gaussian_filter(sigma).get_signal()

def vector_vector_grid(vector1, vector2, dtype=None):
    """
    From vector1 = (v1_i)_i and vector2 = (v2_i)_i, returns matrix
    M = (M_{i, j})_{i, j} = ((v1_i, v2_j))_{i, j}.

    Parameters
    ----------
    vector1 : 1D array-like
        Vector 1.
    vector2 : 1D array-like
        Vector 2.
    dtype : Numpy array dtype
        Data type of the Numpy array to return. (default: None)
        NOTE: if dtype == None, then the array is not converted to any type.

    Returns
    -------
    M : 2D array-like
        Matrix M.
    """

    M = np.zeros((len(vector1), len(vector2), 2))
    M[:, :, 0] = vector1
    M = np.transpose(M, (1, 0, 2))
    M[:, :, 1] = vector2

    if dtype != None: return M.astype(dtype)
    else: return M

def wave_vectors_2D(nx, ny, d=1):
    """
    Returns wave vectors for 2D signals with window lengths nx and ny in the
    two directions and sample spacing d.

    Parameters
    ----------
    nx : int
        Window length in first direction.
    ny : int
        Window length in second direction.
    d : float
        Sample spacing. (default: 1)

    Returns
    -------
    wave_vectors : (nx, ny, 2) Numpy array
        Grid of wave vectors.
    """

    return 2*np.pi*vector_vector_grid(
        np.fft.fftfreq(nx, d=d),
        np.fft.fftfreq(ny, d=d))

def kFFTgrid(grid):
    """
    Calculates the Fast Fourier Transform (FFT) of 2D grid and returns its dot
    and cross product with corresponding normalised wave vector.

    Parameters
    ----------
    grid : array-like
        2D grid of 2D vectors (i.e., (_, _, 2) grid).

    Returns
    -------
    k_cross_grid : grid.shape Numpy array
        Grid of cross products between normalised wave vectors and grid Fourier
        transform.
    k_dot_grid : grid.shape Numpy array
        Grid of dot products between normalised wave vectors and grid Fourier
        transform.
    """

    FFTgrid = np.fft.fft2(grid, axes=(0, 1))                        # Fourier transform of grid
    wave_vectors = wave_vectors_2D(*grid.shape[:2])                 # grid of wave vectors
    wave_vectors_norm = np.sqrt(np.sum(wave_vectors**2, axis=-1))   # grid of wave vectors norm

    k_cross_grid = np.cross(wave_vectors, FFTgrid)   # k cross FFTgrid

    k_dot_grid = np.zeros(FFTgrid.shape[:2], dtype=np.complex128)
    for i in range(FFTgrid.shape[0]):
        for j in range(FFTgrid.shape[1]):
            k_dot_grid[i, j] = np.dot(wave_vectors[i, j],
                FFTgrid[i, j])  # k dot FFTgrid

    return (divide_arrays(k_cross_grid, wave_vectors_norm),
        divide_arrays(k_dot_grid, wave_vectors_norm))

def divide_arrays(array1, array2):
    """
    Divide array1 by array2, and outputs 0 values where array2 is equal to 0.
    NOTE: array1, array2 and out must have the same shapes.

    Parameters
    ----------
    array1 : array-like
        Numerator array.
    array2 : array-like
        Denominator array.

    Returns
    -------
    array : array-like
        Quotient array.
    """

    if not(isinstance(array1, np.ndarray)): array1 = np.array(array1)
    if not(isinstance(array2, np.ndarray)): array2 = np.array(array2)

    return np.divide(array1, array2,
        out=np.zeros(array1.shape, dtype=array1.dtype), where=array2!=0)

def grid_from_function(grid_values, function, dimension=None):
    """
    Returns grid of dimension dimension from function evaluated at
    grid_values.

    NOTE: in 1D, use list(map(function, grid_values)).

    Parameters
    ----------
    grid_values : array-like
        Grid of values at which to evaluate function.
    function : function
        Function of grid values variables.
    dimension : int or None
        Dimension of the grid to return. (default: None)
        NOTE: None is considered as dimension equal to dimension of
        grid_values.
        NOTE : dimension can be lesser than grid_values dimension, in this case
        values in grid_values remaining dimensions are passed as positional
        parameters to function.

    Returns
    -------
    grid : Numpy array
        Grid created from function evaluated at grid_values.
    """

    grid_values = np.array(grid_values)
    grid_values_dimension = len(grid_values.shape)  # dimension of grid_values

    if dimension == None or dimension > grid_values_dimension:
        dimension = grid_values_dimension

    grid_shape = grid_values.shape[:dimension]  # shape of grid
    values_length = np.prod(grid_shape)         # number of elements in grid

    grid = np.array(list(map(
        lambda value: function(*np.array(value).flatten()),
        np.reshape(grid_values,
        (values_length, *grid_values.shape[dimension:])))))

    return np.reshape(grid, grid_shape + grid.shape[1:])

def step_function(X, Y):
    """
    Returns step function f from array-likes X and Y, such that
           | Y[0]      if x <= X[0]
    f(x) = | Y[i + 1]  if X[i] < x <= X[i + 1]
           | Y[-1]     if x >= X[-1]

    NOTE: X and Y must have the same shape.

    Parameters
    ----------
    X : 1D array-like
        x-coordinates.
    Y : 1D array-like
        y-coordinates.

    Returns
    -------
    f : lambda function
        f function.
    """

    return lambda x: Y[next((i for i in range(len(X)) if X[i] >= x), -1)]

class FFT2Dfilter:
    """
    Filter 2D signal from Fourier components obtained via fast Fourier
    transform.

    /!\\ WARNING /!\\
    Using bandlimiting low-pass filters self.cut_high_wave_frequencies and
    self.cut_low_wave_lengths may cause ringing artifacts (see
    https://en.wikipedia.org/wiki/Ringing_artifacts).
    """

    def __init__(self, signalFFT, d=1, **kwargs):
        """
        Defines wave vectors corresponding to input FFT.
        NOTE: It is assumed that the order of Fourier components has not been
        altered from the np.fft.fft2 function.

        Parameters
        ----------
        signalFFT : 2D array-like
            Fast Fourier transform of signal.
        d : float
            Sample spacing. (default: 1)

        Optional keyword arguments
        --------------------------
        wave_vectors : (*signalFFT.shape, 2) array-like
            Wave vectors corresponding to signalFFT components.
        """

        self.signalFFT = np.array(signalFFT)    # signal fast Fourier transform

        if not('wave_vectors' in kwargs):                                       # no input wave vectors
            self.wave_vectors = wave_vectors_2D(*self.signalFFT.shape[:2], d=d) # wave vectors corresponding to signalFFT components
        else: self.wave_vectors = np.array(kwargs['wave_vectors'])
        self.wave_vectors_norm = np.sqrt(np.sum(self.wave_vectors**2, axis=-1)) # wave vectors norm

    def get_signal(self):
        """
        Gets signal defined by the Fourier components in self.signalFFT.

        Returns
        -------
        signal : Numpy array
            Signal from inverse fast Fourier transform.
        """

        return np.fft.ifft2(self.signalFFT, axes=(0, 1))

    def cut_low_wave_frequencies(self, threshold):
        """
        Sets Fourier components corresponding to wave vectors corresponding to
        frequencies lower than threshold to 0.

        Parameters
        ----------
        threshold : float
            Threshold frequency for cutting.

        Returns
        -------
        filteredFFT : active_particles.maths.FFT2Dfilter
            Filtered Fourier components.
        """

        filteredFFT = deepcopy(self)
        filteredFFT.signalFFT[filteredFFT.wave_vectors_norm < threshold] = 0   # cut low wave frequencies

        return filteredFFT

    def cut_high_wave_frequencies(self, threshold):
        """
        Sets Fourier components corresponding to wave vectors corresponding to
        frequencies higher than threshold to 0.

        Parameters
        ----------
        threshold : float
            Threshold frequency for cutting.

        Returns
        -------
        filteredFFT : active_particles.maths.FFT2Dfilter
            Filtered Fourier components.
        """

        filteredFFT = deepcopy(self)
        filteredFFT.signalFFT[filteredFFT.wave_vectors_norm > threshold] = 0   # cut high wave frequencies

        return filteredFFT

    def cut_low_wave_lengths(self, threshold):
        """
        Sets Fourier components corresponding to wave vectors corresponding to
        lengths lower than threshold to 0.

        Parameters
        ----------
        threshold : float
            Threshold length for cutting.

        Returns
        -------
        filteredFFT : active_particles.maths.FFT2Dfilter
            Filtered Fourier components.
        """

        return self.cut_high_wave_frequencies(np.divide(2*np.pi, threshold))

    def cut_high_wave_lengths(self, threshold):
        """
        Sets Fourier components corresponding to wave vectors corresponding to
        lengths higher than threshold to 0.

        Parameters
        ----------
        threshold : float
            Threshold length for cutting.

        Returns
        -------
        filteredFFT : active_particles.maths.FFT2Dfilter
            Filtered Fourier components.
        """

        return self.cut_low_wave_frequencies(np.divide(2*np.pi, threshold))

    def gaussian_filter(self, sigma):
        """
        Multiply signal FFT with Gaussian function
        exp(-1/2 \\sigma^2\\vec{k^2}) of wave vectors \\vec{k}, such that the
        resulting signal is a convolution of the original signal with the
        normalised Gaussian function
        1/(2\\pi\\sigma^2) exp(-\\vec{r}^2/(2\\sigma^2)) of space variable
        \\vec{r}.

        Parameters
        ----------
        sigma : float
            Standard deviation \\sigma of the convoluting Gaussian function.

        Returns
        -------
        filteredFFT : active_particles.maths.FFT2Dfilter
            Filtered Fourier components.
        """

        filteredFFT = deepcopy(self)
        if sigma == 0: return filteredFFT   # no filtering

        gaussian_coefficients = np.exp(
            -1/2*(sigma**2)*np.sum(self.wave_vectors**2, axis=-1))
        try:
            filteredFFT.signalFFT *= gaussian_coefficients
        except ValueError:
            filteredFFT.signalFFT *= np.reshape(gaussian_coefficients,
                gaussian_coefficients.shape + (1,))

        return filteredFFT

def count(arrays, max_norm):
    """
    Returns number of arrays in array which norm is lesser than or equal to
    max_norm in infite norm.

    Parameters
    ----------
    arrays : 2D array-like
        Arrays.
    max_norm : float
        Maximum norm.

    Returns
    -------
    N : int
        Number of arrays which norm is lesser than or equal to max_norm in
        infinite norm.
    """

    return np.sum((abs(np.array(arrays)) <= max_norm).all(axis=-1))

def gaussian_smooth_1D(X, Y, sigma, *x):
    """
    From y-coordinates Y at corresponding x-coordinates X, this function
    returns smoothed y-coordinates with smoothing function exp(-(x/sigma)^2)
    at x-coordinates x.

    Parameters
    ----------
    X : array-like
        Input x-coordinates.
    Y : array-like
        Input y-coordinates.
    sigma : float
        Smoothing length scale.
        NOTE: if sigma == 0 or None, a linear interpolation is performed.
    x : float
        Output x-coordinates.
        NOTE: if no x is passed, then smoothed y-coordinates are returned at X.

    Returns
    -------
    smoothedY : array-like
        Smoothed y-coordinates.
    """

    X = np.array(X)
    Y = np.array(Y)

    if x == (): x = X
    else: x = np.array(x)

    if sigma == 0 or sigma == None: # perform linear interpolation
        return interpolate.interp1d(X, Y,
            kind='linear', fill_value='extrapolate')(x)

    smoothing_function = lambda x: np.exp(-(x/sigma)**2)
    smoothedY = np.empty(len(x))

    for index in range(len(x)):
        smoothing_coefficients = list(map(smoothing_function, X - x[index]))
        smoothedY[index] =\
            np.sum(Y*smoothing_coefficients)/np.sum(smoothing_coefficients)

    return smoothedY

def gaussian_smooth_2D(X, Y, Z, sigma, *xy):
    """
    From z-coordinates Z at corresponding pairs of x-coordinates X and
    y-coordinates Y, this function returns smoothed z-coordinates with
    smoothing function exp(-(x^2 + y^2)/sigma^2) at xy-coordinates xy.

    Parameters
    ----------
    X : array-like
        Input x-coordinates.
    Y : array-like
        Input y-coordinates.
    Z : array-like
        Input z-coordinates.
    sigma : float
        Smoothing length scale.
        NOTE: if sigma == 0 or None, a linear interpolation is performed.
    xy : 2-uple of float
        Output xy-coordinates as 2-uples (x, y).
        NOTE: if no xy are passed, then smoothed xy-coordinates are returned
              at X and Y.

    Returns
    -------
    smoothedZ : array-like
        Smoothed z-coordinates.
    """

    XY = np.vstack((X, Y)).T
    Z = np.array(Z)

    if xy == (): xy = XY
    else: xy = np.array(xy)

    if sigma == 0 or sigma == None: # perform linear interpolation
        return np.array(list(map(
            lambda x, y: interpolate.griddata(XY, Z, [(x, y)],
                method='linear')[0],
            *xy.T)))

    smoothing_function = lambda x, y: np.exp(-(x**2 + y**2)/(sigma**2))
    smoothedZ = np.empty(len(xy))

    for index in range(len(xy)):
        smoothing_coefficients = list(map(smoothing_function,
            *(XY - xy[index]).T))
        smoothedZ[index] =\
            np.sum(Z*smoothing_coefficients)/np.sum(smoothing_coefficients)

    return smoothedZ

def neighbouring_boxes_2D(index, shape):
    """
    In a 2D grid of shape shape with periodic boundaries, this function returns
    the 9 neighbouring boxes indexes of box with index index, including index.

    Parameters
    ----------
    index : 2-uple of int
        Index of the box to get neighbours of.
    shape : 2-uple of int or int
        Number of boxes in all or one direction.

    Returns
    -------
    neighbours : list of 2-uple
        List of indexes of neighbouring boxes.
    """

    index = np.array(index, dtype=int)
    shape = (lambda shape: np.array([shape[0], shape[-1]], dtype=int))(
        np.array(shape, ndmin=1))
    neighbours = []

    for inc_x in [-1, 0, 1]:        # increment in x index
        for inc_y in [-1, 0, 1]:    # increment in y index
            inc = np.array([inc_x, inc_y], dtype=int)
            neighbours += [tuple((index + inc + shape)%shape)]

    return neighbours

class Histogram:
    """
    Make histogram from lists of float values.
    """

    def __init__(self, Nbins, vmin, vmax, log=False):
        """
        Parameters
        ----------
        Nbins : int
            Number of histogram bins.
        vmin : float
            Minimum included value for histogram bins.
            NOTE: values lesser than vmin will be ignored.
        vmax : float
            Maximum excluded value for histogram bins.
            NOTE: values greater or equal to vmax will be ignored.
        log : bool.
            Logarithmically spaced histogram values. (default: False)
        """

        self.Nbins = int(Nbins)
        self.vmin = vmin
        self.vmax = vmax

        if log:
            self.bins = np.logspace(np.log10(self.vmin), np.log10(self.vmax),
                self.Nbins, endpoint=False, base=10)    # histogram bins
        else:
            self.bins = np.linspace(self.vmin, self.vmax,
                self.Nbins, endpoint=False)             # histogram bins

        self.reset_values()                 # reset values from which to compute the histogram
        self.hist = np.empty(self.Nbins)    # values of the histogram at bins

    def add_values(self, *values, replace=False):
        """
        Add values from which to compute the histogram.

        Parameters
        ----------
        values : float or float array-like
            Values to add.
        replace : bool
            Replace existing values. (default: False)
        """

        if replace: self.reset_values()
        for value in values: self.values = np.append(self.values, value)

    def reset_values(self):
        """
        Delete values from which to compute the histogram (self.values).
        """

        self.values = np.array([])

    def get_histogram(self):
        """
        Get histogram from values in self.values.

        Returns
        -------
        hist : Numpy array
            Values of the histogram at self.bins.
        """

        for bin in range(self.bins.size):
            bin_inf = self.bins[bin]
            try: bin_sup = self.bins[bin + 1]
            except IndexError: bin_sup = self.vmax
            self.hist[bin] = np.sum(
                (self.values >= bin_inf)*(self.values < bin_sup))

        binned_values = np.sum(self.hist)
        if binned_values == 0: return self.hist # no binned value
        else: self.hist /= np.sum(self.hist)
        return self.hist

class Wrap:
    """
    Wrap functions.
    """

    def __init__(self, x, y, p):
        """
        Initialises class to wrap the function with values y at x so that it is
        p-periodic.

        Parameters
        ----------
        x : array-like
            Array of points at which the original function has been evaluated.
        y : array-like
            Values of the function at points x.
        p : array-like
            Period of the function in each direction.
        """

        self.x = np.array(x)
        try:
            self.n, self.xdim = self.x.shape    # number of points and dimension of space
        except ValueError:
            self.x = np.reshape(self.x, (len(self.x), 1))
            self.n, self.xdim = self.x.shape

        self.y = np.array(y)
        try:
            _, self.ydim = y.shape  # dimension of values
        except ValueError:
            self.ydim = 1

        self.xmin = np.min(self.x, axis=0)  # array of minimum positions by dimension
        self.xmax = np.max(self.x, axis=0)  # array of maximum positions by dimension

        self.p = p

    def evaluate(self, *X, method='linear', fill_value=0, processes=None):
        """
        Evaluate wrapped function at points X.

        NOTE: Original function is interpolated.

        NOTE: As a matter of efficiency, wrapped function at points in X is
              evaluated with a pool of worker processes. (see
              multiprocessing.Pool and multiprocessing.Pool.starmap)

        Parameters
        ----------
        method : string
            Method of interpolation. (see scipy.interpolate.griddata)
            DEFAULT: linear
        fill_value : float
            Value used to fill in for requested points outside of the convex
            hull of the input points. (see scipy.interpolate.griddata)
            DEFAULT: 0
        processes : int
            Number of worker processes to use. (see multiprocessing.Pool)
            NOTE: If processes == None then processes = os.cpu_count().
            DEFAULT: None

        Positional arguments
        --------------------
        X : (self.xdim,) array-like
            Points at which to evaluate the wrapped function.

        Returns
        -------
        Y : (len(X), self.ydmin) array-like
            Wrapped function evaluated at X.
        """

        with Pool(processes=processes) as pool: # pool of worker processes
            Y = pool.starmap(
                partial(self._evaluate, method=method, fill_value=fill_value),
                product(X))
        return np.array(Y)

    def _evaluate(self, X, method='linear', fill_value=0):
        """
        Evaluate wrapped function at point X.

        NOTE: Original function is interpolated.

        NOTE: This function is to be called by
              active_particles.maths.Wrap.evaluate.

        Parameters
        ----------
        X : (self.xdim,) array-like
            Point at which to evaluate the wrapped function.
        method : string
            Method of interpolation. (see scipy.interpolate.griddata)
            DEFAULT: linear
        fill_value : float
            Value used to fill in for requested points outside of the convex
            hull of the input points. (see scipy.interpolate.griddata)
            DEFAULT: 0

        Returns
        -------
        Y : (self.ydim,) Numpy array
            Wrapped function evaluated at X.
        """

        X = np.array(X)
        Y = np.zeros((self.ydim,))

        mmin = np.array(list(map(math.ceil, (self.xmin - X)/self.p)))
        mmax = np.array(list(map(math.floor, (self.xmax - X)/self.p)))
        for m in np.ndindex(tuple(mmax - mmin + 1)):
            m = mmin + np.array(m)
            Y += interpolate.griddata(self.x, self.y, X + self.p*m,
                method=method, fill_value=fill_value)[0]

        return Y
