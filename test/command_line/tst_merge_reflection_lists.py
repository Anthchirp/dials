
from __future__ import division


class Test(object):

  def __init__(self):
    from os.path import join
    from dials.array_family import flex
    import libtbx.load_env
    from dials.array_family import flex
    try:
      dials_regression = libtbx.env.dist_path('dials_regression')
    except KeyError, e:
      print 'FAIL: dials_regression not configured'
      exit(0)

    self.path = join(dials_regression, "centroid_test_data")

    table = flex.reflection_table()
    table['hkl'] = flex.miller_index(360)
    table['id'] = flex.size_t(360)
    table['intensity.sum.value'] = flex.double(360)
    table.as_pickle("temp.pickle")

  def run(self):
    from libtbx import easy_run
    from dials.array_family import flex

    # Call dials.merge_reflection_lists
    easy_run.fully_buffered([
      'dials.merge_reflection_lists',
      'temp.pickle',
      'temp.pickle',
      '-m', 'update'
    ]).raise_if_errors()

    table = flex.reflection_table.from_pickle('merged.pickle')
    assert(len(table) == 360)
    print 'OK'

    # Call dials.merge_reflection_lists
    easy_run.fully_buffered([
      'dials.merge_reflection_lists',
      'temp.pickle',
      'temp.pickle',
      '-m', 'extend'
    ]).raise_if_errors()

    table = flex.reflection_table.from_pickle('merged.pickle')
    assert(len(table) == 720)
    print 'OK'


if __name__ == '__main__':
  from dials.test import cd_auto
  with cd_auto(__file__):
    test = Test()
    test.run()
