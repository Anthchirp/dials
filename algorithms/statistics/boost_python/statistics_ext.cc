/*
 * statistics_ext.cc
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
#include <boost/math/distributions/normal.hpp>
#include <dials/array_family/scitbx_shared_and_versa.h>
#include <dials/algorithms/statistics/kolmogorov_smirnov_one_sided_distribution.h>
#include <dials/algorithms/statistics/kolmogorov_smirnov_two_sided_distribution.h>
#include <dials/algorithms/statistics/kolmogorov_smirnov_test.h>
#include <dials/algorithms/statistics/correlation.h>

namespace dials { namespace algorithms { namespace boost_python {

  using namespace boost::python;

  template <typename RealType>
  RealType kolmogorov_smirnov_one_sided_cdf(std::size_t n, RealType x) {
    return cdf(kolmogorov_smirnov_one_sided_distribution<RealType>(n), x);
  }

  template <typename RealType>
  RealType kolmogorov_smirnov_two_sided_cdf(std::size_t n, RealType x) {
    return cdf(kolmogorov_smirnov_two_sided_distribution<RealType>(),
        x * std::sqrt((double) n));
  }

  //template <typename RealType>
  //RealType kolmogorov_smirnov_one_sided_pdf(std::size_t n, RealType x) {
    //return pdf(kolmogorov_smirnov_one_sided_distribution<RealType>(n), x);
  //}

  template <typename RealType>
  boost::python::tuple kolmogorov_smirnov_test_standard_normal(
      const af::const_ref<RealType> &data, std::string type) {

    // Get the enumeration
    KSType etype = TwoSided;
    if (type.compare("less") == 0) {
      etype = Less;
    } else if (type.compare("greater") == 0) {
      etype = Greater;
    } else {
      DIALS_ASSERT(type.compare("two_sided") == 0);
    }

    // Perform the test
    std::pair<RealType,RealType> result =
      kolmogorov_smirnov_test(
        boost::math::normal_distribution<RealType>(0, 1),
        data.begin(), data.end(),
        etype);
    return boost::python::make_tuple(result.first, result.second);
  }

  BOOST_PYTHON_MODULE(dials_algorithms_statistics_ext)
  {
    def("kolmogorov_smirnov_one_sided_cdf",
        &kolmogorov_smirnov_one_sided_cdf<double>);
    def("kolmogorov_smirnov_two_sided_cdf",
        &kolmogorov_smirnov_two_sided_cdf<double>);
    //def("kolmogorov_smirnov_one_sided_pdf",
    //    &kolmogorov_smirnov_one_sided_pdf<double>);
    def ("kolmogorov_smirnov_test_standard_normal",
        &kolmogorov_smirnov_test_standard_normal<double>, (
          arg("data"),
          arg("type") = "two_sided"));


    def("spearman_correlation_coefficient",
       &spearman_correlation_coefficient<double>);
    def("pearson_correlation_coefficient",
       &pearson_correlation_coefficient<double>);
  }

}}} // namespace = dials::algorithms::boost_python
