/*
 * find_overlapping.h
 *
 *  Copyright (C) 2013 Diamond Light Source
 *
 *  Author: James Parkhurst
 *
 *  This code is distributed under the BSD license, a copy of which is
 *  included in the root directory of this package.
 */
#ifndef DIALS_ALGORITHMS_INTEGRATION_FIND_OVERLAPPING_H
#define DIALS_ALGORITHMS_INTEGRATION_FIND_OVERLAPPING_H

#include <vector>
#include <boost/shared_ptr.hpp>
#include <scitbx/array_family/tiny_types.h>
#include <dials/array_family/scitbx_shared_and_versa.h>
#include <dials/model/data/adjacency_list.h>
#include <dials/algorithms/spatial_indexing/detect_collisions.h>
#include <dials/error.h>

namespace dials { namespace algorithms {

  using scitbx::af::int6;

  // Helper functions needed for 3D collision detection
  template <> struct bound_coord_type<int6> { typedef int type; };
  template <> int get_minimum_bound<0, int6>(const int6 &b) { return b[0]; }
  template <> int get_maximum_bound<0, int6>(const int6 &b) { return b[1]; }
  template <> int get_minimum_bound<1, int6>(const int6 &b) { return b[2]; }
  template <> int get_maximum_bound<1, int6>(const int6 &b) { return b[3]; }
  template <> int get_minimum_bound<2, int6>(const int6 &b) { return b[4]; }
  template <> int get_maximum_bound<2, int6>(const int6 &b) { return b[5]; }

}} // namespace dials::algorithms

namespace dials { namespace algorithms { namespace shoebox {

  using scitbx::af::int6;
  using dials::model::AdjacencyList;

  /**
   * Given a set of reflections, find the bounding_boxes that overlap.
   * This function uses a single shot collision detection algorithm to
   * find the colliding bounding_boxes and then puts all the pairs of colliding
   * indices into an adjacency list. Vertices are referred to in the
   * adjacency list by index.
   * @param bbox The list of bounding boxes
   * @returns An adjacency list
   */
  inline
  boost::shared_ptr<AdjacencyList> find_overlapping(
      const af::const_ref<int6> &bboxes) {

    // Ensure we have a valid number of bboxes
    DIALS_ASSERT(bboxes.size() > 0);

    // Create a list of all the pairs of collisions between bouding boxes.
    std::vector<std::pair<int, int> > collisions;
    detect_collisions3d(bboxes.begin(), bboxes.end(), collisions);

    // Put all the collisions into an adjacency list
    boost::shared_ptr<AdjacencyList> list(new AdjacencyList);
    for (std::size_t i = 0; i < bboxes.size(); ++i) {
      add_vertex(*list);
    }
    for (std::size_t i = 0; i < collisions.size(); ++i) {
      add_edge(collisions[i].first, collisions[i].second, *list);
    }

    // Return the adjacency list
    return list;
  }

  namespace detail {

    // Struct to help sort data
      struct sort_by_panel {
        const af::const_ref<std::size_t> p_;
        sort_by_panel(const af::const_ref<std::size_t> &p)
          : p_(p) {}
        bool operator()(std::size_t a, std::size_t b) {
          return p_[a] < p_[b];
        }
      };
  }

  /**
   * Given a set of reflections, find the bounding_boxes that overlap.
   * This function uses a single shot collision detection algorithm to
   * find the colliding bounding_boxes and then puts all the pairs of colliding
   * indices into an adjacency list. Vertices are referred to in the
   * adjacency list by index.
   * @param panel The list of panels
   * @param bbox The list of bounding boxes
   * @returns An adjacency list
   */
  inline
  boost::shared_ptr<AdjacencyList> find_overlapping_multi_panel(
      const af::const_ref<int6> &bbox,
      const af::const_ref<std::size_t> &panel) {


    DIALS_ASSERT(panel.size() > 0);
    DIALS_ASSERT(panel.size() == bbox.size());

    // The arrays to use in the collision detection
    std::vector<int6> data(panel.size());
    std::vector<std::size_t> index(panel.size());
    for (std::size_t i = 0; i < index.size(); ++i) {
      index[i] = i;
    }
    std::vector<std::size_t> offset;

    // Sort arrays by panel
    std::sort(index.begin(), index.end(), detail::sort_by_panel(panel));

    // Create an array of offsets where the panel number is the same
    // and put the sorted list of bboxes into an new array
    offset.push_back(0);
    std::size_t p = panel[index[0]];
    for (std::size_t i = 0; i < index.size(); ++i) {
      std::size_t j = index[i];
      data[i] = bbox[j];
      if (panel[j] != p) {
        p = panel[j];
        offset.push_back(i);
      }
    }
    offset.push_back(index.size());

    // Do the collision detection for all bboxes in the same panel
    boost::shared_ptr<AdjacencyList> list(new AdjacencyList);
    for (std::size_t i = 0; i < bbox.size(); ++i) {
      add_vertex(*list);
    }
    for (std::size_t j = 0; j < offset.size() - 1; ++j) {
      std::size_t d0 = offset[j];
      std::size_t d1 = offset[j+1];
      std::vector< std::pair<int,int> > collisions;

      // Detect the collisions
      detect_collisions3d(
          data.begin() + d0,
          data.begin() + d1,
          collisions);

      // Put all the collisions into an adjacency list
      for (std::size_t i = 0; i < collisions.size(); ++i) {
        add_edge(
            index[d0 + collisions[i].first],
            index[d0 + collisions[i].second],
            *list);
      }
    }
    return list;
  }

  class OverlapFinder {
  public:

    OverlapFinder(const af::const_ref< af::tiny<int,2> > &groups) {
      for (std::size_t i = 0; i < groups.size(); ++i) {
        DIALS_ASSERT(groups[i][0] >= 0);
        DIALS_ASSERT(groups[i][1] > groups[i][0]);
        if (i > 0) {
          DIALS_ASSERT(groups[i][0] >= groups[i-1][1]);
        }
        for (int j = groups[i][0]; j < groups[i][1]; ++j) {
          exp_group_.push_back(i);
        }
      }
      DIALS_ASSERT(exp_group_.size() > 0);
    }

    struct sort_by_group {
      const std::vector<std::size_t>& g_;
      sort_by_group(const std::vector<std::size_t> &g)
        : g_(g) {}
      bool operator()(std::size_t a, std::size_t b) {
        return g_[a] < g_[b];
      }
    };

    boost::shared_ptr<AdjacencyList> operator()(
      const af::const_ref<std::size_t> &id,
      const af::const_ref<int6> &bbox,
      const af::const_ref<std::size_t> &panel) const {

      DIALS_ASSERT(panel.size() > 0);
      DIALS_ASSERT(panel.size() == bbox.size());
      DIALS_ASSERT(panel.size() == id.size());

      // Get the maximum panel number
      std::size_t max_panel = af::max(panel);

      // The arrays to use in the collision detection
      std::vector<std::size_t> group(panel.size());
      std::vector<int6> data(panel.size());
      std::vector<std::size_t> index(panel.size());
      for (std::size_t i = 0; i < index.size(); ++i) {
        index[i] = i;
      }
      std::vector<std::size_t> offset;

      // Construct a list of groups
      for (std::size_t i = 0; i < id.size(); ++i) {
        DIALS_ASSERT(id[i] < exp_group_.size());
        std::size_t eg = exp_group_[id[i]];
        std::size_t pp = panel[i];
        group[i] = pp + eg*max_panel;
      }

      // Sort arrays by group
      std::sort(index.begin(), index.end(), sort_by_group(group));

      // Create an array of offsets where the group number is the same and put
      // the sorted list of bboxes into an new array
      offset.push_back(0);
      std::size_t g = group[index[0]];
      for (std::size_t i = 0; i < index.size(); ++i) {
        std::size_t j = index[i];
        data[i] = bbox[j];
        if (group[j] != g) {
          DIALS_ASSERT(group[j] > g);
          g = group[j];
          offset.push_back(i);
        }
      }
      offset.push_back(index.size());

      // Do the collision detection for all bboxes in the same group
      boost::shared_ptr<AdjacencyList> list(new AdjacencyList);
      for (std::size_t i = 0; i < bbox.size(); ++i) {
        add_vertex(*list);
      }
      for (std::size_t j = 0; j < offset.size() - 1; ++j) {
        std::size_t d0 = offset[j];
        std::size_t d1 = offset[j+1];
        std::vector< std::pair<int,int> > collisions;

        // Detect the collisions
        detect_collisions3d(
            data.begin() + d0,
            data.begin() + d1,
            collisions);

        // Put all the collisions into an adjacency list
        for (std::size_t i = 0; i < collisions.size(); ++i) {
          add_edge(
              index[d0 + collisions[i].first],
              index[d0 + collisions[i].second],
              *list);
        }
      }
      return list;
    }

  private:

    std::vector<std::size_t> exp_group_;
  };

}}} // namespace dials::algorithms::shoebox

#endif // DIALS_ALGORITHMS_INTEGRATION_FIND_OVERLAPPING_H
