#
# masker.py
#
#  Copyright (C) 2013 Diamond Light Source
#
#  Author: James Parkhurst
#
#  This code is distributed under the BSD license, a copy of which is
#  included in the root directory of this package.

from __future__ import division

class MaskerBase(object):
  '''A root class to that does overlap masking'''

  def __init__(self, experiment):
    ''' Initialise the overlap masking algorithm

    Params:
        experiment The experiment data
    '''
    from dials.algorithms.shoebox import MaskOverlapping

    # Construct the overlapping reflection mask
    self.mask_overlapping = MaskOverlapping()


  def __call__(self, reflections, adjacency_list=None):
    ''' Mask the given reflections.

    Params:
        reflections The reflection list
        adjacency_list The adjacency_list (optional)

    Returns:
        The masked reflection list

    '''
    from logging import info

    # Mask the overlaps if an adjacency list is given
    if adjacency_list:
      info('Masking overlapping reflections')
      self.mask_overlapping(
        reflections['shoebox'],
        reflections['xyzcal.px'],
        adjacency_list)
      info('Masked {0} overlapping reflections'.format(
          len(adjacency_list)))

    # Return the reflections
    return reflections

class Masker3DProfile(MaskerBase):
  '''A class to perform 3D profile masking'''

  def __init__(self, experiments, profile_model):
    ''' Initialise the masking algorithms

    Params:
        experiment The experiment data
        delta_d The extent of the reflection in reciprocal space
        delta_m The extent of the reflection in reciprocal space

    '''
    assert(len(experiments) == len(profile_model))
    super(Masker3DProfile, self).__init__(experiments[0])
    self._experiments = experiments
    self._profile_model = profile_model

  def __call__(self, reflections, adjacency_list=None):
    ''' Mask the given reflections.

    Params:
        reflections The reflection list
        adjacency_list The adjacency_list (optional)

    Returns:
        The masked reflection list

    '''
    reflections = super(Masker3DProfile, self).__call__(reflections, adjacency_list)

    # Mask the foreground region
    self._profile_model.compute_mask(self._experiments, reflections)

    # Return the reflections
    return reflections

class MaskerEmpirical(MaskerBase):
  '''A class to perform empirical masking'''

  def __init__(self, experiment, reference):
    ''' Initialise the masking algorithms

    Params:
        experiment The experiment data

    '''
    super(MaskerEmpirical, self).__init__(experiment)

    from dials.algorithms.shoebox import MaskEmpirical

    # Construct the foreground pixel mask
    self.mask_empirical = MaskEmpirical(reference)
    self._reference = reference

  def __call__(self, reflections, adjacency_list=None):
    ''' Mask the given reflections.

    Params:
        reflections The reflection list
        adjacency_list The adjacency_list (optional)

    Returns:
        The masked reflection list

    '''
    reflections = super(MaskerEmpirical, self).__call__(reflections, adjacency_list)

    from logging import info

    if self.mask_empirical:
      # Mask the foreground region
      self.mask_empirical(reflections)

    # Return the reflections
    return reflections
