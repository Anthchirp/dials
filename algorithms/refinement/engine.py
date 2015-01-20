#
#  Copyright (C) (2013) STFC Rutherford Appleton Laboratory, UK.
#
#  Author: David Waterman.
#
#  This code is distributed under the BSD license, a copy of which is
#  included in the root directory of this package.
#

"""Contains classes for refinement engines. Refinery is the shared interface,
LevenbergMarquardtIterations, GaussNewtonIterations, SimpleLBFGS and LBFGScurvs
are the current concrete implementations"""

from __future__ import division
from logging import info, debug

from scitbx import lbfgs
from scitbx.array_family import flex
import libtbx
import sys

# use lstbx classes
from scitbx.lstbx import normal_eqns, normal_eqns_solving

# termination reason strings
TARGET_ACHIEVED = "RMSD target achieved"
RMSD_CONVERGED = "RMSD no longer decreasing"
STEP_TOO_SMALL = "Step too small"
OBJECTIVE_INCREASE = "Refinement failure: objective increased"
MAX_ITERATIONS = "Reached maximum number of iterations"
MAX_TRIAL_ITERATIONS = "Reached maximum number of consecutive unsuccessful trial steps"
DOF_TOO_LOW = "Not enough degrees of freedom to refine"

class Journal(dict):
  """Container in which to store information about refinement history.

  This is simply a dict but provides some extra methods for access that
  maintain values as columns in a table. Refinery classes will use these methods
  while entering data to ensure the table remains consistent. Methods inherited
  from dict are not hidden for ease of use of this object when returned to the
  user."""
  reason_for_termination = None
  _nrows = 0

  def get_nrows(self):
    return self._nrows

  def add_column(self, key):
    """Add a new column named by key"""
    self[key] = [None] * self._nrows

    return

  def add_row(self):
    """Add an element to the end of each of the columns. Fail if any columns
    are the wrong length"""

    for k in self.keys():
      assert len(self[k]) == self._nrows
      self[k].append(None)
    self._nrows += 1

    return

  def del_last_row(self):
    """Delete the last element from the each of the columns. Fail if any columns
    are the wrong length"""

    if self._nrows == 0: return None
    for k in self.keys():
      assert len(self[k]) == self._nrows
      self[k].pop()
    self._nrows -= 1

    return

  def set_last_cell(self, key, value):
    """Set last cell in column given by key to value. Fail if the column is the
    wrong length"""

    assert len(self[key]) == self._nrows
    self[key][-1] = value

    return

class Refinery(object):
  """Interface for Refinery objects. This should be subclassed and the run
  method implemented."""

  # NOTES. A Refinery is initialised with a Target function. The target
  # function already contains a ReflectionManager (which holds the data) so
  # there's no need to pass the data in here. In fact the Target
  # class does the bulk of the work, as it also does the reflection prediction
  # to get the updated predictions on each cycle. This should make some sense
  # as the target function is inextricably linked to the space in which
  # predictions are made (e.g. detector space, phi), so it is not general
  # enough to sit abstractly above the prediction.

  # This keeps the Refinery simple and able to be focused only on generic
  # features of managing a refinement run, like reporting results and checking
  # termination criteria.

  # The prediction values come from a PredictionParameterisation object.
  # This is also referred to by the Target function, but it makes sense for
  # Refinery to be able to refer to it directly. So refinery should keep a
  # separate link to its PredictionParameterisation.

  def __init__(self, target, prediction_parameterisation, log = None,
               verbosity = 0, track_step = False,
               track_gradient = False, track_parameter_correlation = False,
               track_out_of_sample_rmsd = False,
               max_iterations = None):

    # reference to PredictionParameterisation and Target objects
    self._parameters = prediction_parameterisation
    self._target = target

    # initial parameter values
    self.x = flex.double(self._parameters.get_param_vals())
    self.old_x = None

    # undefined initial functional and gradients values
    self._f = None
    self._g = None
    self._jacobian = None

    # filename for an optional log file
    self._log = log

    self._verbosity = verbosity

    self._target_achieved = False

    self._max_iterations = max_iterations

    # attributes for journalling functionality, based on lstbx's
    # journaled_non_linear_ls class
    self.history = Journal()
    self.history.add_column("num_reflections")
    self.history.add_column("objective")#flex.double()
    if track_gradient:
      self.history.add_column("gradient")
    self.history.add_column("gradient_norm")#flex.double()
    if track_parameter_correlation:
      self.history.add_column("parameter_correlation")
    if track_step:
      self.history.add_column("solution")
    if track_out_of_sample_rmsd:
      self.history.add_column("out_of_sample_rmsd")
    self.history.add_column("solution_norm")#flex.double()
    self.history.add_column("parameter_vector")
    self.history.add_column("parameter_vector_norm")#flex.double()
    self.history.add_column("rmsd")

    self.prepare_for_step()

  def get_num_steps(self):
    return self.history.get_nrows() - 1

  def prepare_for_step(self):
    """Update the parameterisation and prepare the target function"""

    # set current parameter values
    self._parameters.set_param_vals(self.x)

    # do reflection prediction
    self._target.predict()

    return

  def update_journal(self):
    """Append latest step information to the journal attributes"""

    # add step quantities to journal
    self.history.add_row()
    self.history.set_last_cell("num_reflections", self._target.get_num_matches())
    self.history.set_last_cell("rmsd", self._target.rmsds())
    self.history.set_last_cell("parameter_vector", self._parameters.get_param_vals())
    self.history.set_last_cell("objective", self._f)
    if self.history.has_key("gradient"):
      self.history.set_last_cell("gradient", self._g)
    if self.history.has_key("parameter_correlation"):
      if self._jacobian is not None:
        self.history.set_last_cell("parameter_correlation",
          self._packed_corr_mat(self._jacobian))
    if self.history.has_key("out_of_sample_rmsd"):
      preds = self._target.predict_for_free_reflections()
      self.history.set_last_cell("out_of_sample_rmsd",
        self._target.rmsds_for_reflection_table(preds))
    return

  @staticmethod
  def _packed_corr_mat(m):
    """Return a 1D flex array containing the upper diagonal values of the
    correlation matrix calculated between columns of 2D matrix m"""

    try: # convert matrices of type scitbx_sparse_ext.matrix
      m = m.as_dense_matrix()
    except AttributeError:
      pass
    ncol = m.all()[1]
    packed_len = (ncol*(ncol + 1)) // 2
    i = 0
    tmp = flex.double(packed_len)
    for col1 in range(ncol):
      for col2 in range(col1, ncol):
        tmp[i] = flex.linear_correlation(m.matrix_copy_column(col1),
                                     m.matrix_copy_column(col2)).coefficient()
        i += 1

    return tmp

  def get_correlation_matrix_for_step(self, step):
    """Decompress and return the full 2D correlation matrix between columns of
    the Jacobian that was stored in the journal at the given step number. If
    not available, return None"""

    if self.history.has_key("parameter_correlation") is False: return None
    try:
      packed = self.history["parameter_correlation"][step]
    except IndexError:
      return None
    if packed is None: return None
    nparam = len(self.x)
    corr_mat = flex.double(flex.grid(nparam, nparam))
    i = 0
    for row in range(nparam):
      for col in range(row, nparam):
        corr_mat[row, col] = packed[i]
        i += 1
    corr_mat.matrix_copy_upper_to_lower_triangle_in_place()
    return corr_mat

  def test_for_termination(self):
    """Return True if refinement should be terminated"""

    # Basic version delegate to the Target class. Derived classes may
    # implement other termination criteria
    self._target_achieved = self._target.achieved()

    return self._target_achieved

  def test_rmsd_convergence(self):
    """Test for convergence of RMSDs"""

    # http://en.wikipedia.org/wiki/
    # Non-linear_least_squares#Convergence_criteria
    try:
      r1 = self.history["rmsd"][-1]
      r2 = self.history["rmsd"][-2]
    except IndexError:
      return False

    tests = [abs((e[1] - e[0])/e[1]) < 0.0001 if e[1] > 0 else True for e in zip(r1, r2)]

    return all(tests)

  def test_objective_increasing_but_not_nref(self):
    """Test for an increase in the objective value between steps. This
    could be caused simply by the number of matches between observations
    and predictions increasing. However, if the number of matches stayed
    the same or reduced then this is a bad sign."""

    try:
      l1 = self.history["objective"][-1]
      l2 = self.history["objective"][-2]
      n1 = self.history["num_reflections"][-1]
      n2 = self.history["num_reflections"][-2]
    except IndexError:
      return False

    return l1 > l2 and n1 <= n2

  def run(self):
    """
    To be implemented by derived class. It is expected that each step of
    refinement be preceeded by a call to prepare_for_step and followed by
    calls to update_journal and test_for_termination (in that order).
    """

    # Specify a minimizer and its parameters, and run
    raise NotImplementedError()

class AdaptLbfgs(Refinery):
  """Adapt Refinery for L-BFGS minimiser"""

  def __init__(self, *args, **kwargs):

    Refinery.__init__(self, *args, **kwargs)

    self._termination_params = lbfgs.termination_parameters(
        max_iterations = self._max_iterations)

    import cStringIO
    self._log_string = cStringIO.StringIO

    return

  def compute_functional_and_gradients(self):

    self.prepare_for_step()

    # compute target function and its gradients
    self._f, self._g = self._target.compute_functional_and_gradients()

    return self._f, flex.double(self._g)

  def callback_after_step(self, minimizer):
    """
    Do journalling, evaluate rmsds and return True if the target is
    reached to terminate the refinement.
    """

    self.update_journal()
    debug("Step %d", self.history.get_nrows() - 1)

    if self.test_for_termination():
      self.history.reason_for_termination = TARGET_ACHIEVED
      return True

    if self.test_rmsd_convergence():
      self.history.reason_for_termination = RMSD_CONVERGED
      return True

    return False

  def run_lbfgs(self, curvatures=False):
    """
    Run the minimiser, keeping track of its log.
    """

    ref_log = self._log_string()
    if curvatures: self.diag_mode = "always"
    self.minimizer = lbfgs.run(target_evaluator=self,
        termination_params=self._termination_params,
        log=ref_log)

    log = ref_log.getvalue()
    if self._log:
      f = open(self._log, "a")
      f.write(log)
      f.close()
    ref_log.close()

    pos = log.rfind("lbfgs minimizer stop: ")
    if pos >= 0:
      msg = log[pos:].splitlines()[0]
      if self.history.reason_for_termination:
        self.history.reason_for_termination += "\n"
        self.history.reason_for_termination += msg
      else: self.history.reason_for_termination = msg

    if self.minimizer.error:
      self.history.reason_for_termination = self.minimizer.error

    return

class SimpleLBFGS(AdaptLbfgs):
  """Refinery implementation, using cctbx LBFGS with basic settings"""

  def run(self):

    return self.run_lbfgs(curvatures=False)

class LBFGScurvs(AdaptLbfgs):
  """Refinery implementation using cctbx LBFGS with curvatures"""

  def run(self):

    return self.run_lbfgs(curvatures=True)

  def compute_functional_gradients_diag(self):

    f, g = self.compute_functional_and_gradients()
    curvs = self.curvatures()

    diags = 1. / curvs

    if self._verbosity > 2:
      msg = "  curv: " +  "%.5f " * len(tuple(curvs))
      debug(msg, *curvs)

    return self._f, flex.double(self._g), diags

  def curvatures(self):

    # This relies on compute_functional_and_gradients being called first
    # (in order to set the parameters and update predictions).
    return(flex.double(self._target.curvatures()))


class AdaptLstbx(
    Refinery,
    normal_eqns.non_linear_ls,
    normal_eqns.non_linear_ls_mixin):
  """Adapt Refinery for lstbx"""

  def __init__(self, target, prediction_parameterisation, log=None,
               verbosity = 0, track_step = False, track_gradient = False,
               track_parameter_correlation = False,
               track_out_of_sample_rmsd = False, max_iterations = None):

    Refinery.__init__(self, target, prediction_parameterisation,
             log=log, verbosity=verbosity, track_step=track_step,
             track_gradient=track_gradient,
             track_parameter_correlation=track_parameter_correlation,
             track_out_of_sample_rmsd=track_out_of_sample_rmsd,
             max_iterations=max_iterations)

    # required for restart to work (do I need that method?)
    self.x_0 = self.x.deep_copy()

    normal_eqns.non_linear_ls.__init__(self, n_parameters = len(self._parameters))

  def restart(self):
    self.x = self.x_0.deep_copy()
    self.old_x = None

  def parameter_vector_norm(self):
    return self.x.norm()

  def build_up(self, objective_only=False):

    # code here to calculate the residuals. Rely on the target class
    # for this

    # I need to use the weights. They are the variances of the
    # observations... See http://en.wikipedia.org/wiki/Non-linear_least_squares
    # at 'diagonal weight matrix'

    # set current parameter values
    self.prepare_for_step()

    # Reset the state to construction time, i.e. no equations accumulated
    self.reset()

    block_num=0
    while not self._target.finished_residuals_and_gradients:
      # get calculations from the target
      residuals, self._jacobian, weights = \
          self._target.compute_residuals_and_gradients(block_num)
      block_num+=1

      if objective_only:
        self.add_residuals(residuals, weights)
      else:
        self.add_equations(residuals, self._jacobian, weights)

  def step_forward(self):
    self.old_x = self.x.deep_copy()
    self.x += self.step()

  def step_backward(self):
    if self.old_x is None:
      return False
    else:
      self.x, self.old_x = self.old_x, None
      return True

  def finalise(self):
    """perform various post-run tasks"""

    # it is possible to get here with zero steps taken by the minimiser. For
    # example by failing for the MAX_TRIAL_ITERATIONS reason before any forward
    # steps are taken with the LevMar engine. If so the below is invalid,
    # so return early
    if self.history.get_nrows() == 0: return None

    # invert normal matrix from N^-1 = (U^-1)(U^-1)^T
    cf_inv = self.cf.matrix_packed_u_as_upper_triangle().\
        matrix_inversion()
    nm_inv = cf_inv.matrix_multiply_transpose(cf_inv)

    # keep the estimated parameter variance-covariance matrix
    self.parameter_var_cov = \
        self.history["reduced_chi_squared"][-1] * nm_inv
    # send this back to the models to calculate their uncertainties
    self._parameters.calculate_model_state_uncertainties(
      self.parameter_var_cov)

    # send parameter variances back to the parameter classes
    # themselves, for reporting purposes and for building restraints
    # based on existing parameterisations.
    s2 = self.parameter_var_cov.matrix_diagonal()
    assert s2.all_ge(0.0)
    s = flex.sqrt(s2)
    self._parameters.set_param_esds(s)

    return

  def _print_normal_matrix(self):
    """Print the full normal matrix at the current step. For debugging only"""
    debug("The normal matrix for the current step is:")
    debug(self.normal_matrix_packed_u().\
          matrix_packed_u_as_symmetric().\
          as_scitbx_matrix().matlab_form(format=None,
          one_row_per_line=True))
    debug("\n")

class GaussNewtonIterations(AdaptLstbx, normal_eqns_solving.iterations):
  """Refinery implementation, using lstbx Gauss Newton iterations"""

  # defaults that may be overridden
  gradient_threshold = 1.e-10
  step_threshold = None
  damping_value = 0.0007
  max_shift_over_esd = 15
  convergence_as_shift_over_esd = 1e-5

  def __init__(self, target, prediction_parameterisation, log=None,
               verbosity=0, track_step=False, track_gradient=False,
               track_parameter_correlation=False,
               track_out_of_sample_rmsd=False,
               max_iterations=20, **kwds):

    AdaptLstbx.__init__(self, target, prediction_parameterisation,
             log=log, verbosity=verbosity, track_step=track_step,
             track_gradient=track_gradient,
             track_parameter_correlation=track_parameter_correlation,
             track_out_of_sample_rmsd=track_out_of_sample_rmsd,
             max_iterations=max_iterations)

    # add an attribute to the journal
    self.history.add_column("reduced_chi_squared")#flex.double()

    # adopt any overrides of the defaults above
    libtbx.adopt_optional_init_args(self, kwds)

  def run(self):
    self.n_iterations = 0

    # prepare for first step
    self.build_up()

    # return early if refinement is not possible
    if self.dof < 1:
      self.history.reason_for_termination = DOF_TOO_LOW
      return

    while True:

      # set functional and gradients for the step (to add to the history)
      self._f = self.objective()
      self._g = -self.opposite_of_gradient()

      # cache some items for the journal prior to solve
      pvn = self.parameter_vector_norm()
      gn = self.opposite_of_gradient().norm_inf()

      # debugging
      #if self._verbosity > 3: self._print_normal_matrix()

      # solve the normal equations
      self.solve()

      # standard journalling
      self.update_journal()
      debug("Step %d", self.history.get_nrows() - 1)

      # add cached items to the journal
      self.history.set_last_cell("parameter_vector_norm", pvn)
      self.history.set_last_cell("gradient_norm", gn)

      # extra journalling post solve
      if self.history.has_key("solution"):
        self.history.set_last_cell("solution", self.actual.step().deep_copy())
      self.history.set_last_cell("solution_norm", self.step().norm())
      self.history.set_last_cell("reduced_chi_squared", self.chi_sq())

      # test termination criteria
      if self.test_for_termination():
        self.history.reason_for_termination = TARGET_ACHIEVED
        break

      if self.test_rmsd_convergence():
        self.history.reason_for_termination = RMSD_CONVERGED
        break

      if self.had_too_small_a_step():
        self.history.reason_for_termination = STEP_TOO_SMALL
        break

      if self.test_objective_increasing_but_not_nref():
        self.history.reason_for_termination = OBJECTIVE_INCREASE
        if self.step_backward():
          self.history.reason_for_termination += ". Parameters set back one step"
        self.prepare_for_step()
        break

      if self.n_iterations == self._max_iterations:
        self.history.reason_for_termination = MAX_ITERATIONS
        break

      # prepare for next step
      self.step_forward()
      self.n_iterations += 1
      self.build_up()

    self.cf = self.step_equations().cholesky_factor_packed_u()
    self.finalise()

    return


class LevenbergMarquardtIterations(GaussNewtonIterations):
  """Refinery implementation, employing lstbx Levenberg Marquadt
  iterations"""

  tau = 1e-3

  class mu(libtbx.property):
    def fget(self):
      return self._mu
    def fset(self, value):
      self._mu = value

  def run(self):

    # add an attribute to the journal
    self.history.add_column("mu")
    self.history.add_column("nu")

    #FIXME need a much neater way of doing this stuff through
    #inheritance
    # set max iterations if not already.
    if self._max_iterations is None:
      self._max_iterations = 20

    self.n_iterations = 0
    nu = 2
    self.build_up()

    # return early if refinement is not possible
    if self.dof < 1:
      self.history.reason_for_termination = DOF_TOO_LOW
      return

    a = self.normal_matrix_packed_u()
    self.mu = self.tau*flex.max(a.matrix_packed_u_diagonal())

    while True:

      # set functional and gradients for the step
      self._f = self.objective()
      self._g = -self.opposite_of_gradient()

      # cache some items for the journal prior to solve
      pvn = self.parameter_vector_norm()
      gn = self.opposite_of_gradient().norm_inf()

      # debugging
      #if self._verbosity > 3: self._print_normal_matrix()

      a.matrix_packed_u_diagonal_add_in_place(self.mu)

      # solve the normal equations
      self.solve()

      # keep the cholesky factor for ESD calculation if we end this step. Doing
      # it here ensures the normal equations are solved (cholesky_factor_packed_u
      # can only be called if that is the case)
      self.cf = self.step_equations().cholesky_factor_packed_u().deep_copy()

      # standard journalling
      self.update_journal()
      debug("Step %d", self.history.get_nrows() - 1)

      # add cached items to the journal
      self.history.set_last_cell("parameter_vector_norm", pvn)
      self.history.set_last_cell("gradient_norm", gn)

      # extra journalling post solve
      self.history.set_last_cell("mu", self.mu)
      self.history.set_last_cell("nu", nu)
      if self.history.has_key("solution"):
        self.history.set_last_cell("solution", self.actual.step().deep_copy())
      self.history.set_last_cell("solution_norm", self.step().norm())
      self.history.set_last_cell("reduced_chi_squared", self.chi_sq())

      # test termination criteria before taking the next forward step
      if self.had_too_small_a_step():
        self.history.reason_for_termination = STEP_TOO_SMALL
        break
      if self.test_for_termination():
        self.history.reason_for_termination = TARGET_ACHIEVED
        break
      if self.test_rmsd_convergence():
        self.history.reason_for_termination = RMSD_CONVERGED
        break
      if self.n_iterations == self._max_iterations:
        self.history.reason_for_termination = MAX_ITERATIONS
        break

      h = self.step()
      expected_decrease = 0.5*h.dot(self.mu*h - self._g)
      self.step_forward()
      self.n_iterations += 1
      self.build_up(objective_only=True)
      objective_new = self.objective()
      actual_decrease = self._f - objective_new
      rho = actual_decrease/expected_decrease
      if rho > 0:
        self.mu *= max(1/3, 1 - (2*rho - 1)**3)
        nu = 2
      else:
        self.step_backward()
        self.history.del_last_row()
        if nu >= 8192:
          self.history.reason_for_termination = MAX_TRIAL_ITERATIONS
          break
        self.mu *= nu
        nu *= 2

      # prepare for next step
      self.build_up()

    self.finalise()

    return
