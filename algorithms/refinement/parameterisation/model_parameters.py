#
#  Copyright (C) (2013) STFC Rutherford Appleton Laboratory, UK.
#
#  Author: David Waterman.
#
#  This code is distributed under the BSD license, a copy of which is
#  included in the root directory of this package.
#

from __future__ import division
import abc

class Parameter(object):
  """A class to help formalise what a parameter is. A Parameter must
  have a numerical value (either a length or an angle). It may also
  have a vector axis which provides context for what that number
  means.

  Together the values and axes of a set of parameters' can be
  used to compose the state of a model. For example, the value might be
  a rotation angle, with the axis of rotation providing the context.

  A slot is also provided for the estimated standard deviation of the
  value, which may be of use in future. Currently, whenever the
  parameter value is set, the esd is reset to None. So this must be
  set separately, and after the parameter value if it is required"""

  def __init__(self, value, axis = None, ptype = None, name = "Parameter"):
    self._value = value
    self._esd = None
    self._axis = axis
    self._ptype = ptype
    self._name = name
    self._fixed = False

    return

  @property
  def value(self):
    return self._value

  @property
  def name(self):
    return self._name

  @value.setter
  def value(self, val):
    self._value = val
    self._esd = None

  @property
  def esd(self):
    return self._esd

  @esd.setter
  def esd(self, esd):
    self._esd = esd

  @property
  def param_type(self):
    return self._ptype

  @property
  def axis(self):
    return self._axis

  def get_fixed(self):
    return self._fixed

  def fix(self):
    self._fixed = True

  def unfix(self):
    self._fixed = False

  def __str__(self):

    msg = "Parameter " + self.name + ":\n"
    try:
      msg += "    Type: " + self.param_type + "\n"
    except TypeError:
      msg += "    Type: " + str(self.param_type) + "\n"
    try:
      msg += "    Axis: (%5.3f, %5.3f, %5.3f)" % tuple(self.axis) + "\n"
    except TypeError:
      msg += "    Axis: " + str(self.axis) + "\n"
    msg += "    Value: %5.3f" % self.value + "\n"
    try:
      msg += "    Sigma: %5.3f" % self.esd + "\n"
    except TypeError:
      msg += "    Sigma: " + str(self.esd) + "\n"

    return msg

class ModelParameterisation(object):
  """An abstract interface that model elements, such as the detector
  model, the source model, etc. should adhere to in order to compose
  their state from their parameters, access their parameters, and
  derivatives of their state wrt their parameters, taking into account
  whether particular parameters are fixed or free.

  It is possible to parameterise a model with multiple states. The
  most obvious example is a detector with multiple panels. Each panel
  has its own matrix describing its geometrical 'state'. One set of
  parameters is used to compose all states and calculate all
  derivatives of these states."""

  __metaclass__  = abc.ABCMeta

  def __init__(self, models, initial_state, param_list, experiment_ids,
               is_multi_state=False):
    assert(isinstance(param_list, list))
    self._initial_state = initial_state
    self._models = models
    self._param = list(param_list)
    self._total_len = len(self._param)
    self._num_free = None
    self._dstate_dp = [None] * len(param_list)
    self._is_multi_state = is_multi_state
    self._exp_ids = experiment_ids
    return

  def num_free(self):
    """the number of free parameters"""

    if self._num_free is None:
      self._num_free = sum(not x.get_fixed() for x in self._param)
    return self._num_free

  def num_total(self):
    """the total number of parameters, both fixed and free"""
    return self._total_len

  def get_experiment_ids(self):
    """the experiments parameterised by this ModelParameterisation"""
    return self._exp_ids

  @abc.abstractmethod
  def compose(self):
    """compose the current model state from its initial state and its
    parameter list. Also calculate the derivatives of the state wrt
    each parameter in the list. Should be called automatically once
    parameters are updated, e.g. at the end of each refinement cycle"""

    pass

  def get_params(self, only_free = True):
    """Return the internal list of parameters. It is intended that this
    function be used for reporting parameter attributes, not for modifying
    them.

    If only_free, any fixed parameters are filtered from the returned list.
    Otherwise all parameters are returned"""

    if only_free:

      return [x for x in self._param if not x.get_fixed()]

    else:
      return [x for x in self._param]

  def get_param_vals(self, only_free = True):
    """export the values of the internal list of parameters as a
    sequence of floats.

    If only_free, the values of fixed parameters are filtered from the
    returned list. Otherwise all parameter values are returned"""

    if only_free:

      return [x.value for x in self._param if not x.get_fixed()]

    else:
      return [x.value for x in self._param]

  def get_param_names(self, only_free = True):
    """export the names of the internal list of parameters

    If only_free, the names of fixed parameters are filtered from the
    returned list. Otherwise all parameter names are returned"""

    # FIXME combine functionality with get_param_vals by returning a named,
    # ordered list?

    if only_free:
      return [x.name for x in self._param if not x.get_fixed()]

    else:
      return [x.name for x in self._param]

  def set_param_vals(self, vals):
    """set the values of the internal list of parameters from a
    sequence of floats.

    Only free parameters can be set, therefore the length of vals must equal
    the value of num_free"""

    assert(len(vals) == self.num_free())

    v = iter(vals)
    for p in self._param:
      if not p.get_fixed(): # only set the free parameters
        p.value = v.next()

    # compose with the new parameter values
    self.compose()

    return

  def get_fixed(self):
    """return the list determining whether each parameter is fixed or not"""

    return [p.get_fixed() for p in self._param]


  def set_fixed(self, fix):
    """set parameters to be fixed or free"""

    assert(len(fix) == len(self._param))

    for f, p in zip(fix, self._param):
      if f: p.fix()
      else: p.unfix()

    # reset the cached number of free parameters
    self._num_free = None

    return

  @abc.abstractmethod
  def get_state(self, multi_state_elt=None):
    """return the current state of the model under parameterisation.
    This is required, for example, by the calculation of finite
    difference gradients.

    For a multi-state parameterisation, the requested state is
    selected passing an integer array index in multi_state_elt"""

    # To be implemented by the derived class, where it is clear what aspect
    # of the model under parameterisation is considered its state. The
    # type of this result should match the type of one element of the return
    # value of get_ds_dp.
    pass

  def get_ds_dp(self, only_free = True, multi_state_elt=None):
    """get a list of derivatives of the state wrt each parameter, as
    a list in the same order as the internal list of parameters.

    If only_free, the derivatives with respect to fixed parameters
    are omitted from the returned list. Otherwise a list for all
    parameters is returned, with values of 0.0 for the fixed
    parameters.

    For a multi-state parameterisation, the requested state is
    selected passing an integer array index in multi_state_elt"""

    if only_free:
      grads = [ds_dp for ds_dp, p in zip(self._dstate_dp, self._param) \
              if not p.get_fixed()]
    else:
      grads = [0. * ds_dp if p.get_fixed() else ds_dp \
                  for ds_dp, p in zip(self._dstate_dp, self._param)]

    if multi_state_elt is not None and self._is_multi_state:
      return [e[multi_state_elt] for e in grads]
    else:
      return grads
