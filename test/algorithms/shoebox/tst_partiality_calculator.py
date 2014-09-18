from __future__ import division

class Test(object):

  def __init__(self):
    from math import pi

    import libtbx.load_env
    try:
      dials_regression = libtbx.env.dist_path( 'dials_regression' )
    except KeyError, e:
      print 'FAIL: dials_regression not configured'
      exit(0)

    import os

    filename = os.path.join(dials_regression,
        'centroid_test_data', 'fake_long_experiments.json')

    from dxtbx.model.experiment.experiment_list import ExperimentListFactory
    exlist = ExperimentListFactory.from_json_file(filename)
    assert(len(exlist) == 1)
    self.experiment = exlist[0]

    # Set the delta_divergence/mosaicity
    self.n_sigma = 5
    self.sigma_b = 0.060 * pi / 180
    self.sigma_m = 0.154 * pi / 180
    self.delta_m = self.n_sigma * self.sigma_m

    from dials.algorithms.profile_model.gaussian_rs import ProfileModel
    self.profile_model = ProfileModel(self.n_sigma, self.sigma_b, self.sigma_m)

  def run(self):
    from dials.algorithms.profile_model.gaussian_rs import \
      PartialityCalculator3D
    from dials.array_family import flex

    calculator = PartialityCalculator3D(
      self.experiment.beam,
      self.experiment.goniometer,
      self.experiment.scan,
      self.delta_m)

    predicted = flex.reflection_table.from_predictions(self.experiment)
    predicted.compute_bbox(self.experiment, self.profile_model)

    # Remove any touching edges of scan to get only fully recorded
    x0, x1, y0, y1, z0, z1 = predicted['bbox'].parts()
    predicted = predicted.select((z0 > 0) & (z1 < 100))
    assert(len(predicted) > 0)

    # Compute partiality
    partiality = calculator(
      predicted['s1'],
      predicted['xyzcal.px'].parts()[2],
      predicted['bbox'])

    # Should have all fully recorded
    assert(len(partiality) == len(predicted))
    assert(partiality.all_gt(1.0 - 1e-7))

    # Trim bounding boxes
    x0, x1, y0, y1, z0, z1 = predicted['bbox'].parts()
    z0 = z0 + 1
    z1 = z1 - 1
    predicted['bbox'] = flex.int6(x0, x1, y0, y1, z0, z1)
    predicted = predicted.select(z1 > z0)
    assert(len(predicted) > 0)

    # Compute partiality
    partiality = calculator(
      predicted['s1'],
      predicted['xyzcal.px'].parts()[2],
      predicted['bbox'])

    # Should have all partials
    assert(len(partiality) == len(predicted))
    assert(partiality.all_lt(1.0) and partiality.all_gt(0))

    print 'OK'

if __name__ == '__main__':
  test = Test()
  test.run()
