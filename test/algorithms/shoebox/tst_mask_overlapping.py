from __future__ import division

class Test(object):

  def __init__(self):
    import libtbx.load_env
    import os

    try:
      dials_regression = libtbx.env.dist_path('dials_regression')
    except KeyError, e:
      print 'FAIL: dials_regression not configured'
      exit(0)

    self.sweep_filename = os.path.join(dials_regression,
        'centroid_test_data', 'sweep.json')

    self.crystal_filename = os.path.join(dials_regression,
        'centroid_test_data', 'crystal.json')


  def run(self):
    from dials.model.serialize import load
    from dials.algorithms import shoebox
    from cctbx.crystal.crystal_model.serialize import load_crystal
    from dials.array_family import flex

    # Load the sweep and crystal
    self.sweep = load.sweep(self.sweep_filename)
    self.crystal = load_crystal(self.crystal_filename)

    # Get the reflections and overlaps
    reflections, adjacency_list = self.predict_reflections()
    reflections['shoebox'] = flex.shoebox(
      reflections['panel'],
      reflections['bbox'])
    reflections['shoebox'].allocate_with_value(shoebox.MaskCode.Valid)

    # If the adjacency list is given, then create the reflection mask
    assert(len(self.detector) == 1)
    image_size = self.detector[0].get_image_size()
    shoeboxes = reflections['shoebox']
    coords = reflections['xyzcal.px']
    shoebox_masker = shoebox.MaskOverlapping()
    shoebox_masker(shoeboxes, coords, adjacency_list)

    # Loop through all edges
    overlapping = []
    for e in adjacency_list.edges():
      v1, v2 = adjacency_list[e]
      overlapping.append(v1)
      overlapping.append(v2)

    # Ensure elements are unique
    overlapping = set(overlapping)

    # Ensure we have some overlaps
    assert(len(overlapping) > 0)

    # Get all non-overlapping reflections
    all_r = set(range(len(reflections)))
    non_overlapping = all_r.difference(overlapping)

    # Run the tests
    self.tst_non_overlapping(reflections, non_overlapping,
        self.detector[0].get_image_size())
    self.tst_overlapping(reflections, overlapping, adjacency_list,
        image_size)

  def tst_non_overlapping(self, reflections, non_overlapping, image_size):
    '''Ensure non-overlapping reflections have all their values 1.'''
    import numpy
    from dials.algorithms import shoebox

    # Check that all elements in non_overlapping masks are 1
    shoeboxes = reflections['shoebox']
    for i in non_overlapping:
      mask = shoeboxes[i].mask
      assert(mask.all_eq(shoebox.MaskCode.Valid))

    # Passed that test
    print "OK"

  def tst_overlapping(self, reflections, overlapping,
      adjacency_list, image_size):
    '''Ensure masks for overlapping reflections are set properly.'''
    import numpy
    from scitbx import matrix
    from dials.algorithms import shoebox

    # Loop through all overlaps
    shoeboxes = reflections['shoebox']
    coord = reflections['xyzcal.px']
    for i in overlapping:
      r1 = shoeboxes[i]
      bbox_1 = r1.bbox
      r1_coord = matrix.col(coord[i])

      # Create a mask that we expect
      r1_size = (bbox_1[5] - bbox_1[4],
                 bbox_1[3] - bbox_1[2],
                 bbox_1[1] - bbox_1[0])
      expected_mask = numpy.zeros(shape = r1_size, dtype=numpy.int32)
      expected_mask[:,:,:] = shoebox.MaskCode.Valid

      # Loop through all reflections which this reflection overlaps
      for j in adjacency_list.adjacent_vertices(i):
        r2 = shoeboxes[j]
        bbox_2 = r2.bbox
        r2_coord = matrix.col(coord[j])

        # Get bounding box of intersection
        bbox_3 = (max(bbox_1[0], bbox_2[0]), min(bbox_1[1], bbox_2[1]),
                  max(bbox_1[2], bbox_2[2]), min(bbox_1[3], bbox_2[3]),
                  max(bbox_1[4], bbox_2[4]), min(bbox_1[5], bbox_2[5]))

        # Check intersection is valid
        assert(bbox_3[0] < bbox_3[1])
        assert(bbox_3[2] < bbox_3[3])
        assert(bbox_3[4] < bbox_3[5])

        # Get the coordinates are all mask values
        mask_coord = []
        for k in range(bbox_3[4], bbox_3[5]):
          for j in range(bbox_3[2], bbox_3[3]):
            for i in range(bbox_3[0], bbox_3[1]):
              mask_coord.append(matrix.col((i+0.5, j+0.5, k+0.5)))

        dist = lambda a, m: numpy.array([(a - b).length() for b in m])

        # Find the indices in the intersection area where r2 is closer to
        # the point than r1
        ind = numpy.where(dist(r1_coord, mask_coord) >
                          dist(r2_coord, mask_coord))[0]

        # Set the mask values for r1 where r2 is closer to 0
        k0, k1 = bbox_3[4] - bbox_1[4], bbox_3[5] - bbox_1[4]
        j0, j1 = bbox_3[2] - bbox_1[2], bbox_3[3] - bbox_1[2]
        i0, i1 = bbox_3[0] - bbox_1[0], bbox_3[1] - bbox_1[0]
        intersect_mask = expected_mask[k0:k1, j0:j1, i0:i1]
        intersect_mask_1d = intersect_mask.reshape((-1))
        intersect_mask_1d[ind] = 0
        intersect_mask[:,:] = intersect_mask_1d.reshape(intersect_mask.shape)
        expected_mask[k0:k1, j0:j1, i0:i1] = intersect_mask

      # Check the masks are the same
      calculated_mask = r1.mask.as_numpy_array()
      assert(numpy.all(calculated_mask == expected_mask))

    # Passed the test
    print "OK"

  def predict_reflections(self):
    from dials.algorithms import shoebox
    from dials.algorithms import filtering
    from cctbx import sgtbx
    from math import sqrt
    from dials.array_family import flex
    from dials.model.data import ReflectionList
    from dials.model.experiment.experiment_list import ExperimentList
    from dials.model.experiment.experiment_list import Experiment

    # Get models from the sweep
    self.beam = self.sweep.get_beam()
    self.detector = self.sweep.get_detector()
    self.gonio = self.sweep.get_goniometer()
    self.scan = self.sweep.get_scan()

    exlist = ExperimentList()
    exlist.append(Experiment(
      imageset=self.sweep,
      beam=self.beam,
      detector=self.detector,
      goniometer=self.gonio,
      scan=self.scan,
      crystal=self.crystal))

    sigma_b = exlist[0].beam.get_sigma_divergence(deg=False)
    sigma_m = exlist[0].crystal.get_mosaicity(deg=False)

    predicted = flex.reflection_table.from_predictions(exlist)
    predicted.compute_bbox(exlist[0], 5, sigma_b, sigma_m)


    # Find overlapping reflections
    overlaps = shoebox.find_overlapping(predicted['bbox'])

    # Return the reflections and overlaps
    return predicted, overlaps

if __name__ == '__main__':
  test = Test()
  test.run()
