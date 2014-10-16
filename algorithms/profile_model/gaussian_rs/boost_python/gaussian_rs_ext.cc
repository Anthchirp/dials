/*
 * gaussian_rs_ext.cc
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
#include <boost_adaptbx/std_pair_conversion.h>
#include <dials/algorithms/profile_model/gaussian_rs/bbox_calculator.h>
#include <dials/algorithms/profile_model/gaussian_rs/partiality_calculator.h>
#include <dials/algorithms/profile_model/gaussian_rs/mask_calculator.h>
#include <dials/algorithms/profile_model/gaussian_rs/ideal_profile.h>
#include <dials/algorithms/profile_model/gaussian_rs/coordinate_system.h>

namespace dials {
namespace algorithms {
namespace profile_model {
namespace gaussian_rs {
namespace boost_python {

  using namespace boost::python;

  /**
   * Helper function to calculate zeta for an array of s1.
   */
  af::shared<double> zeta_factor_array(
      vec3<double> m2, vec3<double> s0,
      const af::const_ref< vec3<double> > &s1) {
    af::shared<double> result(s1.size());
    for (std::size_t i = 0; i < s1.size(); ++i) {
      result[i] = zeta_factor(m2, s0, s1[i]);
    }
    return result;
  }

  /**
   * Helper function to calculate zeta for an array of s1 with experiment
   * indices
   */
  af::shared<double> zeta_factor_array_multi(
      const af::const_ref< vec3<double> > &m2,
      const af::const_ref< vec3<double> > &s0,
      const af::const_ref< vec3<double> > &s1,
      const af::const_ref< std::size_t > &index) {
    DIALS_ASSERT(m2.size() == s0.size());
    DIALS_ASSERT(s1.size() == index.size());
    af::shared<double> result(s1.size());
    for (std::size_t i = 0; i < index.size(); ++i) {
      std::size_t j = index[i];
      DIALS_ASSERT(j < m2.size());
      result[i] = zeta_factor(m2[j], s0[j], s1[i]);
    }
    return result;
  }

  BOOST_PYTHON_MODULE(dials_algorithms_profile_model_gaussian_rs_ext)
  {
    class_ <BBoxCalculatorIface, boost::noncopyable>(
        "BBoxCalculatorIface", no_init)
      .def("__call__", &BBoxCalculatorIface::single, (
        arg("s1"),
        arg("frame"),
        arg("panel")))
      .def("__call__", &BBoxCalculatorIface::array, (
        arg("s1"),
        arg("frame"),
        arg("panel")))
      ;

    class_ <BBoxCalculator3D, bases<BBoxCalculatorIface> >(
        "BBoxCalculator3D", no_init)
      .def(init <const Beam&,
                 const Detector&,
                 const Goniometer&,
                 const Scan&,
                 double,
                 double > ((
        arg("beam"),
        arg("detector"),
        arg("goniometer"),
        arg("scan"),
        arg("delta_divergence"),
        arg("delta_mosaicity"))))
      ;

    class_ <BBoxCalculator2D, bases<BBoxCalculatorIface> >(
        "BBoxCalculator2D", no_init)
      .def(init <const Beam&,
                 const Detector&,
                 double,
                 double > ((
        arg("beam"),
        arg("detector"),
        arg("delta_divergence"),
        arg("delta_mosaicity"))))
      ;

    class_ <BBoxMultiCalculator>("BBoxMultiCalculator")
      .def("append", &BBoxMultiCalculator::push_back)
      .def("__len__", &BBoxMultiCalculator::size)
      .def("__call__", &BBoxMultiCalculator::operator())
      ;

    class_ <MaskCalculatorIface, boost::noncopyable>(
        "MaskCalculatorIface", no_init)
      .def("__call__", &MaskCalculatorIface::single, (
        arg("shoebox"),
        arg("s1"),
        arg("frame"),
        arg("panel")))
      .def("__call__", &MaskCalculatorIface::array, (
        arg("shoebox"),
        arg("s1"),
        arg("frame"),
        arg("panel")))
      ;

    class_ <PartialityCalculatorIface, boost::noncopyable>(
        "PartialityCalculatorIface", no_init)
      .def("__call__", &PartialityCalculatorIface::single, (
        arg("s1"),
        arg("frame"),
        arg("bbox")))
      .def("__call__", &PartialityCalculatorIface::array, (
        arg("s1"),
        arg("frame"),
        arg("bbox")))
      ;

    class_ <PartialityCalculator3D, bases<PartialityCalculatorIface> >(
        "PartialityCalculator3D", no_init)
      .def(init <const Beam&,
                 const Goniometer&,
                 const Scan&,
                 double > ((
        arg("beam"),
        arg("goniometer"),
        arg("scan"),
        arg("delta_m"))))
      ;

    class_ <PartialityCalculator2D, bases<PartialityCalculatorIface> >(
        "PartialityCalculator2D", no_init)
      .def(init <const Beam&,
                 double > ((
        arg("beam"),
        arg("delta_m"))))
      ;

    class_ <PartialityMultiCalculator>("PartialityMultiCalculator")
      .def("append", &PartialityMultiCalculator::push_back)
      .def("__len__", &PartialityMultiCalculator::size)
      .def("__call__", &PartialityMultiCalculator::operator())
      ;

    class_ <MaskCalculator3D, bases<MaskCalculatorIface> >(
        "MaskCalculator3D", no_init)
      .def(init <const Beam&,
                 const Detector&,
                 const Goniometer&,
                 const Scan&,
                 double,
                 double > ((
        arg("beam"),
        arg("detector"),
        arg("goniometer"),
        arg("scan"),
        arg("delta_divergence"),
        arg("delta_mosaicity"))))
      ;

    class_ <MaskCalculator2D, bases<MaskCalculatorIface> >(
        "MaskCalculator2D", no_init)
      .def(init <const Beam&,
                 const Detector&,
                 double,
                 double > ((
        arg("beam"),
        arg("detector"),
        arg("delta_divergence"),
        arg("delta_mosaicity"))))
      ;

    class_ <MaskMultiCalculator>("MaskMultiCalculator")
      .def("append", &MaskMultiCalculator::push_back)
      .def("__len__", &MaskMultiCalculator::size)
      .def("__call__", &MaskMultiCalculator::operator())
      ;

    def("ideal_profile_float", &ideal_profile<float>);
    def("ideal_profile_double", &ideal_profile<double>);

    // Export zeta factor functions
    def("zeta_factor",
      (double (*)(vec3<double>, vec3<double>, vec3<double>))&zeta_factor,
      (arg("m2"), arg("s0"), arg("s1")));
    def("zeta_factor",
      (double (*)(vec3<double>, vec3<double>))&zeta_factor,
      (arg("m2"), arg("e1")));
    def("zeta_factor", &zeta_factor_array, (
      arg("m2"), arg("s0"), arg("s1")));
    def("zeta_factor", &zeta_factor_array_multi, (
      arg("m2"), arg("s0"), arg("s1"), arg("index")));

    // Export coordinate system 2d
    class_<CoordinateSystem2d>("CoordinateSystem2d", no_init)
      .def(init<vec3<double>,
                vec3<double> >((
        arg("s0"),
        arg("s1"))))
      .def("s0", &CoordinateSystem2d::s0)
      .def("s1", &CoordinateSystem2d::s1)
      .def("p_star", &CoordinateSystem2d::p_star)
      .def("e1_axis", &CoordinateSystem2d::e1_axis)
      .def("e2_axis", &CoordinateSystem2d::e2_axis)
      .def("from_beam_vector",
        &CoordinateSystem2d::from_beam_vector)
      .def("to_beam_vector",
        &CoordinateSystem2d::to_beam_vector);

    // Export coordinate system
    class_<CoordinateSystem>("CoordinateSystem", no_init)
      .def(init<vec3<double>,
                vec3<double>,
                vec3<double>,
                double>((
        arg("m2"),
        arg("s0"),
        arg("s1"),
        arg("phi"))))
      .def("m2", &CoordinateSystem::m2)
      .def("s0", &CoordinateSystem::s0)
      .def("s1", &CoordinateSystem::s1)
      .def("phi", &CoordinateSystem::phi)
      .def("p_star", &CoordinateSystem::p_star)
      .def("e1_axis", &CoordinateSystem::e1_axis)
      .def("e2_axis", &CoordinateSystem::e2_axis)
      .def("e3_axis", &CoordinateSystem::e3_axis)
      .def("zeta", &CoordinateSystem::zeta)
      .def("lorentz_inv", &CoordinateSystem::lorentz_inv)
      .def("lorentz", &CoordinateSystem::lorentz)
      .def("path_length_increase", &CoordinateSystem::path_length_increase)
      .def("limits", &CoordinateSystem::limits)
      .def("from_beam_vector",
        &CoordinateSystem::from_beam_vector)
      .def("from_rotation_angle",
        &CoordinateSystem::from_rotation_angle)
      .def("from_rotation_angle_fast",
        &CoordinateSystem::from_rotation_angle_fast)
      .def("from_beam_vector_and_rotation_angle",
        &CoordinateSystem::from_beam_vector_and_rotation_angle)
      .def("to_beam_vector",
        &CoordinateSystem::to_beam_vector)
      .def("to_rotation_angle",
        &CoordinateSystem::to_rotation_angle)
      .def("to_rotation_angle_fast",
        &CoordinateSystem::to_rotation_angle_fast)
      .def("to_beam_vector_and_rotation_angle",
        &CoordinateSystem::to_beam_vector_and_rotation_angle);

    boost_adaptbx::std_pair_conversions::to_tuple<vec3<double>,double>();
  }

}}}}} // namespace = dials::algorithms::profile_model::gaussian_rs::boost_python
