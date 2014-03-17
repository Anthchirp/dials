/*
 * fitting.h
 *
 *  Copyright (C) 2013 Diamond Light Source
 *
 *  Author: James Parkhurst
 *
 *  This code is distributed under the BSD license, a copy of which is
 *  included in the root directory of this package.
 */
#ifndef DIALS_ALGORITHMS_INTEGRATION_PROFILE_FITTING_H
#define DIALS_ALGORITHMS_INTEGRATION_PROFILE_FITTING_H

#include <boost/math/tools/minima.hpp>
#include <scitbx/array_family/ref_reductions.h>
#include <scitbx/vec2.h>
#include <dials/array_family/scitbx_shared_and_versa.h>
#include <dials/error.h>

namespace dials { namespace algorithms {

  using scitbx::af::sum;
  using scitbx::vec2;

  /**
   * Class to fix the observed with the reference profile
   */
  template <typename FloatType = double>
  class ProfileFitting {
  public:

    typedef FloatType float_type;

    /**
     * Instantiate the fitting algorithm with the reflection profile
     * @param p The profile to fit to
     * @param c The contents of the pixels
     * @param b The background of the pixels
     */
    ProfileFitting(const af::const_ref<FloatType, af::c_grid<3> > &p,
                   const af::const_ref<bool, af::c_grid<3> > &m,
                   const af::const_ref<FloatType, af::c_grid<3> > &c,
                   const af::const_ref<FloatType, af::c_grid<3> > &b,
                   double eps = 1e-3,
                   std::size_t max_iter = 10)
    {
      // Check the input
      DIALS_ASSERT(p.size() == m.size());
      DIALS_ASSERT(p.size() == c.size());
      DIALS_ASSERT(p.size() == b.size());
      DIALS_ASSERT(eps > 0.0);
      DIALS_ASSERT(max_iter >= 1);

      // Iterate to calculate the intensity. Exit if intensity goes less
      // than zero or if the tolerance or number of iteration is reached.
      double I0 = sum(c) - sum(b);
      vec2<double> I(0.0, 0.0);
      for (niter_ = 0; niter_ < max_iter; ++niter_) {
        I = estimate_intensity(p, m, c, b, I0);
        if ((error_ = std::abs(I[0] - I0)) < eps) {
          break;
        }
        I0 = I[0];
      }
      DIALS_ASSERT(I[1] >= 0);

      // Set the intensity and variance
      intensity_ = I[0];
      variance_ = I[1];
      correlation_ = compute_correlation(p, m, c, b);
    }

    /**
     * @returns The intensity
     */
    double intensity() const {
      return intensity_;
    }

    /**
     * @returns the variance
     */
    double variance() const {
      return variance_;
    }

    /**
     * @returns the correlation
     */
    double correlation() const {
      return correlation_;
    }

    /**
     * @returns The number of iterations
     */
    std::size_t niter() const {
      return niter_;
    }

    /**
     * @returns The error in the fit
     */
    double error() const {
      return error_;
    }

  private:

    /**
     * Evaluate the next intensity iteration.
     * @ returns The estimate of the intensity
     */
    vec2<double>
    estimate_intensity(const af::const_ref<FloatType, af::c_grid<3> > &p,
                       const af::const_ref<bool, af::c_grid<3> > &m,
                       const af::const_ref<FloatType, af::c_grid<3> > &c,
                       const af::const_ref<FloatType, af::c_grid<3> > &b,
                       double I) const {
      double sum1 = 0.0;
      double sum2 = 0.0;
      double sumv = 0.0;
      for (std::size_t i = 0; i < p.size(); ++i) {
        if (m[i]) {
          double v = std::abs(b[i]) + std::abs(I * p[i]);
          sumv += v;
          if (v > 0) {
            sum1 += (c[i] - b[i]) * p[i] / v;
            sum2 += p[i] * p[i] / v;
          }
        }
      }
      return vec2<double>(sum2 != 0 ? sum1 / sum2 : 0.0, sumv);

      //double df = 0.0, d2f = 0.0, sum_v = 0.0;
      //for (std::size_t i = 0; i < p.size(); ++i) {
        //if (m[i]) {
          //double v = std::abs(b[i]) + std::abs(p[i] * I);
          //double v2 = v*v;
          //double v3 = v2*v;
          //double c2 = c[i] * c[i];
          //double p2 = p[i] * p[i];
          //if (v > 0) {
            //df  += p[i] * (1.0 - c2 / v2);
            //d2f += 2.0 * p2 * c2 / v3;
            //sum_v += v;
          //}
        //}
      //}
      /*return vec2<double>(I - (d2f != 0 ? df / d2f : 0.0), sum_v);*/
    }

    /**
     * Compute the correlation coefficient between the profile and reference
     */
    double
    compute_correlation(const af::const_ref<FloatType, af::c_grid<3> > &p,
                        const af::const_ref<bool, af::c_grid<3> > &m,
                        const af::const_ref<FloatType, af::c_grid<3> > &c,
                        const af::const_ref<FloatType, af::c_grid<3> > &b) const {
      double xb = 0.0, yb = 0.0;
      std::size_t count = 0;
      for (std::size_t i = 0; i < p.size(); ++i) {
        if (m[i]) {
          xb += p[i];
          yb += c[i] - b[i];
          count++;
        }
      }
      DIALS_ASSERT(count > 0);
      xb /= count;
      yb /= count;
      double sdxdy = 0.0, sdx2 = 0.0, sdy2 = 0.0;
      for (std::size_t i = 0; i < p.size(); ++i) {
        if (m[i]) {
          double dx = p[i] - xb;
          double dy = c[i] - b[i] - yb;
          sdxdy += dx*dy;
          sdx2 += dx*dx;
          sdy2 += dy*dy;
        }
      }
      DIALS_ASSERT(sdx2 > 0.0 && sdy2 > 0.0);
      return sdxdy / (std::sqrt(sdx2) * std::sqrt(sdy2));
    }

    double intensity_;
    double variance_;
    double correlation_;
    std::size_t niter_;
    double error_;
  };

  /**
   * Class to fix the observed with the reference profile
   */
  template <typename FloatType = double>
  class ProfileFitting2 {
  public:

    typedef FloatType float_type;

    /**
     * Instantiate the fitting algorithm with the reflection profile
     * @param p The profile to fit to
     * @param c The contents of the pixels
     * @param b The background of the pixels
     */
    ProfileFitting2(const af::const_ref<FloatType, af::c_grid<3> > &p,
                   const af::const_ref<bool, af::c_grid<3> > &m,
                   const af::const_ref<FloatType, af::c_grid<3> > &c,
                   const af::const_ref<FloatType, af::c_grid<3> > &b,
                   double eps = 1e-3,
                   std::size_t max_iter = 10)
    {
      // Check the input
      DIALS_ASSERT(p.size() == c.size());
      DIALS_ASSERT(p.size() == b.size());
      DIALS_ASSERT(eps > 0.0);
      DIALS_ASSERT(max_iter >= 1);

      // Iterate to calculate the intensity. Exit if intensity goes less
      // than zero or if the tolerance or number of iteration is reached.
      double I = 0.0, I0 = sum(c);
      for (niter_ = 0; niter_ < max_iter; ++niter_) {
        I = estimate_intensity(p, c, b, I0);
        std::cout << I0 << ", " << I << std::endl;
        DIALS_ASSERT(I >= 0.0);
        if ((error_ = std::abs(I - I0)) < eps) {
          break;
        }
        I0 = I;
      }

      // Set the intensity and variance
      intensity_ = I;
      variance_ = estimate_variance(p, b, I);
      correlation_ = compute_correlation(p, m, c, b);
    }

    /**
     * @returns The intensity
     */
    double intensity() const {
      return intensity_;
    }

    /**
     * @returns the variance
     */
    double variance() const {
      return variance_;
    }

    /**
     * @returns the correlation
     */
    double correlation() const {
      return correlation_;
    }

    /**
     * @returns The number of iterations
     */
    std::size_t niter() const {
      return niter_;
    }

    /**
     * @returns The error in the fit
     */
    double error() const {
      return error_;
    }

  private:

    /**
     * Evaluate the next intensity iteration.
     * @ returns The estimate of the intensity
     */
    double estimate_intensity(const af::const_ref<FloatType, af::c_grid<3> > &p,
                              const af::const_ref<FloatType, af::c_grid<3> > &c,
                              const af::const_ref<FloatType, af::c_grid<3> > &b,
                              double I0) {
      double s1 = 0.0, s2 = 0.0;
      for (std::size_t i = 0; i < p.size(); ++i) {
        double v = b[i] + I0 * p[i];
        if (v == 0.0) continue;
        double pv = p[i] / v;
        s1 += (c[i] - b[i]) * pv;
        s2 += p[i] * pv;
      }
      return s2 == 0.0 ? 0.0 : s1 / s2;
    }

    /**
     * Calculate the total variance in the profile.
     * @returns The total variance
     */
    double estimate_variance(const af::const_ref<FloatType, af::c_grid<3> > &p,
                             const af::const_ref<FloatType, af::c_grid<3> > &b,
                             double I) {
      double V = 0.0;
      for (std::size_t i = 0; i < p.size(); ++i) {
        V += b[i] + I * p[i];
      }
      return V;
    }

    /**
     * Compute the correlation coefficient between the profile and reference
     */
    double
    compute_correlation(const af::const_ref<FloatType, af::c_grid<3> > &p,
                        const af::const_ref<bool, af::c_grid<3> > &m,
                        const af::const_ref<FloatType, af::c_grid<3> > &c,
                        const af::const_ref<FloatType, af::c_grid<3> > &b) const {
      double xb = 0.0, yb = 0.0;
      std::size_t count = 0;
      for (std::size_t i = 0; i < p.size(); ++i) {
        if (m[i]) {
          xb += p[i];
          yb += c[i] - b[i];
          count++;
        }
      }
      DIALS_ASSERT(count > 0);
      xb /= count;
      yb /= count;
      double sdxdy = 0.0, sdx2 = 0.0, sdy2 = 0.0;
      for (std::size_t i = 0; i < p.size(); ++i) {
        if (m[i]) {
          double dx = p[i] - xb;
          double dy = c[i] - b[i] - yb;
          sdxdy += dx*dy;
          sdx2 += dx*dx;
          sdy2 += dy*dy;
        }
      }
      DIALS_ASSERT(sdx2 > 0.0 && sdy2 > 0.0);
      return sdxdy / (std::sqrt(sdx2) * std::sqrt(sdy2));
    }

    double intensity_;
    double variance_;
    double correlation_;
    std::size_t niter_;
    double error_;
  };

}} // namespace dials::algorithms

#endif /* DIALS_ALGORITHMS_INTEGRATION_PROFILE_FITTING_H */
