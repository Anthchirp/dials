#!/usr/bin/env python

#
#  Copyright (C) (2014) STFC Rutherford Appleton Laboratory, UK.
#
#  Author: David Waterman.
#
#  This code is distributed under the BSD license, a copy of which is
#  included in the root directory of this package.
#

from __future__ import division

#### Python and general cctbx imports

import sys
from cctbx.sgtbx import space_group, space_group_symbols
from libtbx.phil import parse
from scitbx.math import five_number_summary

#### dials imports
from dials.array_family import flex

##### Import model builder

from setup_geometry import Extract

##### Imports for reflection prediction

from dials.algorithms.spot_prediction import IndexGenerator
from dxtbx.model.experiment.experiment_list import ExperimentList, Experiment
from dials.algorithms.refinement.prediction import ScansRayPredictor

#### Import model parameterisations

from dials.algorithms.refinement.parameterisation.prediction_parameters_stills \
  import StillsPredictionParameterisation

from dials.algorithms.refinement.parameterisation.detector_parameters import \
    DetectorParameterisationSinglePanel
from dials.algorithms.refinement.parameterisation.beam_parameters import \
    BeamParameterisation
from dials.algorithms.refinement.parameterisation.crystal_parameters import \
    CrystalOrientationParameterisation, \
    CrystalUnitCellParameterisation

def run(verbose = False):
  #### Create models

  # build models, with a larger crystal than default in order to get plenty of
  # reflections on the 'still' image
  overrides = """
  geometry.parameters.crystal.a.length.range=40 50;
  geometry.parameters.crystal.b.length.range=40 50;
  geometry.parameters.crystal.c.length.range=40 50;
  geometry.parameters.random_seed = 42"""

  master_phil = parse("""
      include scope dials.test.algorithms.refinement.geometry_phil
      """, process_includes=True)

  models = Extract(master_phil, overrides)

  mydetector = models.detector
  mygonio = models.goniometer
  mycrystal = models.crystal
  mybeam = models.beam

  # Build a mock scan for a 3 degree sweep
  from dxtbx.model.scan import scan_factory
  sf = scan_factory()
  myscan = sf.make_scan(image_range = (1,1),
                        exposure_times = 0.1,
                        oscillation = (0, 3.0),
                        epochs = range(1),
                        deg = True)
  sweep_range = myscan.get_oscillation_range(deg=False)

  #### Create parameterisations of these models

  det_param = DetectorParameterisationSinglePanel(mydetector)
  s0_param = BeamParameterisation(mybeam, mygonio)
  xlo_param = CrystalOrientationParameterisation(mycrystal)
  xluc_param = CrystalUnitCellParameterisation(mycrystal)

  # Create a scans ExperimentList, only for generating reflections
  experiments = ExperimentList()
  experiments.append(Experiment(
        beam=mybeam, detector=mydetector, goniometer=mygonio, scan=myscan,
        crystal=mycrystal, imageset=None))

  # Create a stills ExperimentList
  stills_experiments = ExperimentList()
  stills_experiments.append(Experiment(
        beam=mybeam, detector=mydetector, crystal=mycrystal, imageset=None))

  #### Generate reflections

  # Create a ScansRayPredictor
  ray_predictor = ScansRayPredictor(experiments, sweep_range)

  # Generate rays
  resolution = 2.0
  index_generator = IndexGenerator(mycrystal.get_unit_cell(),
                        space_group(space_group_symbols(1).hall()).type(),
                        resolution)
  indices = index_generator.to_array()
  rays = ray_predictor.predict(indices)

  # Make a standard reflection_table and copy in the ray data
  reflections = flex.reflection_table.empty_standard(len(rays))
  reflections.update(rays)

  # Build a prediction parameterisation for the stills experiment
  pred_param = StillsPredictionParameterisation(stills_experiments,
                 detector_parameterisations = [det_param],
                 beam_parameterisations = [s0_param],
                 xl_orientation_parameterisations = [xlo_param],
                 xl_unit_cell_parameterisations = [xluc_param])

  # use a ReflectionManager to keep track of predictions
  from dials.algorithms.refinement.reflection_manager import \
    StillsReflectionManager
  refman = StillsReflectionManager(reflections, stills_experiments,
                                   iqr_multiplier=None)

  # Make a reflection predictor of the type expected by the Target class
  from dials.algorithms.refinement.prediction import ExperimentsPredictor
  ref_predictor = ExperimentsPredictor(stills_experiments)

  # Make a target to ensure reflections are predicted with the stills predictor.
  # This sets the "delpsical.rad" column.
  from dials.algorithms.refinement.target_stills import \
    LeastSquaresStillsResidualWithRmsdCutoff
  target = LeastSquaresStillsResidualWithRmsdCutoff(stills_experiments,
      ref_predictor, refman, pred_param)

  # get predictions from the reflection manager
  reflections = refman.get_matches()

  # get analytical gradients
  an_grads = pred_param.get_gradients(reflections)

  # get finite difference gradients
  p_vals = pred_param.get_param_vals()
  deltas = [1.e-7] * len(p_vals)

  p_names = pred_param.get_param_names()
  for i in range(len(deltas)):

    # save parameter value
    val = p_vals[i]

    # calc reverse state
    p_vals[i] -= deltas[i] / 2.
    pred_param.set_param_vals(p_vals)

    ref_predictor.update()
    ref_predictor.predict(reflections)

    x, y, _ = reflections['xyzcal.mm'].deep_copy().parts()
    delpsi = reflections['delpsical.rad'].deep_copy()
    rev_state = flex.vec3_double(x, y, delpsi)

    # calc forward state
    p_vals[i] += deltas[i]
    pred_param.set_param_vals(p_vals)

    ref_predictor.update()
    ref_predictor.predict(reflections)

    x, y, _ = reflections['xyzcal.mm'].deep_copy().parts()
    delpsi = reflections['delpsical.rad'].deep_copy()
    fwd_state = flex.vec3_double(x, y, delpsi)

    # reset parameter to saved value
    p_vals[i] = val

    # finite difference
    fd = (fwd_state - rev_state)
    x_grads, y_grads, delpsi_grads = fd.parts()
    x_grads /= deltas[i]
    y_grads /= deltas[i]
    delpsi_grads /= deltas[i]

    # compare FD with analytical calculations
    if verbose: print "\n\nParameter {0}: {1}". format(i,  p_names[i])
    grads = (x_grads, y_grads, delpsi_grads)

    for idx, name in enumerate(["dX_dp", "dY_dp", "dDeltaPsi_dp"]):
      if verbose: print name
      a = grads[idx]
      b = an_grads[i][name]

      abs_error = a - b
      denom = a + b

      fns = five_number_summary(abs_error)
      if verbose: print ("  summary of absolute errors: %9.6f %9.6f %9.6f " + \
        "%9.6f %9.6f") % fns
      assert flex.max(flex.abs(abs_error)) < 0.0003
      # largest absolute error found to be about 0.00025 for dY/dp of
      # Crystal0g_param_3. Reject outlying absolute errors and test again.
      iqr = fns[3] - fns[1]

      # skip further stats on errors with an iqr of near zero, e.g. dDeltaPsi_dp
      # for detector parameters, which are all equal to zero
      if iqr < 1.e-10:
        continue

      sel1 = abs_error < fns[3] + 1.5 * iqr
      sel2 = abs_error > fns[1] - 1.5 * iqr
      sel = sel1 & sel2
      tst = flex.max_index(flex.abs(abs_error.select(sel)))
      tst_val = abs_error.select(sel)[tst]
      n_outliers = sel.count(False)
      if verbose: print ("  {0} outliers rejected, leaving greatest " + \
        "absolute error: {1:9.6f}").format(n_outliers, tst_val)
      # largest absolute error now 0.000062 for dX/dp of Crystal0g_param_3
      assert abs(tst_val) < 0.00007

      # Completely skip parameters with FD gradients all zero (e.g. gradients of
      # DeltaPsi for detector parameters)
      sel1 = flex.abs(a) < 1.e-10
      if sel1.all_eq(True):
        continue

      # otherwise calculate normalised errors, by dividing absolute errors by
      # the IQR (more stable than relative error calculation)
      norm_error = abs_error / iqr
      fns = five_number_summary(norm_error)
      if verbose: print ("  summary of normalised errors: %9.6f %9.6f %9.6f " + \
        "%9.6f %9.6f") % fns
      # largest normalised error found to be about 25.7 for dY/dp of
      # Crystal0g_param_3.
      try:
        assert flex.max(flex.abs(norm_error)) < 30
      except AssertionError as e:
        e.args += ("extreme normalised error value: {0}".format(
                   flex.max(flex.abs(norm_error))),)
        raise e

      # Reject outlying normalised errors and test again
      iqr = fns[3] - fns[1]
      if iqr > 0.:
        sel1 = norm_error < fns[3] + 1.5 * iqr
        sel2 = norm_error > fns[1] - 1.5 * iqr
        sel = sel1 & sel2
        tst = flex.max_index(flex.abs(norm_error.select(sel)))
        tst_val = norm_error.select(sel)[tst]
        n_outliers = sel.count(False)

        # most outliers found for for dY/dp of Crystal0g_param_3 (which had
        # largest errors, so no surprise there).
        try:
          assert n_outliers < 250
        except AssertionError as e:
          e.args += ("too many outliers rejected: {0}".format(n_outliers),)
          raise e

        if verbose: print ("  {0} outliers rejected, leaving greatest " + \
          "normalised error: {1:9.6f}").format(n_outliers, tst_val)
        # largest normalied error now about -4. for dX/dp of Detector0Tau1
        assert abs(tst_val) < 4.5

  # return to the initial state
  pred_param.set_param_vals(p_vals)

if __name__ == "__main__":

  # switch this to true to see summary output
  run(verbose=False)

  # In comparison with FD approximations, the worst gradients by far are dX/dp
  # and dY/dp for parameter Crystal0g_param_3. Is this to do with the geometry
  # of the test case?
  print "OK"
