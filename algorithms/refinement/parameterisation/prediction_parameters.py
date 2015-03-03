#
#  Copyright (C) (2014) STFC Rutherford Appleton Laboratory, UK.
#
#  Author: David Waterman.
#
#  This code is distributed under the BSD license, a copy of which is
#  included in the root directory of this package.
#

#### Python and general cctbx imports

from __future__ import division
from scitbx import matrix

#### DIALS imports

from dials.array_family import flex

"""This version of PredictionParameterisation vectorises calculations over
reflections, using flex arrays"""

class PredictionParameterisation(object):
  """
  Abstract interface for a class that groups together model parameterisations
  relating to diffraction geometry and provides:

  * A list of all free parameters concatenated from each of the models, with a
    getter and setter method that delegates to the contained models
  * Derivatives of the reflection prediction equation with respect to each of
    these free parameters

  Derived classes determine whether the reflection prediction equation is
  expressed in detector space (X, Y, phi) or orthogonalised reciprocal space.

  It is assumed that the provided model parameterisations will be one of four
  types:

  * Detector parameterisation
  * Beam parameterisation
  * Crystal orientation parameterisation
  * Crystal unit cell parameterisation

  One of each must be supplied for each Experiment. These could be satisfied by
  a dummy class if no parameterisation is desired for some model.

  We also need access to the underlying models that are parameterised. The
  model parameterisation objects do not provide access to these models as it is
  not their job to do so. Instead we keep a separate reference to an
  ExperimentList that allows access to the relevant models.

  The goniometer is not yet parameterised, but we need it for the equations if
  we are doing parameterisation in X, Y, Phi space. Conversely, if
  parameterisation is only in X, Y space, the goniometer model is optional.

  A class implementing PredictionParameterisation is used by a Refinery
  object directly, which takes the list of parameters, and indirectly via a
  Target function object, which takes the list of derivatives and composes the
  derivatives of a Target function from them.

  """

  def __init__(self,
               experiments,
               detector_parameterisations = None,
               beam_parameterisations = None,
               xl_orientation_parameterisations = None,
               xl_unit_cell_parameterisations = None):

    # References to the underlying models
    self._experiments = experiments

    # Keep references to all parameterised models
    self._detector_parameterisations = detector_parameterisations
    self._beam_parameterisations = beam_parameterisations
    self._xl_orientation_parameterisations = \
        xl_orientation_parameterisations
    self._xl_unit_cell_parameterisations = \
        xl_unit_cell_parameterisations

    # Check there are free parameters to refine
    self._length = self._len()
    if self._length == 0:
      raise RuntimeError("There are no free parameters for refinement")

    # Calculate Experiment to parameterisation mapping
    e2bp = dict([(ids, i) for i, dp in enumerate(beam_parameterisations) \
                 for ids in dp.get_experiment_ids()])
    e2xop = dict([(ids, i) for i, dp in enumerate(xl_orientation_parameterisations) \
                 for ids in dp.get_experiment_ids()])
    e2xucp = dict([(ids, i) for i, dp in enumerate(xl_unit_cell_parameterisations) \
                  for ids in dp.get_experiment_ids()])
    e2dp = dict([(ids, i) for i, dp in enumerate(detector_parameterisations) \
                 for ids in dp.get_experiment_ids()])
    from collections import namedtuple
    ParamSet = namedtuple('ParamSet', ['beam_param', 'xl_ori_param',
                                         'xl_uc_param', 'det_param'])

    self._exp_to_param = {i: ParamSet(e2bp.get(i), e2xop.get(i),
        e2xucp.get(i), e2dp.get(i)) for i, _ in enumerate(experiments)}

  def _len(self):
    length = 0
    if self._detector_parameterisations:
      for model in self._detector_parameterisations:
        length += model.num_free()

    if self._beam_parameterisations:
      for model in self._beam_parameterisations:
        length += model.num_free()

    if self._xl_orientation_parameterisations:
      for model in self._xl_orientation_parameterisations:
        length += model.num_free()

    if self._xl_unit_cell_parameterisations:
      for model in self._xl_unit_cell_parameterisations:
        length += model.num_free()

    return length

  def __len__(self):
    return self._length

  def get_param_vals(self):
    """return a concatenated list of parameters from each of the components
    in the global model"""

    global_p_list = []
    if self._detector_parameterisations:
      det_plists = [x.get_param_vals() for x
                    in self._detector_parameterisations]
      params = [x for l in det_plists for x in l]
      global_p_list.extend(params)

    if self._beam_parameterisations:
      src_plists = [x.get_param_vals() for x
                    in self._beam_parameterisations]
      params = [x for l in src_plists for x in l]
      global_p_list.extend(params)

    if self._xl_orientation_parameterisations:
      xlo_plists = [x.get_param_vals() for x
                    in self._xl_orientation_parameterisations]
      params = [x for l in xlo_plists for x in l]
      global_p_list.extend(params)

    if self._xl_unit_cell_parameterisations:
      xluc_plists = [x.get_param_vals() for x
                     in self._xl_unit_cell_parameterisations]
      params = [x for l in xluc_plists for x in l]
      global_p_list.extend(params)

    return global_p_list

  def get_param_names(self):
    """Return a list of the names of parameters in the order they are
    concatenated. Useful for output to log files and debugging."""
    param_names = []
    if self._detector_parameterisations:
      det_param_name_lists = [x.get_param_names() for x in \
                         self._detector_parameterisations]
      names = ["Detector%d" % i + x for i, l \
               in enumerate(det_param_name_lists) for x in l]
      param_names.extend(names)

    if self._beam_parameterisations:
      beam_param_name_lists = [x.get_param_names() for x in \
                         self._beam_parameterisations]
      params = ["Beam%d" % i + x for i, l \
                in enumerate(beam_param_name_lists) for x in l]
      param_names.extend(params)

    if self._xl_orientation_parameterisations:
      xlo_param_name_lists = [x.get_param_names() for x
                    in self._xl_orientation_parameterisations]
      params = ["Crystal%d" % i + x for i, l \
                in enumerate(xlo_param_name_lists) for x in l]
      param_names.extend(params)

    if self._xl_unit_cell_parameterisations:
      xluc_param_name_lists = [x.get_param_names() for x
                     in self._xl_unit_cell_parameterisations]
      params = ["Crystal%d" % i + x for i, l \
                in enumerate(xluc_param_name_lists) for x in l]
      param_names.extend(params)

    return param_names

  def set_param_vals(self, vals):
    """Set the parameter values of the contained models to the values in
    vals. This list must be of the same length as the result of
    get_param_vals and must contain the parameter values in the same order!
    This order is to be maintained by any sensible refinement engine."""

    assert len(vals) == len(self)
    it = iter(vals)

    if self._detector_parameterisations:
      for model in self._detector_parameterisations:
        tmp = [it.next() for i in range(model.num_free())]
        model.set_param_vals(tmp)

    if self._beam_parameterisations:
      for model in self._beam_parameterisations:
        tmp = [it.next() for i in range(model.num_free())]
        model.set_param_vals(tmp)

    if self._xl_orientation_parameterisations:
      for model in self._xl_orientation_parameterisations:
        tmp = [it.next() for i in range(model.num_free())]
        model.set_param_vals(tmp)

    if self._xl_unit_cell_parameterisations:
      for model in self._xl_unit_cell_parameterisations:
        tmp = [it.next() for i in range(model.num_free())]
        model.set_param_vals(tmp)

  def set_param_esds(self, esds):
    """Set the estimated standard deviations of parameter values of the
    contained models to the values in esds. This list must be of the same length
    as the result of get_param_vals and must contain the parameter values in the
    same order! This order is to be maintained by any sensible refinement
    engine."""

    assert len(esds) == len(self)
    it = iter(esds)

    if self._detector_parameterisations:
      for model in self._detector_parameterisations:
        tmp = [it.next() for i in range(model.num_free())]
        model.set_param_esds(tmp)

    if self._beam_parameterisations:
      for model in self._beam_parameterisations:
        tmp = [it.next() for i in range(model.num_free())]
        model.set_param_esds(tmp)

    if self._xl_orientation_parameterisations:
      for model in self._xl_orientation_parameterisations:
        tmp = [it.next() for i in range(model.num_free())]
        model.set_param_esds(tmp)

    if self._xl_unit_cell_parameterisations:
      for model in self._xl_unit_cell_parameterisations:
        tmp = [it.next() for i in range(model.num_free())]
        model.set_param_esds(tmp)

  def calculate_model_state_uncertainties(self, var_cov):
    """
    Take the variance-covariance matrix of all free parameters calculated by
    the minimisation engine. For each parameterisation in the global model,
    extract the subset of this matrix for the associated block of parameters.
    Pass this on to the relevant model parameterisation to calculate its own
    uncertainty of state."""

    i = 0
    if self._detector_parameterisations:
      for model in self._detector_parameterisations:
        n = model.num_free()
        sub = var_cov.matrix_copy_block(i, i, n, n).as_scitbx_matrix()
        state_covs = model.calculate_state_uncertainties(sub)
        if state_covs is None: continue
        if len(state_covs) == 1:
          model.set_state_uncertainties(state_covs[0])
        else:
          for i_state, state_cov in enumerate(state_covs):
            model.set_state_uncertainties(state_cov, multi_state_elt=i_state)
        i += n

    if self._beam_parameterisations:
      for model in self._beam_parameterisations:
        n = model.num_free()
        sub = var_cov.matrix_copy_block(i, i, n, n).as_scitbx_matrix()
        state_covs = model.calculate_state_uncertainties(sub)
        if state_covs is None: continue
        if len(state_covs) == 1:
          model.set_state_uncertainties(state_covs[0])
        else:
          for i_state, state_cov in enumerate(state_covs):
            model.set_state_uncertainties(state_cov, multi_state_elt=i_state)
        i += n

    if self._xl_orientation_parameterisations:
      for model in self._xl_orientation_parameterisations:
        n = model.num_free()
        sub = var_cov.matrix_copy_block(i, i, n, n).as_scitbx_matrix()
        state_covs = model.calculate_state_uncertainties(sub)
        if state_covs is None: continue
        if len(state_covs) == 1:
          model.set_state_uncertainties(state_covs[0])
        else:
          for i_state, state_cov in enumerate(state_covs):
            model.set_state_uncertainties(state_cov, multi_state_elt=i_state)
        i += n

    if self._xl_unit_cell_parameterisations:
      for model in self._xl_unit_cell_parameterisations:
        n = model.num_free()
        sub = var_cov.matrix_copy_block(i, i, n, n).as_scitbx_matrix()
        state_covs = model.calculate_state_uncertainties(sub)
        if state_covs is None: continue
        if len(state_covs) == 1:
          model.set_state_uncertainties(state_covs[0])
        else:
          for i_state, state_cov in enumerate(state_covs):
            model.set_state_uncertainties(state_cov, multi_state_elt=i_state)
        i += n

    return

  def get_gradients(self, reflections):
    """
    Calculate gradients of the prediction formula with respect to each
    of the parameters of the contained models, for all of the reflections.

    To be implemented by a derived class, which determines the space of the
    prediction formula (e.g. we calculate dX/dp, dY/dp, dphi/dp for the
    prediction formula for a rotation scan expressed in detector space, but
    components of d\vec{r}/dp for the prediction formula in reciprocal space

    """

    ### Calculate various quantities of interest for the reflections

    # Set up arrays of values for each reflection
    n = len(reflections)
    D = flex.mat3_double(n)
    s0 = flex.vec3_double(n)
    U = flex.mat3_double(n)
    B = flex.mat3_double(n)
    axis = flex.vec3_double(n)

    for iexp, exp in enumerate(self._experiments):

      sel = reflections['id'] == iexp
      isel = sel.iselection()

      # D matrix array
      panels = reflections['panel'].select(isel)
      for ipanel, D_mat in enumerate([p.get_D_matrix() for p in exp.detector]):
        subsel = isel.select(panels == ipanel)
        D.set_selected(subsel, D_mat)

      # s0 array
      s0.set_selected(isel, exp.beam.get_s0())

      # U and B arrays
      exp_U, exp_B = self._get_U_B_for_experiment(exp.crystal, reflections, isel)
      U.set_selected(isel, exp_U)
      B.set_selected(isel, exp_B)

      # axis array
      if exp.goniometer:
        axis.set_selected(isel, exp.goniometer.get_rotation_axis())

    return self._get_gradients_core(reflections, D, s0, U, B, axis)

  @staticmethod
  def _prepare_gradient_vectors(m, n):
    """set up lists of vectors to store calculated gradients in. This method
    may be overriden by a derived class to e.g. use sparse vectors"""

    dX_dp = [flex.double(m, 0.) for p in range(n)]
    dY_dp = [flex.double(m, 0.) for p in range(n)]
    dZ_dp = [flex.double(m, 0.) for p in range(n)]

    return dX_dp, dY_dp, dZ_dp

  def _get_U_B_for_experiment(self, crystal, reflections, isel):
    """helper function to return either a single U, B pair (for scan-static) or
    U, B arrays (scan-varying) for a particular experiment."""

    # isel and reflections ignored here (they are needed for the scan-varying
    # overload)
    return crystal.get_U(), crystal.get_B()


class SparseGradientVectorMixin(object):
  """Mixin class to use sparse vectors for storage of gradients of the
  prediction formula"""

  @staticmethod
  def _prepare_gradient_vectors(m, n):

    from scitbx import sparse

    dX_dp = [sparse.matrix_column(m) for p in range(n)]
    dY_dp = [sparse.matrix_column(m) for p in range(n)]
    dZ_dp = [sparse.matrix_column(m) for p in range(n)]

    return dX_dp, dY_dp, dZ_dp

class XYPhiPredictionParameterisation(PredictionParameterisation):

  def _get_gradients_core(self, reflections, D, s0, U, B, axis):
    """Calculate gradients of the prediction formula with respect to
    each of the parameters of the contained models, for reflection h
    that reflects at rotation angle phi with scattering vector s that
    intersects panel panel_id. That is, calculate dX/dp, dY/dp and
    dphi/dp"""

    # Spindle rotation matrices for every reflection
    #R = self._axis.axis_and_angle_as_r3_rotation_matrix(phi)
    #R = flex.mat3_double(len(reflections))
    # NB for now use flex.vec3_double.rotate_around_origin each time I need the
    # rotation matrix R.

    self._axis = axis
    self._s0 = s0

    # pv is the 'projection vector' for the ray along s1.
    self._D = D
    self._s1 = reflections['s1']
    self._pv = D * self._s1

    # also need quantities derived from pv, precalculated for efficiency
    u, v, w = self._pv.parts()
    self._w_inv = 1/w
    self._u_w_inv = u * self._w_inv
    self._v_w_inv = v * self._w_inv

    self._UB = U * B
    self._U = U
    self._B = B

    # r is the reciprocal lattice vector, in the lab frame
    self._h = reflections['miller_index'].as_vec3_double()
    self._phi_calc = reflections['xyzcal.mm'].parts()[2]
    self._r = (self._UB * self._h).rotate_around_origin(self._axis, self._phi_calc)

    # All of the derivatives of phi have a common denominator, given by
    # (e X r).s0, where e is the rotation axis. Calculate this once, here.
    self._e_X_r = self._axis.cross(self._r)
    self._e_r_s0 = (self._e_X_r).dot(self._s0)

    # Note that e_r_s0 -> 0 when the rotation axis, beam vector and
    # relp are coplanar. This occurs when a reflection just touches
    # the Ewald sphere.
    #
    # There is a relationship between e_r_s0 and zeta_factor.
    # Uncommenting the code below shows that
    # s0.(e X r) = zeta * |s X s0|

    #from dials.algorithms.profile_model.gaussian_rs import zeta_factor
    #from libtbx.test_utils import approx_equal
    #s = matrix.col(reflections['s1'][0])
    #z = zeta_factor(axis[0], s0[0], s)
    #ss0 = (s.cross(matrix.col(s0[0]))).length()
    #assert approx_equal(e_r_s0[0], z * ss0)

    # catch small values of e_r_s0
    e_r_s0_mag = flex.abs(self._e_r_s0)
    try:
      assert flex.min(e_r_s0_mag) > 1.e-6
    except AssertionError as e:
      imin = flex.min_index(e_r_s0_mag)
      print "(e X r).s0 too small:"
      print "for", (e_r_s0_mag <= 1.e-6).count(True), "reflections"
      print "out of", len(e_r_s0_mag), "total"
      print "such as", reflections['miller_index'][imin]
      print "with scattering vector", reflections['s1'][imin]
      print "where r =", self._r[imin]
      print "e =", self._axis[imin]
      print "s0 =", self._s0[imin]
      print ("this reflection forms angle with the equatorial plane "
             "normal:")
      vecn = matrix.col(self._s0[imin]).cross(matrix.col(self._axis[imin])).normalize()
      print matrix.col(reflections['s1'][imin]).accute_angle(vecn)
      raise e

    # Set up the lists of derivatives: a separate array over reflections for
    # each free parameter
    m = len(reflections)
    n = len(self) # number of free parameters
    dX_dp, dY_dp, dphi_dp = self._prepare_gradient_vectors(m, n)

    # determine experiment to indices mappings once, here
    experiment_to_idx = []
    for iexp, exp in enumerate(self._experiments):

      sel = reflections['id'] == iexp
      isel = sel.iselection()
      experiment_to_idx.append(isel)

    # reset a pointer to the parameter number
    self._iparam = 0

  ### Work through the parameterisations, calculating their contributions
  ### to derivatives d[pv]/dp and d[phi]/dp

    # loop over the detector parameterisations
    for dp in self._detector_parameterisations:

      # Determine (sub)set of reflections affected by this parameterisation
      isel = flex.size_t()
      for exp_id in dp.get_experiment_ids():
        isel.extend(experiment_to_idx[exp_id])

      # Access the detector model being parameterised
      detector = dp.get_model()

      # Get panel numbers of the affected reflections
      panel = reflections['panel'].select(isel)

      # loop through the panels in this detector
      for panel_id, _ in enumerate(exp.detector):

        # get the right subset of array indices to set for this panel
        sub_isel = isel.select(panel == panel_id)
        sub_pv = self._pv.select(sub_isel)
        sub_D = self._D.select(sub_isel)
        dpv_ddet_p = self._detector_derivatives(dp, sub_pv, sub_D, panel_id)

        # convert to dX/dp, dY/dp and assign the elements of the vectors
        # corresponding to this experiment and panel
        sub_w_inv = self._w_inv.select(sub_isel)
        sub_u_w_inv = self._u_w_inv.select(sub_isel)
        sub_v_w_inv = self._v_w_inv.select(sub_isel)
        dX_ddet_p, dY_ddet_p = self._calc_dX_dp_and_dY_dp_from_dpv_dp(
          sub_w_inv, sub_u_w_inv, sub_v_w_inv, dpv_ddet_p)

        # use a local parameter index pointer because we set all derivatives
        # for this panel before moving on to the next
        iparam = self._iparam
        for dX, dY in zip(dX_ddet_p, dY_ddet_p):
          dX_dp[iparam].set_selected(sub_isel, dX)
          dY_dp[iparam].set_selected(sub_isel, dY)
          # increment the local parameter index pointer
          iparam += 1

      # increment the parameter index pointer to the last detector parameter
      self._iparam += dp.num_free()

    # loop over the beam parameterisations
    for bp in self._beam_parameterisations:

      # Determine (sub)set of reflections affected by this parameterisation
      isel = flex.size_t()
      for exp_id in bp.get_experiment_ids():
        isel.extend(experiment_to_idx[exp_id])

      # Get required data from those reflections
      r = self._r.select(isel)
      e_X_r = self._e_X_r.select(isel)
      e_r_s0 = self._e_r_s0.select(isel)
      D = self._D.select(isel)

      w_inv = self._w_inv.select(isel)
      u_w_inv = self._u_w_inv.select(isel)
      v_w_inv = self._v_w_inv.select(isel)

      dpv_dbeam_p, dphi_dbeam_p = self._beam_derivatives(bp, r, e_X_r, e_r_s0, D)

      # convert to dX/dp, dY/dp and assign the elements of the vectors
      # corresponding to this experiment
      dX_dbeam_p, dY_dbeam_p = self._calc_dX_dp_and_dY_dp_from_dpv_dp(
        w_inv, u_w_inv, v_w_inv, dpv_dbeam_p)
      for dX, dY, dphi in zip(dX_dbeam_p, dY_dbeam_p, dphi_dbeam_p):
        dphi_dp[self._iparam].set_selected(isel, dphi)
        dX_dp[self._iparam].set_selected(isel, dX)
        dY_dp[self._iparam].set_selected(isel, dY)
        # increment the parameter index pointer
        self._iparam += 1

    # loop over the crystal orientation parameterisations
    for xlop in self._xl_orientation_parameterisations:

      # Determine (sub)set of reflections affected by this parameterisation
      isel = flex.size_t()
      for exp_id in xlop.get_experiment_ids():
        isel.extend(experiment_to_idx[exp_id])

      # Get required data from those reflections
      axis = self._axis.select(isel)
      phi_calc = self._phi_calc.select(isel)
      h = self._h.select(isel)
      s1 = self._s1.select(isel)
      e_X_r = self._e_X_r.select(isel)
      e_r_s0 = self._e_r_s0.select(isel)
      B = self._B.select(isel)
      D = self._D.select(isel)

      w_inv = self._w_inv.select(isel)
      u_w_inv = self._u_w_inv.select(isel)
      v_w_inv = self._v_w_inv.select(isel)

      dpv_dxlo_p, dphi_dxlo_p = self._xl_orientation_derivatives(
          xlop, axis, phi_calc, h, s1, e_X_r, e_r_s0, B, D)

      # convert to dX/dp, dY/dp and assign the elements of the vectors
      # corresponding to this experiment
      dX_dxlo_p, dY_dxlo_p = self._calc_dX_dp_and_dY_dp_from_dpv_dp(
        w_inv, u_w_inv, v_w_inv, dpv_dxlo_p)
      for dX, dY, dphi in zip(dX_dxlo_p, dY_dxlo_p, dphi_dxlo_p):
        dphi_dp[self._iparam].set_selected(isel, dphi)
        dX_dp[self._iparam].set_selected(isel, dX)
        dY_dp[self._iparam].set_selected(isel, dY)
        # increment the parameter index pointer
        self._iparam += 1

    # loop over the crystal unit cell parameterisations
    for xlucp in self._xl_unit_cell_parameterisations:

      # Determine (sub)set of reflections affected by this parameterisation
      isel = flex.size_t()
      for exp_id in xlucp.get_experiment_ids():
        isel.extend(experiment_to_idx[exp_id])

      # Get required data from those reflections
      axis = self._axis.select(isel)
      phi_calc = self._phi_calc.select(isel)
      h = self._h.select(isel)
      s1 = self._s1.select(isel)
      e_X_r = self._e_X_r.select(isel)
      e_r_s0 = self._e_r_s0.select(isel)
      U = self._U.select(isel)
      D = self._D.select(isel)

      w_inv = self._w_inv.select(isel)
      u_w_inv = self._u_w_inv.select(isel)
      v_w_inv = self._v_w_inv.select(isel)

      dpv_dxluc_p, dphi_dxluc_p =  self._xl_unit_cell_derivatives(
        xlucp, axis, phi_calc, h, s1, e_X_r, e_r_s0, U, D)

      # convert to dX/dp, dY/dp and assign the elements of the vectors
      # corresponding to this experiment
      dX_dxluc_p, dY_dxluc_p = self._calc_dX_dp_and_dY_dp_from_dpv_dp(
        w_inv, u_w_inv, v_w_inv, dpv_dxluc_p)
      for dX, dY, dphi in zip(dX_dxluc_p, dY_dxluc_p, dphi_dxluc_p):
        dphi_dp[self._iparam].set_selected(isel, dphi)
        dX_dp[self._iparam].set_selected(isel, dX)
        dY_dp[self._iparam].set_selected(isel, dY)
        # increment the parameter index pointer
        self._iparam += 1

    return (dX_dp, dY_dp, dphi_dp)

  def _detector_derivatives(self, dp, pv, D, panel_id):
    """helper function to convert derivatives of the detector state to
    derivatives of the vector pv"""

    # get the derivatives of detector d matrix for this panel
    dd_ddet_p = dp.get_ds_dp(multi_state_elt=panel_id)

    # calculate the derivative of pv for this parameter
    dpv_ddet_p = [(D * (-1. * der).elems) * pv for der in dd_ddet_p]

    return dpv_ddet_p

  def _beam_derivatives(self, bp, r, e_X_r, e_r_s0, D):
    """helper function to extend the derivatives lists by
    derivatives of the beam parameterisations"""

    # get the derivatives of the beam vector wrt the parameters
    ds0_dbeam_p = bp.get_ds_dp()

    dphi_dp = []
    dpv_dp = []

    # loop through the parameters
    for der in ds0_dbeam_p:

      # calculate the derivative of phi for this parameter
      dphi = (r.dot(der.elems) / e_r_s0) * -1.0
      dphi_dp.append(dphi)

      # calculate the derivative of pv for this parameter
      dpv_dp.append(D * (e_X_r * dphi + der))

    return dpv_dp, dphi_dp

  def _xl_orientation_derivatives(self, xlop, axis, phi_calc, h, s1, e_X_r, e_r_s0, B, D):
    """helper function to extend the derivatives lists by
    derivatives of the crystal orientation parameterisations"""

    # get derivatives of the U matrix wrt the parameters
    dU_dxlo_p = xlop.get_ds_dp()

    dphi_dp = []
    dpv_dp = []

    # loop through the parameters
    for der in dU_dxlo_p:

      der_mat = flex.mat3_double(len(B), der.elems)
      # calculate the derivative of r for this parameter
      # FIXME COULD DO THIS BETTER WITH __rmul__?!
      tmp = der_mat * B * h
      dr = tmp.rotate_around_origin(axis, phi_calc)

      # calculate the derivative of phi for this parameter
      dphi = -1.0 * dr.dot(s1) / e_r_s0
      dphi_dp.append(dphi)

      # calculate the derivative of pv for this parameter
      dpv_dp.append(D * (dr + e_X_r * dphi))

    return dpv_dp, dphi_dp

  def _xl_unit_cell_derivatives(self, xlucp, axis, phi_calc, h, s1, e_X_r, e_r_s0, U, D):
    """helper function to extend the derivatives lists by
    derivatives of the crystal unit cell parameterisations"""

    # get derivatives of the B matrix wrt the parameters
    dB_dxluc_p = xlucp.get_ds_dp()

    dphi_dp = []
    dpv_dp = []

    # loop through the parameters
    for der in dB_dxluc_p:

      der_mat = flex.mat3_double(len(U), der.elems)
      # calculate the derivative of r for this parameter
      tmp = U * der_mat * h
      dr = tmp.rotate_around_origin(axis, phi_calc)

      # calculate the derivative of phi for this parameter
      dphi = -1.0 * dr.dot(s1) / e_r_s0
      dphi_dp.append(dphi)

      # calculate the derivative of pv for this parameter
      dpv_dp.append(D * (dr + e_X_r * dphi))

    return dpv_dp, dphi_dp

  @staticmethod
  def _calc_dX_dp_and_dY_dp_from_dpv_dp(w_inv, u_w_inv, v_w_inv, dpv_dp):
    """helper function to calculate positional derivatives from
    dpv_dp using the quotient rule"""

    dX_dp = []
    dY_dp = []

    for der in dpv_dp:
      du_dp, dv_dp, dw_dp = der.parts()

      dX_dp.append(w_inv * (du_dp - dw_dp * u_w_inv))
      dY_dp.append(w_inv * (dv_dp - dw_dp * v_w_inv))

    return dX_dp, dY_dp

class XYPhiPredictionParameterisationSparse(SparseGradientVectorMixin,
  XYPhiPredictionParameterisation):
  """A version of XYPhiPredictionParameterisation that uses a sparse matrix
  data structure for memory efficiency when there are a large number of
  Experiments"""
  pass
