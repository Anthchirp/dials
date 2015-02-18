/*
 * flex_reflection_table.cc
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
#include <numeric>
#include <dials/array_family/boost_python/flex_table_suite.h>
#include <dials/array_family/reflection_table.h>
#include <dials/model/data/shoebox.h>
#include <dials/model/data/observation.h>
#include <scitbx/array_family/tiny_types.h>
#include <scitbx/array_family/ref_reductions.h>
#include <scitbx/vec3.h>
#include <scitbx/vec2.h>
#include <cctbx/miller.h>

namespace dials { namespace af { namespace boost_python {

  using namespace boost::python;
  using scitbx::vec2;
  using scitbx::vec3;
  using scitbx::af::int6;
  using flex_table_suite::flex_table_wrapper;
  using dials::model::Shoebox;
  using dials::model::Observation;

  /**
   * Construct a reflection table from a list of observations and shoeboxes
   * @param o The observation
   * @param s The shoeboxes
   * @returns A reflection table
   */
  template <typename T>
  T* make_from_observation_and_shoebox(
      const af::const_ref<Observation> &o,
      const af::const_ref< Shoebox<> > &s) {
    // FIXME Should remove as we don't know whether intensity is summed or
    // profile fitted. In any case observation model should be deprecated.
    DIALS_ASSERT(o.size() == s.size());

    // The reflection table
    T result(o.size());
    af::shared<std::size_t>    panel  = result["panel"];
    af::shared< vec3<double> > xyzval = result["xyzobs.px.value"];
    af::shared< vec3<double> > xyzvar = result["xyzobs.px.variance"];
    af::shared<double>         iraw   = result["intensity.sum.value"];
    af::shared<double>         irawv  = result["intensity.sum.variance"];
    af::shared<int6>           bbox   = result["bbox"];
    af::shared< Shoebox<> >    sbox   = result["shoebox"];

    // Copy all the values
    for (std::size_t i = 0; i < result.nrows(); ++i) {

      // Check panel numbers
      DIALS_ASSERT(o[i].panel == s[i].panel);
      panel[i] = o[i].panel;

      // Copy observation info
      xyzval[i] = o[i].centroid.px.position;
      xyzvar[i] = o[i].centroid.px.std_err_sq;
      iraw[i]   = o[i].intensity.observed.value;
      irawv[i]  = o[i].intensity.observed.variance;

      // Copy shoebox info
      bbox[i] = s[i].bbox;
      sbox[i].bbox = s[i].bbox;
      sbox[i].data = s[i].data;
      sbox[i].mask = s[i].mask;
      sbox[i].background = s[i].background;
    }

    // Return the new reflection table
    return new T(result);
  }

  /**
   * A function to print some help about keys
   */
  template <typename T>
  std::string help_keys(const T &self) {
    std::string result =
      "Standard column names:\n"
      "======================\n"
      "\n"
      " Columns in the reflection table can have any name and type;\n"
      " however, it is helpful to have a set of standard data columns\n"
      " which can be used by different algorithms. These are shown below.\n"
      "\n"
      " General properties\n"
      " ------------------\n"
      "\n"
      "  flags:                  bit mask status flags\n"
      "  id:                     experiment id\n"
      "  panel:                  the detector panel index\n"
      "\n"
      " Predicted properties\n"
      " --------------------\n"
      "\n"
      "  miller_index:           miller indices\n"
      "  entering:               reflection entering/exiting\n"
      "  s1:                     the diffracted beam vector\n"
      "  xyzcal.mm:              the predicted location (mm, mm, rad)\n"
      "  xyzcal.px:              the predicted location (px, px, frame)\n"
      "  ub_matrix:              predicted crystal setting\n"
      "\n"
      " Observed properties\n"
      " -------------------\n"
      "\n"
      "  xyzobs.px.value:        centroid pixel position\n"
      "  xyzobs.px.variance:     centroid pixel variance\n"
      "  xyzobs.mm.value:        centroid millimetre position\n"
      "  xyzobs.mm.variance:     centroid millimetre variance\n"
      "  rlp:                    reciprocal lattice point\n"
      "  intensity.sum.value:    raw intensity value\n"
      "  intensity.sum.variance: raw intensity variance\n"
      "  intensity.prf.value:    profile fitted intensity value\n"
      "  intensity.prf.variance: profile fitted intensity variance\n"
      "  lp:                     LP correction (multiplicative)\n"
      "  profile.correlation:    correlation in profile fitting\n"
      "\n"
      " Shoebox properties\n"
      " ------------------\n"
      "\n"
      "  bbox:                   bounding box\n"
      "  shoebox:                shoebox data/mask/background struct\n"
      "\n"
      ;
    return result;
  }

  /**
   * Do ray intersections for all items
   */
  template <typename T>
  af::shared< vec2<double> > compute_ray_intersections(
      const T &self, const model::Detector &detector) {
    af::shared< vec2<double> > result(self.nrows());
    af::const_ref< vec3<double> > s1 =
      self.template get< vec3<double> >("s1").const_ref();
    af::const_ref< std::size_t > panel =
      self.template get< std::size_t >("panel").const_ref();
    for (std::size_t i = 0; i < result.size(); ++i) {
      result[i] = detector[panel[i]].get_ray_intersection(s1[i]);
    }
    return result;
  }

  /**
   * Get where the flag value is set
   */
  template <typename T>
  af::shared<bool> get_flags(const T &self, std::size_t value, bool all) {
    af::shared<bool> result(self.nrows());
    af::shared<std::size_t> flags = self.template get<std::size_t>("flags");
    DIALS_ASSERT(flags.size() == result.size());
    if (all) {
      for (std::size_t i = 0; i < result.size(); ++i) {
        result[i] = (flags[i] & value) == value;
      }
    } else {
      for (std::size_t i = 0; i < result.size(); ++i) {
        result[i] = (flags[i] & value) != 0;
      }
    }
    return result;
  }

  /**
   * Set the flags.
   */
  template <typename T>
  void set_flags_by_mask(T self, const af::const_ref<bool> mask,
      std::size_t value) {
    DIALS_ASSERT(mask.size() == self.nrows());
    af::shared<std::size_t> flags = self.template get<std::size_t>("flags");
    for (std::size_t i = 0; i < mask.size(); ++i) {
      if (mask[i]) {
        flags[i] |= value;
      }
    }
  }

  /**
   * Set the flags.
   */
  template <typename T>
  void set_flags_by_index(T self, const af::const_ref<std::size_t> index,
      std::size_t value) {
    af::shared<std::size_t> flags = self.template get<std::size_t>("flags");
    for (std::size_t i = 0; i < index.size(); ++i) {
      DIALS_ASSERT(index[i] < flags.size());
      flags[index[i]] |= value;
    }
  }

  /**
   * Unset the flags.
   */
  template <typename T>
  void unset_flags_by_mask(T self, const af::const_ref<bool> mask,
      std::size_t value) {
    DIALS_ASSERT(mask.size() == self.nrows());
    af::shared<std::size_t> flags = self.template get<std::size_t>("flags");
    for (std::size_t i = 0; i < mask.size(); ++i) {
      if (mask[i]) {
        flags[i] &= ~value;
      }
    }
  }

  /**
   * Unset the flags.
   */
  template <typename T>
  void unset_flags_by_index(T self, const af::const_ref<std::size_t> index,
      std::size_t value) {
    af::shared<std::size_t> flags = self.template get<std::size_t>("flags");
    for (std::size_t i = 0; i < index.size(); ++i) {
      DIALS_ASSERT(index[i] < flags.size());
      flags[index[i]] &= ~value;
    }
  }

  /**
   * Split the reflection table in partials.
   */
  template <typename T>
  void split_partials(T self) {

    // Check the input
    DIALS_ASSERT(self.is_consistent());
    DIALS_ASSERT(self.contains("bbox"));

    // Compute the number of partials
    af::const_ref<int6> bbox = self["bbox"];
    std::size_t num_full = bbox.size();
    std::size_t num_partial = 0;
    for (std::size_t i = 0; i < bbox.size(); ++i) {
      DIALS_ASSERT(bbox[i][1] > bbox[i][0]);
      DIALS_ASSERT(bbox[i][3] > bbox[i][2]);
      DIALS_ASSERT(bbox[i][5] > bbox[i][4]);
      num_partial += (bbox[i][5] - bbox[i][4]);
    }
    DIALS_ASSERT(num_partial >= num_full);

    // If num partial is the same as num full exit early
    if (num_partial == num_full) {
      return;
    }

    // Create the new bounding boxes and indices
    af::shared<int6> bbox_new(num_partial);
    af::shared<std::size_t> indices(num_partial);
    std::size_t j = 0;
    for (std::size_t i = 0; i < num_full; ++i) {
      int6 b = bbox[i];
      for (int z = bbox[i][4]; z < bbox[i][5]; ++z) {
        DIALS_ASSERT(j < num_partial);
        bbox_new[j] = b;
        bbox_new[j][4] = z;
        bbox_new[j][5] = z + 1;
        indices[j] = i;
        j++;
      }
    }
    DIALS_ASSERT(j == num_partial);

    // Resize the reflection table
    self.resize(num_partial);

    // Reorder the reflections
    flex_table_suite::reorder(self, indices.const_ref());

    // Set the new bounding boxes
    flex_table_suite::setitem_column(self, "bbox", bbox_new.const_ref());
    flex_table_suite::setitem_column(self, "partial_id", indices.const_ref());
  }

  /**
   * Split the reflection table in partials and return indices.
   */
  template <typename T>
  af::shared<std::size_t> split_partial_indices(T self) {

    // Check the input
    DIALS_ASSERT(self.is_consistent());
    DIALS_ASSERT(self.contains("bbox"));

    // Compute the number of partials
    af::const_ref<int6> bbox = self["bbox"];
    std::size_t num_full = bbox.size();
    std::size_t num_partial = 0;
    for (std::size_t i = 0; i < bbox.size(); ++i) {
      DIALS_ASSERT(bbox[i][1] > bbox[i][0]);
      DIALS_ASSERT(bbox[i][3] > bbox[i][2]);
      DIALS_ASSERT(bbox[i][5] > bbox[i][4]);
      num_partial += (bbox[i][5] - bbox[i][4]);
    }
    DIALS_ASSERT(num_partial >= num_full);

    // If num partial is the same as num full exit early
    af::shared<std::size_t> indices(num_partial);
    if (num_partial == num_full) {
      for (std::size_t i = 0; i < indices.size(); ++i) {
        indices[i] = i;
      }
      return indices;
    }

    // Create the new bounding boxes and indices
    std::size_t j = 0;
    for (std::size_t i = 0; i < num_full; ++i) {
      for (int z = bbox[i][4]; z < bbox[i][5]; ++z) {
        DIALS_ASSERT(j < num_partial);
        indices[j] = i;
        j++;
      }
    }
    DIALS_ASSERT(j == num_partial);
    return indices;
  }

  /**
   * Split reflection table by experiment id
   */
  template <typename T>
  boost::python::list split_by_experiment_id(T self) {
    DIALS_ASSERT(self.contains("id"));

    // Get the id array
    af::const_ref<std::size_t> id = self["id"];

    // Get the number of experiments
    std::size_t num_expr = 0;
    for (std::size_t i = 0; i < id.size(); ++i) {
      if (id[i] >= num_expr) num_expr = id[i] + 1;
    }

    // Get the number of each
    std::vector<std::size_t> num(num_expr, 0);
    for (std::size_t i = 0; i < id.size(); ++i) {
      num[id[i]]++;
    }

    // Compute the indices
    std::vector<std::size_t> indices(id.size());
    std::vector<std::size_t> offset(1, 0);
    std::partial_sum(num.begin(), num.end(), std::back_inserter(offset));
    num.assign(num.size(), 0);
    for (std::size_t i = 0; i < indices.size(); ++i) {
      std::size_t j = id[i];
      DIALS_ASSERT(j < offset.size() - 1);
      std::size_t off1 = offset[j];
      std::size_t off2 = offset[j+1];
      DIALS_ASSERT(off2 > off1);
      DIALS_ASSERT(off2 <= indices.size());
      std::size_t k = off1 + num[j];
      DIALS_ASSERT(j < off2);
      num[j]++;
      indices[k] = i;
    }

    // For each experiment if select the reflections in the list
    boost::python::list result;
    for (std::size_t i = 0; i < offset.size()-1; ++i) {
      std::size_t off1 = offset[i];
      std::size_t off2 = offset[i+1];
      DIALS_ASSERT(off2 >= off1);
      std::size_t off = off1;
      std::size_t num = off2 - off1;
      if (num > 0) {
        DIALS_ASSERT(off + num <= indices.size());
        result.append(flex_table_suite::select_rows_index(
              self, const_ref<std::size_t>(&indices[off], num)));
      }
    }

    // Return the result
    return result;
  }

  /**
   * Split reflection table by experiment id
   */
  template <typename T>
  boost::python::list split_indices_by_experiment_id(
      T self, std::size_t num_expr) {
    DIALS_ASSERT(num_expr > 0);
    DIALS_ASSERT(self.contains("id"));

    // Get the id array
    af::const_ref<std::size_t> id = self["id"];

    // Get the number of each
    std::vector<std::size_t> num(num_expr, 0);
    for (std::size_t i = 0; i < id.size(); ++i) {
      DIALS_ASSERT(id[i] < num_expr);
      num[id[i]]++;
    }

    // Compute the indices
    std::vector<std::size_t> indices(id.size());
    std::vector<std::size_t> offset(1, 0);
    std::partial_sum(num.begin(), num.end(), std::back_inserter(offset));
    num.assign(num.size(), 0);
    for (std::size_t i = 0; i < indices.size(); ++i) {
      std::size_t j = id[i];
      DIALS_ASSERT(j < offset.size() - 1);
      std::size_t off1 = offset[j];
      std::size_t off2 = offset[j+1];
      DIALS_ASSERT(off2 > off1);
      DIALS_ASSERT(off2 <= indices.size());
      std::size_t k = off1 + num[j];
      DIALS_ASSERT(j < off2);
      num[j]++;
      indices[k] = i;
    }

    // For each experiment if select the reflections in the list
    boost::python::list result;
    for (std::size_t i = 0; i < offset.size()-1; ++i) {
      std::size_t off1 = offset[i];
      std::size_t off2 = offset[i+1];
      DIALS_ASSERT(off2 >= off1);
      std::size_t off = off1;
      std::size_t num = off2 - off1;
      if (num > 0) {
        DIALS_ASSERT(off + num <= indices.size());
        result.append(af::shared<std::size_t>(&indices[off], &indices[off]+num));
      } else {
        result.append(af::shared<std::size_t>());
      }
    }

    // Return the result
    return result;
  }

  /**
   * Struct to facilitate wrapping reflection table type
   */
  template <typename T>
  struct flex_reflection_table_wrapper : public flex_table_wrapper<T> {

    typedef flex_table_wrapper<T> base_type;
    typedef typename base_type::flex_types flex_types;
    typedef typename base_type::flex_table_type flex_table_type;
    typedef typename base_type::class_type class_type;

    /**
     * Wrap the reflection table class
     */
    static
    class_type wrap(const char *name) {

      // Wrap with flex table bindings
      class_type result = base_type::wrap(name);

      // Add functions
      result
        .def("__init__", make_constructor(
          &make_from_observation_and_shoebox<flex_table_type>))
        .def("help_keys",
          &help_keys<flex_table_type>)
        .def("compute_ray_intersections",
          &compute_ray_intersections<flex_table_type>)
        .def("get_flags",
          &get_flags<flex_table_type>, (
            boost::python::arg("value"),
            boost::python::arg("all") = true))
        .def("set_flags",
          &set_flags_by_mask<flex_table_type>)
        .def("set_flags",
          &set_flags_by_index<flex_table_type>)
        .def("unset_flags",
          &unset_flags_by_mask<flex_table_type>)
        .def("unset_flags",
          &unset_flags_by_index<flex_table_type>)
        .def("split_partials",
          &split_partials<flex_table_type>)
        .def("split_partial_indices",
          &split_partial_indices<flex_table_type>)
        .def("split_by_experiment_id",
          &split_by_experiment_id<flex_table_type>)
        .def("split_indices_by_experiment_id",
          &split_indices_by_experiment_id<flex_table_type>)
        ;

      // Create the flags enum in the reflection table scope
      scope in_table = result;
      enum_<Flags>("flags")
        .value("predicted", Predicted)
        .value("observed", Observed)
        .value("indexed", Indexed)
        .value("used_in_refinement", UsedInRefinement)
        .value("strong", Strong)
        .value("reference_spot", ReferenceSpot)
        .value("dont_integrate", DontIntegrate)
        .value("integrated_sum", IntegratedSum)
        .value("integrated_prf", IntegratedPrf)
        .value("integrated", Integrated)
        .value("overloaded", Overloaded)
        .value("overlapped_bg", OverlappedBg)
        .value("overlapped_fg", OverlappedFg)
        .value("in_powder_ring", InPowderRing)
        .value("bad_shoebox", BadShoebox)
        .value("bad_spot", BadSpot)
        ;

      // return the wrapped class
      return result;
    }
  };

  void export_flex_reflection_table() {

    // Set the do
    docstring_options local_docstring_options;
    local_docstring_options.enable_user_defined();
    local_docstring_options.enable_py_signatures();
    local_docstring_options.disable_cpp_signatures();

    // Define all the types we want to support in the table
    typedef reflection_table::mapped_type flex_types;

    // Export the reflection table
    flex_reflection_table_wrapper<flex_types>::wrap("reflection_table");
  }

}}} // namespace dials::af::boost_python
