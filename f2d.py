from __future__ import division # No automatic floor division
from base import *

# class F2D inherits Flexure and overrides __init__ therefore setting up the same
# three parameters as class Isostasy; and it then sets up more parameters specific
# to its own type of simulation.
class F2D(Flexure):
  def initialize(self, filename):
    super(F2D, self).initialize(filename)
    if debug: print 'F2D initialized'

  def run(self):
    if self.method == 'FD':
      # Finite difference
      super(F2D, self).FD()
      self.method_func = self.FD
    elif self.method == 'FFT':
      # Fast Fourier transform
      super(F2D, self).FFT()
      self.method_func = self.FFT
    elif self.method == "SPA":
      # Superposition of analytical solutions
      super(F2D, self).SPA()
      self.method_func = self.SPA   
    elif self.method == "SPA_NG":
      # Superposition of analytical solutions,
      # nonuniform points
      super(F2D, self).SPA_NG()
      self.method_func = self.SPA_NG
    else:
      print 'Error: method must be "FD", "FFT", or "SPA"'
      self.abort()

    if debug: print 'F2D run'
    if self.method != "SPA_NG":
      self.makedy()
    self.method_func ()
    #self.imshow(self.w) # debugging

  def finalize(self):
    if debug: print 'F2D finalized'
    super(F2D, self).finalize()
    
  ########################################
  ## FUNCTIONS FOR EACH SOLUTION METHOD ##
  ########################################

  def FD(self):
    dx4, dy4, dx2dy2, D = self.elasprep(self.dx,self.dy,self.Te,self.E,self.nu)
    self.coeff = self.coeff_matrix(D,self.drho,dx4,dy4,dx2dy2,self.nu,self.g)
    self.w = self.direct_fd_solve(self.coeff,self.q0)
    
  def FFT(self):
    print "The fast fourier transform solution method is not yet implemented."

  def SPA(self):
    self.spatialDomainVars()
    self.spatialDomainGridded()

  def SPA_NG(self):
    self.spatialDomainVars()
    self.spatialDomainNoGrid()

  
  ######################################
  ## FUNCTIONS TO SOLVE THE EQUATIONS ##
  ######################################
  
  ## General
  ############

  def makedy(self):
    """
    My solution method requires that dy and dx are equal
    Though I bet you could get away with small differences
    (In fact, when I tried it, it looked convincing)
    So maybe it is just rigorously correct for dx=dy?
    """
    self.dy = self.dx
    # Gives dy to "self", so don't need to return anything

  
  ## SPATIAL DOMAIN SUPERPOSITION OF ANALYTICAL SOLUTIONS
  #########################################################

  # SETUP

  def spatialDomainVars(self):
    from numpy import pi
    self.D = self.E*self.Te**3/(12*(1-self.nu**2)) # Flexural rigidity
    self.alpha = (self.D/(self.drho*self.g))**.25 # 2D flexural parameter
    self.coeff = self.alpha**2/(2*pi*self.D)

  # GRIDDED

  def spatialDomainGridded(self):
  
    from numpy import arange, zeros, exp, sin, cos, pi, meshgrid, sqrt
    from scipy.special import kei
  
    self.nx = self.q0.shape[1]
    self.x = arange(0,self.dx*self.nx,self.dx)
    
    self.ny = self.q0.shape[0]
    self.y = arange(0,self.dx*self.nx,self.dx)
    
    # Prepare a large grid of solutions beforehand, so we don't have to
    # keep calculating kei (time-intensive!)
    # This pre-prepared solution will be for a unit load
    bigshape = 2*self.ny+1,2*self.nx+1 # Tuple shape

    dist_ny = arange(bigshape[0]) - self.ny
    dist_nx = arange(bigshape[1]) - self.nx

    dist_x,dist_y = meshgrid(dist_nx*self.dx,dist_ny*self.dy)

    bigdist = sqrt(dist_x**2 + dist_y**2) # Distances from center
                                          # Center at [ny,nx]
    
    biggrid = self.coeff * kei(bigdist/self.alpha) # Kelvin fcn solution

    # Now compute the deflections
    self.w = zeros((self.ny,self.nx)) # Deflection array
    for i in range(self.nx):
      for j in range(self.ny):
        # Loop over locations that have loads, and sum
        if self.q0[j,i]:
          # Solve by summing portions of "biggrid" while moving origin
          # to location of current cell
          # Load must be multiplied by grid cell size
          self.w += self.q0[j,i] * self.dx * self.dy \
             * biggrid[self.ny-j:2*self.ny-j,self.nx-i:2*self.nx-i]
      # No need to return: w already belongs to "self"

  # NO GRID

  def spatialDomainNoGrid(self):
  
    from numpy import exp, sin, cos, pi, sqrt, zeros
    from scipy.special import kei
  
    # Reassign q0 for consistency
    #self.x = self.q0[:,0]
    #self.y = self.q0[:,1]
    #self.q0 = self.q0[:,2]
    
    self.w = zeros(self.q0.shape)
    for i in range(len(self.x)):
      # Get the point
      x0 = self.x[i]
      y0 = self.y[i]
      # Create array of distances from point of load
      r = sqrt((self.x - x0)**2 + (self.y - y0)**2)
      # Compute and sum deflection
      self.w += self.q0[i] * self.coeff * kei(r/self.alpha)


  ## FINITE DIFFERENCE
  ######################
  
  def elasprep(self,dx,dy,Te,E=1E11,nu=0.25):
    """
    dx4, dy4, dx2dy2, D = elasprep(dx,dy,Te,E=1E11,nu=0.25)
    
    Defines the variables that are required to create the 2D finite 
    difference solution coefficient matrix
    """
    dx4 = dx**4
    dy4 = dy**4
    dx2dy2 = dx**2 * dy**2
    D = E*Te**3/(12*(1-nu**2))
    output = dx4, dy4, dx2dy2, D
    return output

  
  def coeff_matrix(self,D,drho,dx4,dy4,dx2dy2,nu=0.25,g=9.8):
    """
    coeff = coeff_matrix(D,drho,dx4,dy4,dx2dy2,nu=0.25,g=9.8)
    where D is the flexural rigidity, drho is the density difference between
    the mantle and the material filling the depression, nu is Poisson's ratio,
    g is gravitational acceleration at Earth's surface (approx. 9.8 m/s),
    and dx4, dy4, and dx2dy2 are based on the grid dimensions.
    
    All grid parameters except nu and g are generated by the function
    varprep2d, located inside this module

    Calculates the matrix of coefficients that is later used via sparse matrix
    solution techniques (scipy.sparse.linalg.spsolve) to compute the flexural
    response to the load. This step need only be performed once, and the
    coefficient matrix can very rapidly compute flexural solutions to any load.
    This makes this particularly good for probelms with time-variable loads or 
    that require iteration (e.g., water loading, in which additional water 
    causes subsidence, causes additional water detph, etc.).

    This method of coefficient matrix construction utilizes longer-range
    symmetry in the coefficient matrix to build it block-wise, as opposed to
    the much less computationally efficient row-by-row ("serial") method 
    that was previously employed.

    NOTATION FOR COEFFICIENT BIULDING MATRICES (e.g., "cj0i_2"):
    c = "coefficient
    j = columns = x-value
    j0 = no offset: look at center of array
    i = rows = y-value
    i_2 = negative 2 offset (i2 = positive 2 offset)
    """
    
    from scipy import sparse
    from numpy import array

    # Build matrices containing all of the values for each of the coefficients
    # that must be linearly combined to solve this equation
    # 13 coefficients: 13 matrices of the same size as the load

    cj2i0 = (D[1:-1,1:-1] + 0.5*(D[2:,1:-1] - D[:-2,1:-1]))/dy4
    cj1i_1 = (2*D[1:-1,1:-1] \
      + 0.5*(-D[1:-1,2:] + D[1:-1,:-2] + D[2:,1:-1] - D[:-2,1:-1]) \
      + ((1-nu)/8) * (D[2:,2:] - D[:-2,2:] - D[2:,:-2] \
        + D[:-2,:-2])) / dx2dy2
    cj1i0 = (-6*D[1:-1,1:-1] + 2*D[:-2,1:-1])/dy4 \
      + nu*(D[1:-1,2:] - 2*D[1:-1,1:-1] + D[1:-1,:-2])/dx2dy2 \
      + (-D[2:,1:-1] - 4*D[1:-1,1:-1] + D[:-2,1:-1])/dx2dy2
    cj1i1 = (2*D[1:-1,1:-1] \
      + 0.5*(D[1:-1,2:] - D[1:-1,:-2] + D[2:,1:-1] - D[:-2,1:-1]) \
      + ((1-nu)/8)*(D[2:,2:] - D[:-2,2:] - D[2:,:-2] + D[:-2,:-2])) \
      /dx2dy2
    cj0i_2 = (D[1:-1,1:-1] - 0.5*(D[1:-1,2:] - D[1:-1,:-2])) / dx4
    cj0i_1 = (2*D[1:-1,2:] - 6*D[1:-1,1:-1]) / dx4 \
      + nu*(D[2:,1:-1] - 2*D[1:-1,1:-1] + D[:-2,1:-1]) / dx2dy2 \
      + (D[1:-1,2:] - 4*D[1:-1,1:-1] - D[1:-1,2:]) / dx2dy2
    cj0i0 = (-2*D[1:-1,2:] + 10*D[1:-1,1:-1] - 2*D[1:-1,:-2]) / dx4 \
      + (-2*D[2:,1:-1] + 10*D[1:-1,1:-1] - 2*D[:-2,1:-1]) / dy4 \
      + (8*D[1:-1,1:-1]) / dx2dy2 \
      + nu*(-2*D[1:-1,2:] - 2*D[1:-1,:-2] + 8*D[1:-1,1:-1] \
        - 2*D[2:,1:-1] -2*D[:-2,1:-1]) / dx2dy2 \
      + drho*g
    cj0i1 = (-6*D[1:-1,1:-1] + 2*D[1:-1,:-2]) / dx4 \
      + nu*(D[2:,1:-1] - 2*D[1:-1,1:-1] + D[:-2,1:-1]) / dx2dy2 \
      + (-D[1:-1,2:] - 4*D[1:-1,1:-1] + D[1:-1,:-2]) / dx2dy2
    cj0i2 = (D[1:-1,1:-1] + 0.5*(D[1:-1,2:] - D[1:-1,:-2])) / dx4
    cj_1i_1 = (2*D[1:-1,1:-1] \
      + 0.5*(-D[1:-1,2:] + D[1:-1,:-2] - D[2:,1:-1] + D[:-2,1:-1]) \
      + ((1-nu)/8)*(D[2:,2:] - D[:-2,2:] - D[2:,:-2] + D[:-2,:-2])) \
      / dx2dy2
    cj_1i0 = (2*D[2:,1:-1] - 6*D[1:-1,1:-1]) / dy4 \
      + nu*(D[1:-1,2:] - 2*D[1:-1,1:-1] + D[1:-1,:-2]) / dx2dy2 \
      + (D[2:,1:-1] - 4*D[1:-1,1:-1] - D[:-2,1:-1]) / dx2dy2
    cj_1i1 = (2*D[1:-1,1:-1] \
      + 0.5*(D[1:-1,2:] - D[1:-1,:-2] - D[2:,1:-1] + D[:-2,1:-1]) \
      - ((1-nu)/8) * (D[2:,2:] - D[:-2,2:] - D[2:,:-2] \
        + D[:-2,:-2])) / dx2dy2
    cj_2i0 = (D[1:-1,1:-1] - 0.5*(D[2:,1:-1] - D[:-2,1:-1])) / dy4

    # ASSEMBLE COEFFICIENT MATRIX

    # Loop over rows, with each block being a square with both side
    # lengths being the number of columns (i.e. the number of entries 
    # in each row)
    ncolsx = cj0i0.shape[1]
    nrowsy = cj0i0.shape[0]

    # Create a block of zeros to pad the blocks with diagonals and
    # keep everything in the right place.
    # Also important because we will be concatenating these arrays
    # together and need all the sparse arrays to have the same size
    # Looks like actually more efficient if I don't use this, though 
    # it is a nicer conceptualization
    #zeroblock = sparse.dia_matrix( (ncolsx,ncolsx) );

    for i in range(nrowsy):

      # CREATE SPARSE n-DIAGONAL BLOCKS FROM EACH ROW OF THESE MATRICES

      # Leftmost / bottom (which is topmost compared to point about which
      # we are calculating)
      coeffs = cj2i0[i,:]
      offsets = array([0])
      l2 = sparse.dia_matrix( (coeffs,offsets), shape = (ncolsx,ncolsx) )

      # Mid-left
      coeffs = array([cj1i_1[i,:],cj1i0[i,:],cj1i1[i,:]])
      offsets = array([-1,0,1])
      l1 = sparse.dia_matrix( (coeffs,offsets), shape = (ncolsx,ncolsx) )
      
      # Center
      coeffs = array([cj0i_2[i,:],cj0i_1[i,:],cj0i0[i,:],
                         cj0i1[i,:],cj0i2[i,:]])
      offsets = array([-2,-1,0,1,2])
      c0 = sparse.dia_matrix( (coeffs,offsets), shape = (ncolsx,ncolsx) )
      
      # Mid-right
      coeffs = array([cj_1i_1[i,:],cj_1i0[i,:],cj_1i1[i,:]])
      offsets = array([-1,0,1])
      r1 = sparse.dia_matrix( (coeffs,offsets), shape = (ncolsx,ncolsx) )
      
      # Right
      coeffs = cj2i0[i,:]
      offsets = array([0])
      r2 = sparse.dia_matrix( (coeffs,offsets), shape = (ncolsx,ncolsx) )
      
      # ASSEMBLE INTO ONE ROW OF BLOCKS FOR EACH TIME-STEP
      # Adding blocks of zeros of size ncolsx to each side of the array
      # in order to pad it for later concatenation (i.e. making all same size
      # and putting nonzero blocks in correct places)
      # There has got to be a more elegant way to do this, but I don't know it
      # and it will take longer to figure out than to just write it all out now.
      
      if i>=3 and i<=nrowsy-4: # If no truncation at edges (normal case)
        leftzeros = sparse.dia_matrix((ncolsx,ncolsx*(i-2)))
        rightzeros = sparse.dia_matrix((ncolsx,ncolsx*(nrowsy-3-i)))
        coeff_row = sparse.hstack( [leftzeros,l2,l1,c0,r1,r2,rightzeros] )
      
      elif i==0:
        rightzeros = sparse.dia_matrix((ncolsx,ncolsx*(nrowsy-3-i)))
        coeff_row = sparse.hstack( [c0,r1,r2,rightzeros] )
        
      elif i==1:
        rightzeros = sparse.dia_matrix((ncolsx,ncolsx*(nrowsy-3-i)))
        coeff_row = sparse.hstack( [l1,c0,r1,r2,rightzeros] )
      
      elif i==2:
        rightzeros = sparse.dia_matrix((ncolsx,ncolsx*(nrowsy-3-i)))
        coeff_row = sparse.hstack( [l2,l1,c0,r1,r2,rightzeros] )
      
      elif i==nrowsy-1:
        leftzeros = sparse.dia_matrix((ncolsx,ncolsx*(i-2)))
        coeff_row = sparse.hstack( [leftzeros,l2,l1,c0] )
      
      elif i==nrowsy-2:
        leftzeros = sparse.dia_matrix((ncolsx,ncolsx*(i-2)))
        coeff_row = sparse.hstack( [leftzeros,l2,l1,c0,r1] )

      elif i==nrowsy-3:
        leftzeros = sparse.dia_matrix((ncolsx,ncolsx*(i-2)))
        coeff_row = sparse.hstack( [leftzeros,l2,l1,c0,r1,r2] )

      # Concatenate these together
      # Looping over rows, so adding each set of values onto the bottom
      # of the previous set
      if i: # Can't concatenate the first time through loop when you only have one row
        c = sparse.vstack( [c,coeff_row] )
      elif ~i: # Create the array when you have only one row i=0
        c = coeff_row

    return c


  def direct_fd_solve(self,coeff,q0):
    """
    w = direct_fd_solve(coeff,q0) \\
    \\
    Sparse Thomas algorithm-based flexural response calculation.
    Requires the coefficient matrix from "2D.coeff_matrix"
    """
    from scipy.sparse.linalg import spsolve
    from scipy.sparse import csr_matrix
    from numpy import prod
    
    # Convert coefficient array format to csr for sparse solver
    coeff = csr_matrix(coeff)
    
    q0vector = q0.reshape(1,prod(q0.shape))
    q0vector = csr_matrix(q0vector)
    wvector = spsolve(coeff,q0vector)
    w = -wvector.reshape(q0.shape)

    return w
    
  ##############
  ## PLOTTING ##
  ##############

  def imshow(self,image):
    # Plot if you want to - for troubleshooting
    from matplotlib.pyplot import imshow, show, colorbar, figure
    figure()
    imshow(image,interpolation='nearest') #,interpolation='nearest'
    colorbar()
    show()