/*
 * modeller.h
 *
 *  Copyright (C) 2013 Diamond Light Source
 *
 *  Author: James Parkhurst
 *
 *  This code is distributed under the BSD license, a copy of which is
 *  included in the root directory of this package.
 */

#ifndef DIALS_ALGORITHMS_PROFILE_MODEL_GAUSSIAN_RS_MODELLER_H
#define DIALS_ALGORITHMS_PROFILE_MODEL_GAUSSIAN_RS_MODELLER_H

#include <dials/algorithms/profile_model/gaussian_rs/transform/transform.h>
#include <dials/algorithms/profile_model/modeller/empirical_modeller.h>
#include <dials/algorithms/profile_model/modeller/single_sampler.h>
#include <dials/algorithms/profile_model/modeller/grid_sampler.h>
#include <dials/algorithms/profile_model/modeller/circle_sampler.h>
#include <dials/algorithms/integration/fit/fitting.h>

namespace dials { namespace algorithms {

  using dxtbx::model::Beam;
  using dxtbx::model::Detector;
  using dxtbx::model::Goniometer;
  using dxtbx::model::Scan;
  using dials::model::Shoebox;
  using dials::algorithms::profile_model::gaussian_rs::transform::TransformSpec;
  using dials::algorithms::profile_model::gaussian_rs::transform::Forward;

  /**
   * A base class to initialize the sampler
   */
  class GaussianRSProfileModellerBase {
  public:

    enum GridMethod {
      Single = 1,
      RegularGrid = 2,
      CircularGrid = 3
    };

    GaussianRSProfileModellerBase(
        const Beam &beam,
        const Detector &detector,
        const Goniometer &goniometer,
        const Scan &scan,
        double sigma_b,
        double sigma_m,
        double n_sigma,
        std::size_t grid_size,
        std::size_t num_scan_points,
        int grid_method)
      : beam_(beam),
        detector_(detector),
        goniometer_(goniometer),
        scan_(scan),
        sigma_b_(sigma_b),
        sigma_m_(sigma_m),
        n_sigma_(n_sigma),
        grid_size_(grid_size),
        num_scan_points_(num_scan_points),
        grid_method_(grid_method),
        sampler_(
          init_sampler(
            detector,
            scan,
            num_scan_points,
            grid_method)) {}

  protected:

    boost::shared_ptr<SamplerIface> init_sampler(
        const Detector &detector,
        const Scan &scan,
        std::size_t num_scan_points,
        int grid_method) {
      int2 scan_range = scan.get_array_range();
      boost::shared_ptr<SamplerIface> sampler;
      switch (grid_method) {
      case Single:
        sampler = boost::make_shared<SingleSampler>(
            scan_range,
            num_scan_points);
        break;
      case RegularGrid:
        DIALS_ASSERT(detector.size() == 1);
        sampler = boost::make_shared<GridSampler>(
            detector[0].get_image_size(),
            scan_range,
            int3(3, 3, num_scan_points));
        break;
      case CircularGrid:
        DIALS_ASSERT(detector.size() == 1);
        sampler = boost::make_shared<CircleSampler>(
            detector[0].get_image_size(),
            scan_range,
            num_scan_points);
        break;
      default:
        DIALS_ERROR("Unknown grid method");
      };
      return sampler;
    }

    Beam beam_;
    Detector detector_;
    Goniometer goniometer_;
    Scan scan_;
    double sigma_b_;
    double sigma_m_;
    double n_sigma_;
    std::size_t grid_size_;
    std::size_t num_scan_points_;
    int grid_method_;
    boost::shared_ptr<SamplerIface> sampler_;
  };


  /**
   * The profile modeller for the gaussian rs profile model
   */
  class GaussianRSProfileModeller
      : public GaussianRSProfileModellerBase,
        public EmpiricalProfileModeller {
  public:

    /**
     * Initialize
     * @param beam The beam model
     * @param detector The detector model
     * @param goniometer The goniometer model
     * @param scan The scan model
     * @param sigma_b The beam divergence
     * @param sigma_m The mosaicity
     * @param n_sigma The extent
     * @param grid_size The size of the profile grid
     * @param num_scan_points The number of phi scan points
     * @param threshold The modelling threshold value
     * @param grid_method The gridding method
     */
    GaussianRSProfileModeller(
            const Beam &beam,
            const Detector &detector,
            const Goniometer &goniometer,
            const Scan &scan,
            double sigma_b,
            double sigma_m,
            double n_sigma,
            std::size_t grid_size,
            std::size_t num_scan_points,
            double threshold,
            int grid_method)
      : GaussianRSProfileModellerBase(
          beam,
          detector,
          goniometer,
          scan,
          sigma_b,
          sigma_m,
          n_sigma,
          grid_size,
          num_scan_points,
          grid_method),
        EmpiricalProfileModeller(
          sampler_->size(),
          int3(
            2*grid_size+1,
            2*grid_size+1,
            2*grid_size+1),
          threshold),
        spec_(
          beam,
          detector,
          goniometer,
          scan,
          sigma_b,
          sigma_m,
          n_sigma,
          grid_size) {
      DIALS_ASSERT(sampler_ != 0);
    }

    Beam beam() const {
      return beam_;
    }

    Detector detector() const {
      return detector_;
    }

    Goniometer goniometer() const {
      return goniometer_;
    }

    Scan scan() const {
      return scan_;
    }

    double sigma_b() const {
      return sigma_b_;
    }

    double sigma_m() const {
      return sigma_m_;
    }

    double n_sigma() const {
      return n_sigma_;
    }

    std::size_t grid_size() const {
      return grid_size_;
    }

    std::size_t num_scan_points() const {
      return num_scan_points_;
    }

    double threshold() const {
      return threshold_;
    }

    int grid_method() const {
      return grid_method_;
    }

    /**
     * Model the profiles from the reflections
     * @param reflections The reflection list
     */
    void model(af::reflection_table reflections) {

      // Check input is OK
      DIALS_ASSERT(reflections.is_consistent());
      DIALS_ASSERT(reflections.contains("shoebox"));
      DIALS_ASSERT(reflections.contains("flags"));
      DIALS_ASSERT(reflections.contains("partiality"));
      DIALS_ASSERT(reflections.contains("s1"));
      DIALS_ASSERT(reflections.contains("xyzcal.px"));
      DIALS_ASSERT(reflections.contains("xyzcal.mm"));

      // Get some data
      af::const_ref< Shoebox<> > sbox = reflections["shoebox"];
      af::const_ref<double> partiality = reflections["partiality"];
      af::const_ref< vec3<double> > s1 = reflections["s1"];
      af::const_ref< vec3<double> > xyzpx = reflections["xyzcal.px"];
      af::const_ref< vec3<double> > xyzmm = reflections["xyzcal.mm"];
      af::ref<std::size_t> flags = reflections["flags"];

      // Loop through all the reflections and add them to the model
      for (std::size_t i = 0; i < reflections.size(); ++i) {
        DIALS_ASSERT(sbox[i].is_consistent());

        // Check if we want to use this reflection
        if (check1(flags[i], partiality[i], sbox[i])) {

          // Compute the transform
          Forward<double> transform(spec_, s1[i], xyzmm[i][2], sbox[i], true);

          // Get the indices and weights of the profiles
          af::shared<std::size_t> indices = sampler_->nearest_n(xyzpx[i]);
          af::shared<double> weights(indices.size());
          for (std::size_t j = 0; j < indices.size(); ++j) {
            weights[j] = sampler_->weight(indices[j], xyzpx[i]);
          }

          // Add the profile
          add(indices.const_ref(),
              weights.const_ref(),
              transform.profile().const_ref());

          // Set the flags
          flags[i] |= af::UsedInModelling;
        }
      }
    }

    /**
     * Return a profile fitter
     * @return The profile fitter class
     */
    void fit(af::reflection_table reflections) const {

      // Check input is OK
      DIALS_ASSERT(reflections.is_consistent());
      DIALS_ASSERT(reflections.contains("shoebox"));
      DIALS_ASSERT(reflections.contains("flags"));
      DIALS_ASSERT(reflections.contains("partiality"));
      DIALS_ASSERT(reflections.contains("s1"));
      DIALS_ASSERT(reflections.contains("xyzcal.px"));
      DIALS_ASSERT(reflections.contains("xyzcal.mm"));

      // Get some data
      af::const_ref< Shoebox<> > sbox = reflections["shoebox"];
      af::const_ref< vec3<double> > s1 = reflections["s1"];
      af::const_ref< vec3<double> > xyzpx = reflections["xyzcal.px"];
      af::const_ref< vec3<double> > xyzmm = reflections["xyzcal.mm"];
      af::ref<std::size_t> flags = reflections["flags"];
      af::ref<double> intensity_val = reflections["intensity.prf.value"];
      af::ref<double> intensity_var = reflections["intensity.prf.variance"];
      af::ref<double> reference_cor = reflections["profile.correlation"];

      // Loop through all the reflections and process them
      for (std::size_t i = 0; i < reflections.size(); ++i) {
        DIALS_ASSERT(sbox[i].is_consistent());

        // Set values to bad
        intensity_val[i] = 0.0;
        intensity_var[i] = -1.0;
        reference_cor[i] = 0.0;
        flags[i] &= ~af::IntegratedPrf;

        // Check if we want to use this reflection
        if (check2(flags[i], sbox[i])) {

          try {

            // Get the reference profiles
            std::size_t index = sampler_->nearest(xyzpx[i]);
            data_const_reference p = data(index).const_ref();
            mask_const_reference m = mask(index).const_ref();

            // Get the transformed shoebox
            Forward<double> transform(spec_, s1[i], xyzmm[i][2], sbox[i], false);
            data_const_reference c = transform.profile().const_ref();
            data_const_reference b = transform.background().const_ref();

            // Do the profile fitting
            ProfileFitting<double> fit(p, m, c, b, 1e-3, 100);
            DIALS_ASSERT(fit.niter() < 100);

            // Set the data in the reflection
            intensity_val[i] = fit.intensity();
            intensity_var[i] = fit.variance();
            reference_cor[i] = fit.correlation();

            // Set the integrated flag
            flags[i] |= af::IntegratedPrf;

          } catch (dials::error) {
            continue;
          }
        }
      }
    }

  private:

    /**
     * Do we want to use the reflection in profile modelling
     * @param flags The reflection flags
     * @param partiality The reflection partiality
     * @param sbox The reflection shoebox
     * @return True/False
     */
    bool check1(std::size_t flags,
               double partiality,
               const Shoebox<> &sbox) const {

      // Check we're fully recorded
      bool full = partiality > 0.99;

      // Check reflection has been integrated
      bool integrated = flags & af::IntegratedSum;

      // Check if the bounding box is in the image
      bool bbox_valid =
        sbox.bbox[0] >= 0 &&
        sbox.bbox[2] >= 0 &&
        sbox.bbox[1] <= spec_.image_size(sbox.panel)[0] &&
        sbox.bbox[3] <= spec_.image_size(sbox.panel)[1];

      // Check if all pixels are valid
      bool pixels_valid = true;
      for (std::size_t i = 0; i < sbox.mask.size(); ++i) {
        if (sbox.mask[i] & Foreground && !(sbox.mask[i] & Valid)) {
          pixels_valid = false;
          break;
        }
      }

      // Return whether to use or not
      return full && integrated && bbox_valid && pixels_valid;
    }

    /**
     * Do we want to use the reflection in profile fitting
     * @param flags The reflection flags
     * @param sbox The reflection shoebox
     * @return True/False
     */
    bool check2(std::size_t flags,
               const Shoebox<> &sbox) const {

      // Check if we want to integrate
      bool integrate = !(flags & af::DontIntegrate);

      // Check if the bounding box is in the image
      bool bbox_valid =
        sbox.bbox[0] >= 0 &&
        sbox.bbox[2] >= 0 &&
        sbox.bbox[1] <= spec_.image_size(sbox.panel)[0] &&
        sbox.bbox[3] <= spec_.image_size(sbox.panel)[1];

      // Check if all pixels are valid
      bool pixels_valid = true;
      for (std::size_t i = 0; i < sbox.mask.size(); ++i) {
        if (sbox.mask[i] & Foreground && !(sbox.mask[i] & Valid)) {
          pixels_valid = false;
          break;
        }
      }

      // Return whether to use or not
      return integrate && bbox_valid && pixels_valid;
    }

    TransformSpec<double> spec_;
  };

}} // namespace dials::algorithms

#endif // DIALS_ALGORITHMS_PROFILE_MODEL_GAUSSIAN_RS_MODELLER_H
