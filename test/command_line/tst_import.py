from __future__ import division

class Test(object):
  def __init__(self):
    from os.path import join
    import libtbx.load_env
    try:
      dials_regression = libtbx.env.dist_path('dials_regression')
    except KeyError, e:
      print 'FAIL: dials_regression not configured'
      exit(0)

    self.path = join(dials_regression, "centroid_test_data")

  def run(self):
    self.tst_from_image_files()
    self.tst_from_xds_files()

  def tst_from_image_files(self):
    from subprocess import call
    from glob import glob
    import difflib
    from os.path import join, exists

    # Find the image files
    image_files = glob(join(self.path, "centroid*.cbf"))
    image_files = ' '.join(image_files)

    # Import from the image files
    call('dials.import %s -o import_datablock.json > /dev/null' % image_files, shell=True)

    # Get the expected output
    #expected = self.expected_import_from_image_files()

    assert(exists("import_datablock.json"))
    ## Read the created file and do a diff
    #with open("datablock.json", "r") as infile:
      #lines_a = infile.read().splitlines()
      #lines_a = [l.strip() for l in lines_a if "\"template\"" not in l]
      #diff = list(difflib.context_diff(
        #lines_a,
        #[l.strip() for l in expected.splitlines()]))
      #n = len(diff)
      #for i, line in enumerate(diff):
        #print line
      #assert(n == 0)

    print 'OK'

  def tst_from_xds_files(self):
    from subprocess import call
    import difflib
    from os.path import join, abspath, exists
    from os import chdir

    # Import from the image files
    path = abspath(self.path)
    chdir(path)
    call('dials.import --xds=./ -o import_experiments.json > /dev/null', shell=True)

    assert(exists("import_experiments.json"))

    # Get the expected output
    #expected = self.expected_import_from_xds_files()

    ## Read the created file and do a diff
    #with open("experiments.json", "r") as infile:
      #lines_a = infile.read().splitlines()
      #lines_a = [l.strip() for l in lines_a if "\"template\"" not in l]
      #diff = list(difflib.context_diff(
        #lines_a,
        #[l.strip() for l in expected.splitlines()]))
      #n = len(diff)
      #for i, line in enumerate(diff):
        #print line
      #assert(n == 0)

    print 'OK'

  #def expected_import_from_image_files(self):
    #return '''[
  #{
    #"__id__": "DataBlock",
    #"imageset": [
      #{
        #"__id__": "ImageSweep",
        #"beam": 0,
        #"detector": 0,
        #"goniometer": 0,
        #"scan": 0
      #}
    #],
    #"beam": [
      #{
        #"direction": [
          #0.0,
          #0.0,
          #1.0
        #],
        #"polarization_normal": [
          #0.0,
          #1.0,
          #0.0
        #],
        #"divergence": 0.0,
        #"polarization_fraction": 0.999,
        #"sigma_divergence": 0.0,
        #"wavelength": 0.9795
      #}
    #],
    #"detector": [
      #{
        #"panels": [
          #{
            #"origin": [
              #-212.47848,
              #220.00176,
              #-190.17999999999998
            #],
            #"fast_axis": [
              #1.0,
              #0.0,
              #0.0
            #],
            #"name": "Panel",
            #"slow_axis": [
              #0.0,
              #-1.0,
              #0.0
            #],
            #"mask": [
              #[
                #488,
                #1,
                #494,
                #2527
              #],
              #[
                #982,
                #1,
                #988,
                #2527
              #],
              #[
                #1476,
                #1,
                #1482,
                #2527
              #],
              #[
                #1970,
                #1,
                #1976,
                #2527
              #],
              #[
                #1,
                #196,
                #2463,
                #212
              #],
              #[
                #1,
                #408,
                #2463,
                #424
              #],
              #[
                #1,
                #620,
                #2463,
                #636
              #],
              #[
                #1,
                #832,
                #2463,
                #848
              #],
              #[
                #1,
                #1044,
                #2463,
                #1060
              #],
              #[
                #1,
                #1256,
                #2463,
                #1272
              #],
              #[
                #1,
                #1468,
                #2463,
                #1484
              #],
              #[
                #1,
                #1680,
                #2463,
                #1696
              #],
              #[
                #1,
                #1892,
                #2463,
                #1908
              #],
              #[
                #1,
                #2104,
                #2463,
                #2120
              #],
              #[
                #1,
                #2316,
                #2463,
                #2332
              #]
            #],
            #"trusted_range": [
              #-1.0,
              #495976.0
            #],
            #"image_size": [
              #2463,
              #2527
            #],
            #"px_mm_strategy": {
              #"type": "ParallaxCorrectedPxMmStrategy"
            #},
            #"type": "SENSOR_PAD",
            #"pixel_size": [
              #0.17200000000000001,
              #0.17200000000000001
            #]
          #}
        #]
      #}
    #],
    #"goniometer": [
      #{
        #"fixed_rotation": [
          #1.0,
          #0.0,
          #0.0,
          #0.0,
          #1.0,
          #0.0,
          #0.0,
          #0.0,
          #1.0
        #],
        #"rotation_axis": [
          #1.0,
          #0.0,
          #0.0
        #]
      #}
    #],
    #"scan": [
      #{
        #"exposure_time": [
          #0.2,
          #0.2,
          #0.2,
          #0.2,
          #0.2,
          #0.2,
          #0.2,
          #0.2,
          #0.2
        #],
        #"epochs": [
          #1360324992.0,
          #1360324992.0,
          #1360324993.0,
          #1360324993.0,
          #1360324993.0,
          #1360324993.0,
          #1360324993.0,
          #1360324994.0,
          #1360324994.0
        #],
        #"image_range": [
          #1,
          #9
        #],
        #"oscillation": [
          #0.0,
          #0.2
        #]
      #}
    #]
  #}
#]'''

  #def expected_import_from_xds_files(self):
    #return '''{
  #"__id__": "ExperimentList",
  #"experiment": [
    #{
      #"__id__": "Experiment",
      #"beam": 0,
      #"detector": 0,
      #"goniometer": 0,
      #"scan": 0,
      #"crystal": 0,
      #"imageset": 0
    #}
  #],
  #"imageset": [
    #{
      #"__id__": "ImageSweep",
    #}
  #],
  #"beam": [
    #{
      #"direction": [
        #-0.007852057721998333,
        #3.772524827250213e-14,
        #0.9999691721195861
      #],
      #"polarization_normal": [
        #0.0,
        #1.0,
        #0.0
      #],
      #"divergence": 0.0,
      #"polarization_fraction": 0.999,
      #"sigma_divergence": 0.058,
      #"wavelength": 0.9795
    #}
  #],
  #"detector": [
    #{
      #"panels": [
        #{
          #"origin": [
            #-211.53596470096178,
            #219.45303890619488,
            #-192.7062494437063
          #],
          #"fast_axis": [
            #0.9999551354884303,
            #0.0021159302715049923,
            #0.009233084500921031
          #],
          #"name": "Panel",
          #"slow_axis": [
            #0.0021250002879257116,
            #-0.999997269169901,
            #-0.0009726389448611214
          #],
          #"mask": [],
          #"trusted_range": [
            #0.0,
            #0.0
          #],
          #"image_size": [
            #2463,
            #2527
          #],
          #"px_mm_strategy": {
            #"type": "ParallaxCorrectedPxMmStrategy"
          #},
          #"type": "SENSOR_UNKNOWN",
          #"pixel_size": [
            #0.172,
            #0.172
          #]
        #}
      #]
    #}
  #],
  #"goniometer": [
    #{
      #"fixed_rotation": [
        #1.0,
        #0.0,
        #0.0,
        #0.0,
        #1.0,
        #0.0,
        #0.0,
        #0.0,
        #1.0
      #],
      #"rotation_axis": [
        #1.0,
        #-1.5919306617286774e-16,
        #-6.904199434387693e-16
      #]
    #}
  #],
  #"scan": [
    #{
      #"exposure_time": [
        #0.2,
        #0.2,
        #0.2,
        #0.2,
        #0.2,
        #0.2,
        #0.2,
        #0.2,
        #0.2
      #],
      #"epochs": [
        #1360324992.0,
        #1360324992.0,
        #1360324993.0,
        #1360324993.0,
        #1360324993.0,
        #1360324993.0,
        #1360324993.0,
        #1360324994.0,
        #1360324994.0
      #],
      #"image_range": [
        #1,
        #9
      #],
      #"oscillation": [
        #0.0,
        #0.2
      #]
    #}
  #],
  #"crystal": [
    #{
      #"__id__": "crystal",
      #"real_space_a": [
        #35.23781811553089,
        #-7.600614003857873,
        #22.077690418635804
      #],
      #"real_space_b": [
        #-22.657129890916668,
        #-1.4698317405529955,
        #35.65693038892429
      #],
      #"real_space_c": [
        #-5.295803077552249,
        #-38.99952334925477,
        #-4.972795822746061
      #],
      #"space_group_hall_symbol": " P 4 2",
      #"mosaicity": 0.157
    #}
  #]
#}'''

if __name__ == '__main__':
  test = Test()
  test.run()
