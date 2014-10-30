#!/usr/bin/env cctbx.python

#
#  Copyright (C) (2014) STFC Rutherford Appleton Laboratory, UK.
#
#  Author: David Waterman.
#
#  This code is distributed under the BSD license, a copy of which is
#  included in the root directory of this package.
#

"""
Test multiple stills refinement.

"""

# python imports
from __future__ import division
import os
import shutil
import libtbx.load_env # required for libtbx.env.find_in_repositories
from libtbx import easy_run
from libtbx.test_utils import open_tmp_directory
from scitbx import matrix
from dxtbx.model.experiment.experiment_list import ExperimentListFactory

def test1():

  dials_regression = libtbx.env.find_in_repositories(
    relative_path="dials_regression",
    test=os.path.isdir)

  data_dir = os.path.join(dials_regression, "refinement_test_data",
                          "multi_stills")
  experiments_path = os.path.join(data_dir, "combined_experiments.json")
  reflections_path = os.path.join(data_dir, "combined_reflections.pickle")
  cmd = "dials.refine " + experiments_path + " " + reflections_path
  print cmd

  # work in a temporary directory
  cwd = os.path.abspath(os.curdir)
  tmp_dir = open_tmp_directory(suffix="tst_refine_multi_stills")
  os.chdir(tmp_dir)
  try:
    result = easy_run.fully_buffered(command=cmd).raise_if_errors()
    # load results
    reg_exp = ExperimentListFactory.from_json_file(
                os.path.join(data_dir, "regression_experiments.json"),
                check_format=False)
    ref_exp = ExperimentListFactory.from_json_file("refined_experiments.json",
                check_format=False)
  finally:
    os.chdir(cwd)
    # clean up tmp dir
    shutil.rmtree(tmp_dir)
  print "OK"

  for e1, e2 in zip(reg_exp, ref_exp):
    # test refined models against expected
    assert e1.crystal.is_similar_to(e2.crystal)
    assert e1.detector.is_similar_to(e2.detector)
    s0_1 = matrix.col(e1.beam.get_unit_s0())
    s0_2 = matrix.col(e1.beam.get_unit_s0())
    assert s0_1.accute_angle(s0_2, deg=True) < 0.0057 # ~0.1 mrad
  print "OK"

  return

def run():
  if not libtbx.env.has_module("dials_regression"):
    print "Skipping tests in " + __file__ + " as dials_regression not present"
    return

  test1()

if __name__ == '__main__':
  from libtbx.utils import show_times_at_exit
  show_times_at_exit()
  run()
