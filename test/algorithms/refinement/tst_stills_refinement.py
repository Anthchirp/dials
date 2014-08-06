#!/usr/bin/env cctbx.python

#
#  Copyright (C) (2013) STFC Rutherford Appleton Laboratory, UK.
#
#  Author: David Waterman.
#
#  This code is distributed under the BSD license, a copy of which is
#  included in the root directory of this package.
#

"""
A simple test of stills refinement using fake data.
Only the crystal is perturbed while the beam and detector are known.

"""

# Python and cctbx imports
from __future__ import division
import sys
from math import pi
from scitbx import matrix
from libtbx.phil import parse
from libtbx.test_utils import approx_equal

# Get modules to build models and minimiser using PHIL
import setup_geometry
import setup_minimiser

# We will set up a mock scan and a mock experiment list
from dxtbx.model.scan import scan_factory
from dxtbx.model.experiment.experiment_list import ExperimentList, Experiment

# Model parameterisations
from dials.algorithms.refinement.parameterisation.detector_parameters import \
    DetectorParameterisationSinglePanel
from dials.algorithms.refinement.parameterisation.beam_parameters import \
    BeamParameterisation
from dials.algorithms.refinement.parameterisation.crystal_parameters import \
    CrystalOrientationParameterisation, CrystalUnitCellParameterisation

# Symmetry constrained parameterisation for the unit cell
from cctbx.uctbx import unit_cell
from rstbx.symmetry.constraints.parameter_reduction import \
    symmetrize_reduce_enlarge

# Reflection prediction
from dials.algorithms.spot_prediction import IndexGenerator
from dials.algorithms.refinement.prediction import ScansRayPredictor
from dials.algorithms.spot_prediction import ray_intersection
from cctbx.sgtbx import space_group, space_group_symbols

#############################
# Setup experimental models #
#############################

args = sys.argv[1:]
master_phil = parse("""
    include scope dials.test.algorithms.refinement.geometry_phil
    include scope dials.test.algorithms.refinement.minimiser_phil
    """, process_includes=True)

# build models, with a larger crystal than default in order to get enough
# reflections on the 'still' image
param = """
geometry.parameters.crystal.a.length.range=40 50;
geometry.parameters.crystal.b.length.range=40 50;
geometry.parameters.crystal.c.length.range=40 50;
geometry.parameters.random_seed = 42"""
models = setup_geometry.Extract(master_phil, cmdline_args = args,
                        local_overrides=param)

crystal = models.crystal
mydetector = models.detector
mygonio = models.goniometer
mybeam = models.beam

# Build a mock scan for a 1.5 degree wedge. Only used for generating indices near
# the Ewald sphere
sf = scan_factory()
myscan = sf.make_scan(image_range = (1,1),
                      exposure_times = 0.1,
                      oscillation = (0, 1.5),
                      epochs = range(1),
                      deg = True)
sweep_range = myscan.get_oscillation_range(deg=False)
temp = myscan.get_oscillation(deg=False)
im_width = temp[1] - temp[0]
assert approx_equal(im_width, 1.5 * pi / 180.)

# Build experiment lists
stills_experiments = ExperimentList()
stills_experiments.append(Experiment(
      beam=mybeam, detector=mydetector, crystal=crystal, imageset=None))
scans_experiments = ExperimentList()
scans_experiments.append(Experiment(
      beam=mybeam, detector=mydetector, crystal=crystal, goniometer = mygonio,
      scan=myscan, imageset=None))

##########################################################
# Parameterise the models (only for perturbing geometry) #
##########################################################

xlo_param = CrystalOrientationParameterisation(crystal)
xluc_param = CrystalUnitCellParameterisation(crystal)

################################
# Apply known parameter shifts #
################################

# rotate crystal (=5 mrad each rotation)
xlo_p_vals = []
p_vals = xlo_param.get_param_vals()
xlo_p_vals.append(p_vals)
new_p_vals = [a + b for a, b in zip(p_vals, [5., 5., 5.])]
xlo_param.set_param_vals(new_p_vals)

# change unit cell (=1.0 Angstrom length upsets, 0.5 degree of
# gamma angle)
xluc_p_vals = []
p_vals = xluc_param.get_param_vals()
xluc_p_vals.append(p_vals)
cell_params = crystal.get_unit_cell().parameters()
cell_params = [a + b for a, b in zip(cell_params, [1.0, 1.0, -1.0, 0.0,
                                                   0.0, 0.5])]
new_uc = unit_cell(cell_params)
newB = matrix.sqr(new_uc.fractionalization_matrix()).transpose()
S = symmetrize_reduce_enlarge(crystal.get_space_group())
S.set_orientation(orientation=newB)
X = tuple([e * 1.e5 for e in S.forward_independent_parameters()])
xluc_param.set_param_vals(X)

# keep track of the target crystal model to compare with refined
from copy import deepcopy
target_crystal = deepcopy(crystal)

#############################
# Generate some reflections #
#############################

# All indices in a 2.0 Angstrom sphere for crystal
resolution = 2.0
index_generator = IndexGenerator(crystal.get_unit_cell(),
                space_group(space_group_symbols(1).hall()).type(), resolution)
indices = index_generator.to_array()

# Build a ray predictor and predict rays close to the Ewald sphere by using
# the narrow rotation scan
ref_predictor = ScansRayPredictor(scans_experiments, sweep_range)
obs_refs = ref_predictor.predict(indices, experiment_id=0)

# Invent some variances for the centroid positions of the simulated data
im_width = 0.1 * pi / 180.
px_size = mydetector[0].get_pixel_size()
var_x = (px_size[0] / 2.)**2
var_y = (px_size[1] / 2.)**2
var_phi = (im_width / 2.)**2

for ref in obs_refs:

  # set the centroid variance
  ref.centroid_variance = (var_x, var_y, var_phi)

  # ensure the crystal number is set to zero (should be by default)
  ref.crystal = 0

# Build a stills reflection predictor
from dials.algorithms.refinement.prediction import ExperimentsPredictor
stills_ref_predictor = ExperimentsPredictor(stills_experiments)

obs_refs_stills = obs_refs.to_table(centroid_is_mm=True)
stills_ref_predictor.update()
obs_refs_stills = stills_ref_predictor.predict(obs_refs_stills)

# set the calculated centroids as the 'observations'
for iref, ref in enumerate(obs_refs_stills):
  obs_refs_stills[iref] = {'xyzobs.mm.value': ref['xyzcal.mm']}

###############################
# Undo known parameter shifts #
###############################

xlo_param.set_param_vals(xlo_p_vals[0])
xluc_param.set_param_vals(xluc_p_vals[0])

# make a refiner
from dials.framework.registry import Registry
sysconfig = Registry().config()
params = sysconfig.params()

# Change this to get a plot
do_plot = False
if do_plot: params.refinement.refinery.track_parameter_correlation=True

from dials.algorithms.refinement.refiner import RefinerFactory
# decrease bin_size_fraction to terminate on RMSD convergence
params.refinement.target.bin_size_fraction=0.01
params.refinement.parameterisation.beam.fix="all"
params.refinement.parameterisation.detector.fix="all"
refiner = RefinerFactory.from_parameters_data_experiments(params,
  obs_refs_stills, stills_experiments, verbosity=0)

# run refinement
history = refiner.run()

# regression tests
assert len(history.rmsd) == 9
refined_crystal = refiner.get_experiments()[0].crystal
uc1 = refined_crystal.get_unit_cell()
uc2 = target_crystal.get_unit_cell()
assert uc1.is_similar_to(uc2)

if do_plot:
  plt = refiner.parameter_correlation_plot(len(history.parameter_correlation)-1)
  plt.show()

print "OK"

