

class CentroidTest(object):

    EPS = 1e-7

    def __init__(self):
        self.generate_data()
        self.calculate_gold()

    def run(self):
        self.tst_centroid_points()
        self.tst_centroid_image()
        self.tst_centroid_masked_image()

    def tst_centroid_points(self):
        self.tst_centroid_points2d()
        self.tst_centroid_points3d()

    def tst_centroid_points2d(self):
        from dials.algorithms.image.centroid import CentroidPoints2d
        from scitbx import matrix

        centroid = CentroidPoints2d(self.pixels2d, self.points2d)

        assert(abs(self.gold2d - matrix.col(centroid.mean())) < self.EPS)
        assert(abs(self.gold2dvar - matrix.col(centroid.variance())) < self.EPS)
        print 'OK'

    def tst_centroid_points3d(self):
        from dials.algorithms.image.centroid import CentroidPoints3d
        from scitbx import matrix

        centroid = CentroidPoints3d(self.pixels3d, self.points3d)

        assert(abs(self.gold3d - matrix.col(centroid.mean())) < self.EPS)
        assert(abs(self.gold3dvar - matrix.col(centroid.variance())) < self.EPS)
        print 'OK'

    def tst_centroid_image(self):
        self.tst_centroid_image2d()
        self.tst_centroid_image3d()

    def tst_centroid_image2d(self):
        from dials.algorithms.image.centroid import CentroidImage2d
        from scitbx import matrix

        centroid = CentroidImage2d(self.pixels2d)

        assert(abs(self.gold2d - matrix.col(centroid.mean())) < self.EPS)
        assert(abs(self.gold2dvar - matrix.col(centroid.variance())) < self.EPS)
        print 'OK'

    def tst_centroid_image3d(self):
        from dials.algorithms.image.centroid import CentroidImage3d
        from scitbx import matrix

        centroid = CentroidImage3d(self.pixels3d)

        assert(abs(self.gold3d - matrix.col(centroid.mean())) < self.EPS)
        assert(abs(self.gold3dvar - matrix.col(centroid.variance())) < self.EPS)
        print 'OK'

    def tst_centroid_masked_image(self):
        self.tst_centroid_masked_image2d()
        self.tst_centroid_masked_image3d()

    def tst_centroid_masked_image2d(self):
        from dials.algorithms.image.centroid import CentroidMaskedImage2d
        from scitbx import matrix

        centroid = CentroidMaskedImage2d(self.pixels2d, self.mask2d)

        assert(abs(self.goldmasked2d - matrix.col(centroid.mean())) < self.EPS)
        assert(abs(self.goldmasked2dvar - matrix.col(centroid.variance())) < self.EPS)
        print 'OK'

    def tst_centroid_masked_image3d(self):
        from dials.algorithms.image.centroid import CentroidMaskedImage3d
        from scitbx import matrix

        centroid = CentroidMaskedImage3d(self.pixels3d, self.mask3d)

        assert(abs(self.goldmasked3d - matrix.col(centroid.mean())) < self.EPS)
        assert(abs(self.goldmasked3dvar - matrix.col(centroid.variance())) < self.EPS)
        print 'OK'

    def generate_data(self):
        from scitbx.array_family import flex
        from random import random, randint

        # Generate a 3d array of pixels and points
        self.points3d = flex.vec3_double(flex.grid(5, 5, 5))
        self.pixels3d = flex.double(flex.grid(5, 5, 5))
        self.mask3d = flex.int(flex.grid(5, 5, 5))
        for k in range(0, 5):
            for j in range(0, 5):
                for i in range(0, 5):
                    self.points3d[k,j,i] = (i + 0.5, j + 0.5, k + 0.5)
                    self.pixels3d[k,j,i] = random()
                    self.mask3d[k,j,i] = randint(0, 1)

        self.points2d = flex.vec2_double(flex.grid(5, 5))
        self.pixels2d = flex.double(flex.grid(5, 5))
        self.mask2d = flex.int(flex.grid(5, 5))
        for j in range(0, 5):
            for i in range(0, 5):
                self.points2d[j,i] = self.points3d[0, j, i][0:2]
                self.pixels2d[j,i] = self.pixels3d[0, j, i]
                self.mask2d[j,i] = self.mask3d[0, j, i]

    def calculate_gold(self):
        self.calculate_gold2d()
        self.calculate_gold3d()
        self.calculate_gold_masked2d()
        self.calculate_gold_masked3d()

    def calculate_gold2d(self):

        from scitbx import matrix

        r_tot = 0.0
        c_tot = 0.0
        d_tot = 0.0

        for (r, c), d in zip(self.points2d, self.pixels2d):
            r_tot += d * r
            c_tot += d * c
            d_tot += d

        self.gold2d = matrix.col((r_tot / d_tot, c_tot / d_tot))
        _r, _c = self.gold2d

        r_tot = 0.0
        c_tot = 0.0

        for (r, c), d in zip(self.points2d, self.pixels2d):
            r_tot += d * (r - _r) ** 2
            c_tot += d * (c - _c) ** 2

        _sr = r_tot / d_tot
        _sc = c_tot / d_tot

        self.gold2dvar = matrix.col((_sr, _sc))

    def calculate_gold3d(self):

        from scitbx import matrix

        f_tot = 0.0
        r_tot = 0.0
        c_tot = 0.0
        d_tot = 0.0

        for (f, r, c), d in zip(self.points3d, self.pixels3d):
            f_tot += d * f
            r_tot += d * r
            c_tot += d * c
            d_tot += d

        self.gold3d = matrix.col((f_tot / d_tot, r_tot / d_tot, c_tot / d_tot))

        _f, _r, _c = self.gold3d

        f_tot = 0.0
        r_tot = 0.0
        c_tot = 0.0

        for (f, r, c), d in zip(self.points3d, self.pixels3d):
            f_tot += d * (f - _f) ** 2
            r_tot += d * (r - _r) ** 2
            c_tot += d * (c - _c) ** 2

        _sf = f_tot / d_tot
        _sr = r_tot / d_tot
        _sc = c_tot / d_tot

        self.gold3dvar = matrix.col((_sf, _sr, _sc))

    def calculate_gold_masked2d(self):

        from scitbx import matrix

        r_tot = 0.0
        c_tot = 0.0
        d_tot = 0.0

        for (r, c), d, m in zip(self.points2d, self.pixels2d, self.mask2d):
            if m:
                r_tot += d * r
                c_tot += d * c
                d_tot += d

        self.goldmasked2d = matrix.col((r_tot / d_tot, c_tot / d_tot))

        _r, _c = self.goldmasked2d

        r_tot = 0.0
        c_tot = 0.0

        for (r, c), d, m in zip(self.points2d, self.pixels2d, self.mask2d):
            if m:
                r_tot += d * (r - _r) ** 2
                c_tot += d * (c - _c) ** 2

        _sr = r_tot / d_tot
        _sc = c_tot / d_tot

        self.goldmasked2dvar = matrix.col((_sr, _sc))

    def calculate_gold_masked3d(self):

        from scitbx import matrix

        f_tot = 0.0
        r_tot = 0.0
        c_tot = 0.0
        d_tot = 0.0

        for (f, r, c), d, m in zip(self.points3d, self.pixels3d, self.mask3d):
            if m:
                f_tot += d * f
                r_tot += d * r
                c_tot += d * c
                d_tot += d

        self.goldmasked3d = matrix.col((f_tot / d_tot,
            r_tot / d_tot, c_tot / d_tot))

        _f, _r, _c = self.goldmasked3d

        f_tot = 0.0
        r_tot = 0.0
        c_tot = 0.0

        for (f, r, c), d, m in zip(self.points3d, self.pixels3d, self.mask3d):
            if m:
                f_tot += d * (f - _f) ** 2
                r_tot += d * (r - _r) ** 2
                c_tot += d * (c - _c) ** 2

        _sf = f_tot / d_tot
        _sr = r_tot / d_tot
        _sc = c_tot / d_tot

        self.goldmasked3dvar = matrix.col((_sf, _sr, _sc))

if __name__ == '__main__':
    test = CentroidTest()
    test.run()
