#!/usr/bin/env python
#
# export_mosflm.py
#
#  Copyright (C) 2014 Diamond Light Source
#
#  Author: Richard Gildea
#
#  This code is distributed under the BSD license, a copy of which is
#  included in the root directory of this package.
from __future__ import division

import math
import os
from scitbx import matrix
from dxtbx.model.crystal import crystal_model
from dials.util.options import OptionParser
from dials.util.options import flatten_reflections
from dials.util.options import flatten_datablocks
from dials.util.options import flatten_experiments

help_message = '''

This program exports an experiments.json file as an index.mat mosflm-format
matrix file and a mosflm.in file containing basic instructions for input
to mosflm.

Examples::

  dials.export_mosflm experiments.json

'''

def run(args):
  import libtbx.load_env
  from libtbx.utils import Sorry
  usage = "%s [options] experiments.json" %libtbx.env.dispatcher_name

  parser = OptionParser(
    usage=usage,
    read_experiments=True,
    check_format=False,
    epilog=help_message
  )

  params, options = parser.parse_args(show_diff_phil=True)
  experiments = flatten_experiments(params.input.experiments)

  if len(experiments) == 0:
    parser.print_help()
    return

  for i in range(len(experiments)):
    suffix = ""
    if len(experiments) > 1:
      suffix = "_%i" %(i+1)

    sub_dir = "mosflm%s" %suffix
    if not os.path.isdir(sub_dir):
      os.makedirs(sub_dir)
    detector = experiments[i].detector
    beam = experiments[i].beam
    scan = experiments[i].scan
    goniometer = experiments[i].goniometer

    # XXX imageset is getting the experimental geometry from the image files
    # rather than the input experiments.json file
    imageset = experiments[i].imageset

    from rstbx.cftbx.coordinate_frame_helpers import align_reference_frame
    R_to_mosflm = align_reference_frame(
      beam.get_s0(), (1.0, 0.0, 0.0),
      goniometer.get_rotation_axis(), (0.0, 0.0, 1.0))
    #print R_to_mosflm

    cryst = experiments[i].crystal
    cryst = cryst.change_basis(
      cryst.get_space_group().info()\
        .change_of_basis_op_to_reference_setting())
    A = cryst.get_A()
    A_inv = A.inverse()

    real_space_a = R_to_mosflm * A_inv.elems[:3]
    real_space_b = R_to_mosflm * A_inv.elems[3:6]
    real_space_c = R_to_mosflm * A_inv.elems[6:9]

    cryst_mosflm = crystal_model(
      real_space_a, real_space_b, real_space_c,
      space_group=cryst.get_space_group(),
      mosaicity=cryst.get_mosaicity())
    A_mosflm = cryst_mosflm.get_A()
    U_mosflm = cryst_mosflm.get_U()
    assert U_mosflm.is_r3_rotation_matrix(), U_mosflm
    w = beam.get_wavelength()

    index_mat = os.path.join(sub_dir, "index.mat")
    mosflm_in = os.path.join(sub_dir, "mosflm.in")
    print "Exporting experiment to %s and %s" %(index_mat, mosflm_in)

    with open(index_mat, "wb") as f:
      print >> f, format_mosflm_mat(w*A_mosflm, U_mosflm, cryst.get_unit_cell())

    directory, template = os.path.split(imageset.get_template())
    symmetry = cryst_mosflm.get_space_group().type().number()
    beam_centre = tuple(reversed(detector[0].get_beam_centre(beam.get_s0())))
    distance = detector[0].get_distance()

    with open(mosflm_in, "wb") as f:
      print >> f, write_mosflm_input(directory=directory,
                                     template=template,
                                     symmetry=symmetry,
                                     beam_centre=beam_centre,
                                     distance=distance,
                                     mat_file="index.mat")

  return


def format_mosflm_mat(A, U, unit_cell, missets=(0,0,0)):
  lines = []
  uc_params = unit_cell.parameters()
  for i in range(3):
    lines.append(("%12.8f" * 3) %A.elems[i*3:3*(i+1)])
  lines.append(("%12.3f" * 3) %missets)
  for i in range(3):
    lines.append("%12.8f"*3 %U.elems[i*3:3*(i+1)])
  lines.append(("%12.4f" * 6) %uc_params)
  lines.append(("%12.3f" * 3) %missets)
  return "\n".join(lines)


def write_mosflm_input(directory=None, template=None,
                       symmetry=None,
                       beam_centre=None, distance=None,
                       mat_file=None):
  lines = []
  if directory is not None:
    lines.append("DIRECTORY %s" %directory)
  if template is not None:
    lines.append("TEMPLATE %s" %template)
  if symmetry is not None:
    lines.append("SYMMETRY %s" %symmetry)
  if beam_centre is not None:
    lines.append("BEAM %.3f %.3f" %beam_centre)
  if distance is not None:
    lines.append("DISTANCE %.4f" %distance)
  if mat_file is not None:
    lines.append("MATRIX %s" %mat_file)
  return "\n".join(lines)



if __name__ == '__main__':
  import sys
  run(sys.argv[1:])
