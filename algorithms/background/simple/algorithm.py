#!/usr/bin/env python
#
# general.py
#
#  Copyright (C) 2013 Diamond Light Source
#
#  Author: James Parkhurst
#
#  This code is distributed under the BSD license, a copy of which is
#  included in the root directory of this package.

from __future__ import division

class BackgroundAlgorithm(object):
  ''' Class to do background subtraction. '''

  def __init__(self, experiments,
               outlier='nsigma',
               model='constant3d',
               **kwargs):
    ''' Initialise the algorithm. '''
    from dials.algorithms.background.simple import Creator
    from dials.algorithms.background.simple import TruncatedOutlierRejector
    from dials.algorithms.background.simple import NSigmaOutlierRejector
    from dials.algorithms.background.simple import NormalOutlierRejector
    from dials.algorithms.background.simple import MosflmOutlierRejector
    from dials.algorithms.background.simple import Constant2dModeller
    from dials.algorithms.background.simple import Constant3dModeller
    from dials.algorithms.background.simple import Linear2dModeller
    from dials.algorithms.background.simple import Linear3dModeller

    def select_modeller():
      if model == 'constant2d':
        return Constant2dModeller()
      elif model == 'constant3d':
        return Constant3dModeller()
      elif model == 'linear2d':
        return Linear2dModeller()
      elif model == 'linear3d':
        return Linear3dModeller()
      raise RuntimeError("Unexpected background model %s" % model)

    def select_rejector():
      if outlier == 'null':
        return None
      elif outlier == 'truncated':
        return TruncatedOutlierRejector(
          kwargs.get("lower", 0.01),
          kwargs.get("upper", 0.01))
      elif outlier == 'nsigma':
        return NSigmaOutlierRejector(
          kwargs.get("lower", 3),
          kwargs.get("upper", 3))
      elif outlier == 'normal':
        return NormalOutlierRejector(
          kwargs.get("min_pixels", 10))
      elif outlier == 'mosflm':
        return MosflmOutlierRejector(
          kwargs.get("fraction", 1.0),
          kwargs.get("n_sigma", 4.0))
      raise RuntimeError("Unexpected outlier rejector %s" % outlier.algorithm)

    modeller = select_modeller()
    rejector = select_rejector()
    self._creator = Creator(modeller, rejector)

  def compute_background(self, reflections):
    ''' Compute the backgrond. '''
    from logging import info
    from dials.array_family import flex
    from time import time

    # Do the background subtraction
    start_time = time()
    info('')
    info(' Beginning background modelling')
    info('  using %d reflections' % len(reflections))
    reflections['background.mse'] = flex.double(len(reflections))
    success = self._creator(
      reflections['shoebox'],
      reflections['background.mse'])
    reflections['background.mean'] = reflections['shoebox'].mean_background()
    reflections.set_flags(success != True, reflections.flags.dont_integrate)
    info('  successfully processed %d reflections' % success.count(True))
    info('  time taken: %g seconds' % (time() - start_time))
