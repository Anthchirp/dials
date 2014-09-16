/*
 * creator.h
 *
 *  Copyright (C) 2013 Diamond Light Source
 *
 *  Author: James Parkhurst
 *
 *  This code is distributed under the BSD license, a copy of which is
 *  included in the root directory of this package.
 */
#ifndef DIALS_ALGORITHMS_BACKGROUND_CREATOR_H
#define DIALS_ALGORITHMS_BACKGROUND_CREATOR_H

#include <cmath>
#include <boost/shared_ptr.hpp>
#include <dials/array_family/scitbx_shared_and_versa.h>
#include <dials/algorithms/background/simple/outlier_rejector.h>
#include <dials/algorithms/background/simple/modeller.h>
#include <dials/model/data/shoebox.h>
#include <dials/error.h>


namespace dials { namespace algorithms { namespace background {

  using dials::model::Shoebox;
  using dials::model::Valid;
  using dials::model::Background;
  using dials::model::BackgroundUsed;

  /**
   * Class to create background shoebox
   */
  template <typename FloatType = float>
  class Creator {
  public:

    typedef FloatType float_type;

    /**
     * Initialise with the desired modeller.
     * @param modeller The background modeller
     */
    Creator(boost::shared_ptr<Modeller> modeller)
      : modeller_(modeller) {
      DIALS_ASSERT(modeller != NULL);
    }

    /**
     * Initialise with the desired modeller and outlier rejector.
     * @param modeller The background modeller
     * @param rejector The outlier rejector
     */
    Creator(
          boost::shared_ptr<Modeller> modeller,
          boost::shared_ptr<OutlierRejector> rejector)
      : modeller_(modeller),
        rejector_(rejector) {
      DIALS_ASSERT(modeller != NULL);
    }

    /**
     * Create the background for the list of shoeboxes.
     * @param shoeboxes The list of shoeboxes
     * @return Success True/False per shoebox
     */
    af::shared<bool> operator()(
        const af::const_ref< Shoebox<FloatType> > &shoeboxes,
        af::ref<double> mse) const {
      af::shared<bool> result(shoeboxes.size(), true);
      for (std::size_t i = 0; i < shoeboxes.size(); ++i) {
        try {
          mse[i] = this->operator()(shoeboxes[i]);
        } catch (dials::error) {
          result[i] = false;
          mse[i] = 0.0;
        }
      }
      return result;
    }

    /**
     * Create the background for the shoebox
     * @param shoebox The shoebox
     */
    FloatType operator()(Shoebox<FloatType> shoebox) const {
      return this->operator()(
          shoebox.data.const_ref(),
          shoebox.mask.ref(),
          shoebox.background.ref());
    }

    /**
     * Create the background for the given data
     * @param data The shoebox pixel values
     * @param mask The shoebox mask values
     * @param background The shoebox background
     */
    FloatType operator()(
        const af::const_ref< FloatType, af::c_grid<3> > &data_in,
        af::ref< int, af::c_grid<3> > mask,
        af::ref< FloatType, af::c_grid<3> > background) const {

      // Copy the array to a double
      af::versa< double, af::c_grid<3> > data(data_in.accessor());
      std::copy(data_in.begin(), data_in.end(), data.begin());

      // Do outlier rejection on the pixels
      if (rejector_) {
        rejector_->mark(data.const_ref(), mask);
      } else {
        for (std::size_t k = 0; k < mask.accessor()[0]; ++k) {
          for (std::size_t j = 0; j < mask.accessor()[1]; ++j) {
            for (std::size_t i = 0; i < mask.accessor()[2]; ++i) {
              const int maskcode = Valid | Background;
              if ((mask(k,j,i) & maskcode) == maskcode) {
                mask(k,j,i) |= BackgroundUsed;
              }
            }
          }
        }
      }

      // Create a background boolean mask
      af::versa< bool, af::c_grid<3> > bgmask(mask.accessor(), false);
      for (std::size_t i = 0; i < mask.size(); ++i) {
        bgmask[i] = (mask[i] & BackgroundUsed) != 0;
      }

      // Create the background model
      boost::shared_ptr<Model> model = modeller_->create(
          data.const_ref(), bgmask.const_ref());

      // Populate the background shoebox
      double mse = 0.0;
      std::size_t count = 0;
      for (std::size_t k = 0; k < background.accessor()[0]; ++k) {
        for (std::size_t j = 0; j < background.accessor()[1]; ++j) {
          for (std::size_t i = 0; i < background.accessor()[2]; ++i) {
            background(k,j,i) = model->value(k + 0.5, j + 0.5, i + 0.5);
            if (bgmask(k, j, i)) {
              double tmp = (background(k,j,i) - data(k,j,i));
              mse += tmp * tmp;
              count += 1;
            }
          }
        }
      }
      DIALS_ASSERT(count > 0);
      mse /= count;
      return mse;
    }

  private:

    boost::shared_ptr<Modeller> modeller_;
    boost::shared_ptr<OutlierRejector> rejector_;
  };

}}} // namespace dials::algorithms::background

#endif // DIALS_ALGORITHMS_BACKGROUND_CREATOR_H
