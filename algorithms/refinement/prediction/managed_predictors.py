#
#  Copyright (C) (2013) STFC Rutherford Appleton Laboratory, UK.
#
#  Author: David Waterman.
#
#  This code is distributed under the BSD license, a copy of which is
#  included in the root directory of this package.
#

"""Managed reflection prediction for refinement.

* ScansRayPredictor adapts DIALS prediction for use in refinement, by keeping
  up to date with the current model geometry
* StillsRayPredictor predicts reflections without a goniometer, under
  the naive assumption that the relp is already in reflecting position

"""

from __future__ import division

from math import pi
from scitbx import matrix
from dials.algorithms.spot_prediction import ScanStaticRayPredictor

from dials.algorithms.spot_prediction import ScanStaticReflectionPredictor
from dials.algorithms.spot_prediction import StillsReflectionPredictor

class ScansRayPredictor(object):
  """
  Predict for a relp based on the current states of models of the
  experimental geometry. This is a wrapper for DIALS' C++
  RayPredictor class, which does the real work. This class keeps track
  of the experimental geometry, and instantiates a RayPredictor when
  required.
  """

  def __init__(self, experiments, sweep_range=(0, 2.*pi)):
    """Construct by linking to instances of experimental model classes"""

    self._experiments = experiments
    self._sweep_range = sweep_range
    self.update()

  def update(self):
    """Build RayPredictor objects for the current geometry of each Experiment"""

    self._ray_predictors = [ScanStaticRayPredictor(e.beam.get_s0(),
      e.goniometer.get_rotation_axis(),
      self._sweep_range) for e in self._experiments]
    self._UBs = [e.crystal.get_U() * e.crystal.get_B() for e in self._experiments]

  def predict(self, hkl, experiment_id=0, UB=None):
    """
    Solve the prediction formula for the reflecting angle phi.

    If UB is given, override the contained crystal model. This is
    for use in refinement with time-varying crystal parameters
    """

    UB_ = UB if UB else self._UBs[experiment_id]

    rays = self._ray_predictors[experiment_id](hkl, UB_)

    return rays

class ExperimentsPredictor(object):
  """
  Predict for relps based on the current states of models of the experimental
  geometry. This version manages multiple experiments, selecting the correct
  predictor in each case.
  """

  def __init__(self, experiments, force_stills=False):
    """Construct by linking to instances of experimental model classes"""

    self._experiments = experiments
    self._force_stills = force_stills
    self.update()

  def update(self):
    """Build predictor objects for the current geometry of each Experiment"""

    sc = ScanStaticReflectionPredictor
    st = StillsReflectionPredictor
    if self._force_stills:
      self._predictors = [st(e) for e in self._experiments]
    else:
      self._predictors = [sc(e) if e.goniometer else st(e) \
                          for e in self._experiments]
    self._UBs = [e.crystal.get_U() * e.crystal.get_B() for e in self._experiments]

  def predict(self, reflections):
    """
    Predict for all reflections
    """

    for iexp, e in enumerate(self._experiments):

      # select the reflections for this experiment only
      sel = reflections['id'] == iexp
      refs = reflections.select(sel)

      try:
        # determine whether to try scan-varying prediction
        if refs.has_key('ub_matrix'):
          UBs = refs['ub_matrix']
          # predict and assign in place
          self._predictors[iexp].for_reflection_table(refs, UBs)
        else:
          # predict and assign in place
          self._predictors[iexp].for_reflection_table(refs, self._UBs[iexp])

        # write predictions back to overall reflections
        reflections.set_selected(sel, refs)
      except AssertionError:
        ### FIXME DEBUG: here have caught a rare error spotted by Aaron.
        ### Dump relevant objects now for easier debugging
        print "ERROR for experiment", iexp
        print "during attempt to call for_reflection_table"
        print "with UB matrix:"
        print self._UBs[iexp]
        print "saving reflections and experiments to disk"
        from dxtbx.model.experiment.experiment_list import ExperimentListDumper
        dump = ExperimentListDumper(self._experiments)
        dump.as_json("problematic_experiments.json")
        refs.as_pickle("problematic_reflections.json")
        raise

    return reflections

