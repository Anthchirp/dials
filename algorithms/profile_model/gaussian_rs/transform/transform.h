/*
 * transform.h
 *
 *  Copyright (C) 2013 Diamond Light Source
 *
 *  Author: James Parkhurst
 *
 *  This code is distributed under the BSD license, a copy of which is
 *  included in the root directory of this package.
 */
#ifndef DIALS_ALGORITHMS_PROFILE_MODEL_GAUSSIAN_RS_TRANSFORM_H
#define DIALS_ALGORITHMS_PROFILE_MODEL_GAUSSIAN_RS_TRANSFORM_H

#include <scitbx/vec2.h>
#include <scitbx/vec3.h>
#include <scitbx/array_family/tiny_types.h>
#include <dxtbx/model/beam.h>
#include <dxtbx/model/detector.h>
#include <dxtbx/model/goniometer.h>
#include <dxtbx/model/scan.h>
#include <dials/algorithms/polygon/spatial_interpolation.h>
#include <dials/algorithms/profile_model/gaussian_rs/coordinate_system.h>
#include <dials/algorithms/profile_model/gaussian_rs/transform/map_frames.h>
#include <dials/algorithms/profile_model/gaussian_rs/transform/beam_vector_map.h>
#include <dials/model/data/shoebox.h>

namespace dials {
namespace algorithms {
namespace profile_model {
namespace gaussian_rs {
namespace transform {

  using scitbx::vec2;
  using scitbx::vec3;
  using scitbx::af::int2;
  using scitbx::af::int3;
  using scitbx::af::double3;
  using scitbx::af::int6;
  using dxtbx::model::Beam;
  using dxtbx::model::Detector;
  using dxtbx::model::Goniometer;
  using dxtbx::model::Scan;
  using dials::model::Foreground;
  using dials::model::Valid;
  using dials::model::Shoebox;
  using dials::algorithms::polygon::spatial_interpolation::vert4;
  using dials::algorithms::polygon::spatial_interpolation::Match;
  using dials::algorithms::polygon::spatial_interpolation::quad_to_grid;


  /**
   * A class to construct the specification for the transform. Once instantiated
   * this object can be reused to transform lots of reflections.
   */
  class TransformSpec {
  public:

    /*
     * Initialise the class
     * @param beam The beam model
     * @param detector The detector model
     * @param gonio The goniometer model
     * @param scan The scan model
     * @param sigma_b The beam divergence
     * @param sigma_m The crystal mosaicity
     * @param n_sigma The number of standard deviations
     * @param grid_size The size of the reflection basis grid
     */
    TransformSpec(const Beam &beam,
                  const Detector &detector,
                  const Goniometer &gonio,
                  const Scan &scan,
                  double sigma_b,
                  double sigma_m,
                  double n_sigma,
                  std::size_t grid_size)
      : beam_(beam),
        detector_(detector),
        goniometer_(gonio),
        scan_(scan),
        sigma_b_(sigma_b),
        sigma_m_(sigma_m),
        n_sigma_(n_sigma),
        grid_size_(2*grid_size+1, 2*grid_size+1, 2*grid_size+1),
        step_size_(sigma_m_ * n_sigma_ / (grid_size + 0.5),
                   sigma_b_ * n_sigma_ / (grid_size + 0.5),
                   sigma_b_ * n_sigma_ / (grid_size + 0.5)),
        grid_centre_(grid_size + 0.5, grid_size + 0.5, grid_size + 0.5) {
      DIALS_ASSERT(sigma_m_ > 0);
      DIALS_ASSERT(sigma_b_ > 0);
      DIALS_ASSERT(n_sigma_ > 0);
      DIALS_ASSERT(detector.size() > 0);
      DIALS_ASSERT(step_size_.all_gt(0));
      DIALS_ASSERT(grid_size_.all_gt(0));
    }

    /** @returns the beam */
    const Beam& beam() const {
      return beam_;
    }

    /** @returns the detector */
    const Detector& detector() const {
      return detector_;
    }

    /** @return the goniometer */
    const Goniometer& goniometer() const {
      return goniometer_;
    }

    /** @return the scan */
    const Scan& scan() const {
      return scan_;
    }

    /** @return sigma b */
    double sigma_b() const {
      return sigma_b_;
    }

    /** @return sigma m */
    double sigma_m() const {
      return sigma_m_;
    }

    /** @return n sigma */
    double n_sigma() const {
      return n_sigma_;
    }

    /** @returns the grid size */
    int3 grid_size() const {
      return grid_size_;
    }

    /** @returns the grid step size */
    double3 step_size() const {
      return step_size_;
    }

    /** @returns the grid centre */
    double3 grid_centre() const {
      return grid_centre_;
    }

  private:
    Beam beam_;
    Detector detector_;
    Goniometer goniometer_;
    Scan scan_;
    double sigma_b_;
    double sigma_m_;
    double n_sigma_;
    int3 grid_size_;
    double3 step_size_;
    double3 grid_centre_;
  };


  /**
   * A class to perform the local coordinate transform for a single reflection.
   * The class has a number of different constructors to allow the transform
   * to be done with lots of different inputs.
   *
   * Example:
   *
   *  from dials.algorithms.profile_model::gaussian_rs import transform
   *  forward = transform.Forward(spec, reflection)
   *  print forward.profile()
   *  print forward.background()
   */
  template <typename FloatType = double>
  class TransformForward {
  public:

    typedef FloatType float_type;
    typedef TransformSpec transform_spec_type;

    TransformForward() {}

    TransformForward(
        const TransformSpec &spec,
        const CoordinateSystem &cs,
        int6 bbox,
        std::size_t panel,
        const af::const_ref< FloatType, af::c_grid<3> > &image,
        const af::const_ref< bool, af::c_grid<3> > &mask) {
      init(spec, cs, bbox, panel);
      call(spec.detector()[panel], image, mask);
    }

    TransformForward(
        const TransformSpec &spec,
        const CoordinateSystem &cs,
        int6 bbox,
        std::size_t panel,
        const af::const_ref< FloatType, af::c_grid<3> > &image,
        const af::const_ref< FloatType, af::c_grid<3> > &bkgrd,
        const af::const_ref< bool, af::c_grid<3> > &mask) {
      init(spec, cs, bbox, panel);
      call(spec.detector()[panel], image, bkgrd, mask);
    }

    /** @returns The transformed profile */
    af::versa< FloatType, af::c_grid<3> > profile() const {
      return profile_;
    }

    /** @returns The transformed background (if set) */
    af::versa< FloatType, af::c_grid<3> > background() const {
      return background_;
    }

  private:

    /** Initialise using a coordinate system struct */
    void init(const TransformSpec &spec,
              const CoordinateSystem &cs,
              int6 bbox,
              std::size_t panel) {

      // Initialise some stuff
      x0_ = bbox[0];
      y0_ = bbox[2];
      shoebox_size_ = int3(bbox[5]-bbox[4], bbox[3]-bbox[2], bbox[1]-bbox[0]);
      DIALS_ASSERT(shoebox_size_.all_gt(0));
      DIALS_ASSERT(bbox[0] >= 0 && bbox[2] >= 0);
      DIALS_ASSERT(bbox[1] <= spec.detector()[panel].get_image_size()[0]);
      DIALS_ASSERT(bbox[3] <= spec.detector()[panel].get_image_size()[1]);
      step_size_ = spec.step_size();
      grid_size_ = spec.grid_size();
      grid_cent_ = spec.grid_centre();
      s1_ = cs.s1();
      DIALS_ASSERT(s1_.length() > 0);
      e1_ = cs.e1_axis() / s1_.length();
      e2_ = cs.e2_axis() / s1_.length();

      // Calculate the fraction of intensity contributed from each data
      // frame to each grid coordinate
      vec2<int> zrange(bbox[4], bbox[5]);

      // Create the frame mapper
      MapFramesForward<FloatType> map_frames(
          spec.scan().get_array_range()[0],
          spec.scan().get_oscillation()[0],
          spec.scan().get_oscillation()[1],
          spec.sigma_m(),
          spec.n_sigma(),
          spec.grid_size()[2] / 2);
      zfraction_arr_ = map_frames(zrange, cs.phi(), cs.zeta());
    }

    /**
     * Map the pixel values from the input image to the output grid.
     * @param image The image to transform
     * @param mask The mask accompanying the image
     */
    void call(const Panel &panel,
              const af::const_ref< FloatType, af::c_grid<3> > &image,
              const af::const_ref< bool, af::c_grid<3> > &mask) {

      // Check the input
      DIALS_ASSERT(image.accessor().all_eq(shoebox_size_));
      DIALS_ASSERT(image.accessor().all_eq(mask.accessor()));

      af::const_ref< FloatType, af::c_grid<2> > zfraction = zfraction_arr_.const_ref();

      // Initialise the profile arrays
      af::c_grid<3> accessor(grid_size_);
      profile_ = af::versa< FloatType, af::c_grid<3> >(accessor, 0.0);

      // Loop through all the points in the shoebox. Calculate the polygon
      // formed by the pixel in the local coordinate system. Find the points
      // on the grid which intersect with the polygon and the fraction of the
      // pixel area shared with each grid point. For each intersection, loop
      // through the frames, mapping the fraction of the pixel value in each
      // frame to the grid point.
      af::c_grid<2> grid_size2(grid_size_[1], grid_size_[2]);
      for (std::size_t j = 0; j < shoebox_size_[1]; ++j) {
        for (std::size_t i = 0; i < shoebox_size_[2]; ++i) {
          vert4 input(gc(panel, j, i),
                      gc(panel, j, i+1),
                      gc(panel, j+1, i+1),
                      gc(panel, j+1, i));
          af::shared<Match> matches = quad_to_grid(input, grid_size2, 0);
          for (int m = 0; m < matches.size(); ++m) {
            FloatType fraction = matches[m].fraction;
            int index = matches[m].out;
            int ii = index % grid_size_[2];
            int jj = index / grid_size_[2];
            for (int k = 0; k < shoebox_size_[0]; ++k) {
              if (mask(k, j, i)) {
                FloatType value = image(k, j, i) * fraction;
                for (int kk = 0; kk < grid_size_[0]; ++kk) {
                  profile_(kk, jj, ii) += value * zfraction(k, kk);
                }
              }
            }
          }
        }
      }
    }

    /**
     * Map the pixel values from the input image to the output grid.
     * @param image The image to transform
     * @param bkgrd The background image to transform
     * @param mask The mask accompanying the image
     */
    void call(const Panel &panel,
              const af::const_ref< FloatType, af::c_grid<3> > &image,
              const af::const_ref< FloatType, af::c_grid<3> > &bkgrd,
              const af::const_ref< bool, af::c_grid<3> > &mask) {

      // Check the input
      DIALS_ASSERT(image.accessor().all_eq(shoebox_size_));
      DIALS_ASSERT(image.accessor().all_eq(mask.accessor()));
      DIALS_ASSERT(image.accessor().all_eq(bkgrd.accessor()));

      af::const_ref< FloatType, af::c_grid<2> > zfraction = zfraction_arr_.const_ref();

      // Initialise the profile arrays
      af::c_grid<3> accessor(grid_size_);
      profile_ = af::versa< FloatType, af::c_grid<3> >(accessor, 0.0);
      background_ = af::versa< FloatType, af::c_grid<3> >(accessor, 0.0);

      // Loop through all the points in the shoebox. Calculate the polygon
      // formed by the pixel in the local coordinate system. Find the points
      // on the grid which intersect with the polygon and the fraction of the
      // pixel area shared with each grid point. For each intersection, loop
      // through the frames, mapping the fraction of the pixel value in each
      // frame to the grid point.
      af::c_grid<2> grid_size2(grid_size_[1], grid_size_[2]);
      for (std::size_t j = 0; j < shoebox_size_[1]; ++j) {
        for (std::size_t i = 0; i < shoebox_size_[2]; ++i) {
          vert4 input(gc(panel, j, i),
                      gc(panel, j, i+1),
                      gc(panel, j+1, i+1),
                      gc(panel, j+1, i));
          af::shared<Match> matches = quad_to_grid(input, grid_size2, 0);
          for (int m = 0; m < matches.size(); ++m) {
            FloatType fraction = matches[m].fraction;
            int index = matches[m].out;
            int jj = index / grid_size_[2];
            int ii = index % grid_size_[2];
            for (int k = 0; k < shoebox_size_[0]; ++k) {
              if (mask(k, j, i)) {
                FloatType ivalue = image(k, j, i) * fraction;
                FloatType bvalue = bkgrd(k, j, i) * fraction;
                for (int kk = 0; kk < grid_size_[0]; ++kk) {
                  FloatType zf = zfraction(k, kk);
                  profile_(kk, jj, ii) += ivalue * zf;
                  background_(kk, jj, ii) += bvalue * zf;
                }
              }
            }
          }
        }
      }
    }

    /**
     * Get a grid coordinate from an image coordinate
     * @param j The y index
     * @param i The x index
     * @returns The grid (c1, c2) index
     */
    vec2<double> gc(const Panel &panel,
                    std::size_t j,
                    std::size_t i) const {
      vec3<double> sp = panel.get_pixel_lab_coord(vec2<double>(x0_+i,y0_+j));
      vec3<double> ds = sp.normalize() * s1_.length() - s1_;
      return vec2<double>(grid_cent_[2] + (e1_ * ds) / step_size_[2],
                          grid_cent_[1] + (e2_ * ds) / step_size_[1]);
    }

    int x0_, y0_;
    int3 shoebox_size_;
    int3 grid_size_;
    double3 step_size_;
    double3 grid_cent_;
    vec3<double> s1_, e1_, e2_;
    af::versa< FloatType, af::c_grid<3> > profile_;
    af::versa< FloatType, af::c_grid<3> > background_;
    af::versa< FloatType, af::c_grid<2> > zfraction_arr_;
  };

}}}}} // namespace dials::algorithms::profile_model::gaussian_rs::transform

#endif /* DIALS_ALGORITHMS_PROFILE_MODEL_GAUSSIAN_RS_TRANSFORM */
