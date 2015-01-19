from __future__ import division

def run():
  import os
  import libtbx.load_env
  from libtbx import easy_run
  from libtbx.test_utils import show_diff
  try:
    dials_regression = libtbx.env.dist_path('dials_regression')
  except KeyError, e:
    print 'FAIL: dials_regression not configured'
    exit(0)

  path = os.path.join(dials_regression, "refinement_test_data", "i04_weak_data")
  cmd = "dials.compare_orientation_matrices %s/experiments.json %s/regression_experiments.json" %(path, path)
  result = easy_run.fully_buffered(cmd).raise_if_errors()
  assert not show_diff("\n".join(result.stdout_lines[7:]), """\
Rotation matrix to transform crystal 1 to crystal 2
{{1.000, -0.000, 0.000},
 {0.000, 1.000, -0.000},
 {-0.000, 0.000, 1.000}}
Euler angles (xyz): 0.00, 0.00, 0.00
""")


if __name__ == '__main__':
  from dials.test import cd_auto
  with cd_auto(__file__):
    run()
    print "OK"
