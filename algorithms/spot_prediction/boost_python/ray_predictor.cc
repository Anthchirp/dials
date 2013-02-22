/*
 * ray_predictor.cc
 *
 *  Copyright (C) 2013 Diamond Light Source
 *
 *  Author: James Parkhurst
 *
 *  This code is distributed under the BSD license, a copy of which is
 *  included in the root directory of this package.
 */
#include <boost/python.hpp>
#include <boost/python/def.hpp>
#include <dials/algorithms/spot_prediction/ray_predictor.h>
#include <dials/model/experiment/scan.h>
#include <dials/model/experiment/beam.h>
#include <dials/model/experiment/goniometer.h>
#include <dials/model/experiment/detector.h>
#include <dials/model/data/reflection.h>
#include "ray_predictor_wrapper.h"

namespace dials { namespace algorithms { namespace boost_python {

  using namespace boost::python;

  using model::Scan;
  using model::Beam;
  using model::Goniometer;
  using model::Reflection;

  void export_ray_predictor()
  {
    // Export a ray predictor
    ray_predictor_wrapper <
      RayPredictor <
        Beam,
        Goniometer,
        Scan,
        Reflection> >("RayPredictor");
  }

}}} // namespace = dials::spot_prediction::boost_python
