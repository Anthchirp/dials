#
#  Copyright (C) (2013) STFC Rutherford Appleton Laboratory, UK.
#
#  Author: David Waterman.
#
#  This code is distributed under the BSD license, a copy of which is
#  included in the root directory of this package.
#

#### Python and general cctbx imports

from __future__ import division
from scitbx import matrix

#### Import model parameterisations

#from dials.algorithms.refinement.parameterisation.detector_parameters import \
#    DetectorParameterisationSinglePanel
#from dials.algorithms.refinement.parameterisation.beam_parameters import \
#    BeamParameterisationOrientation
#from dials.algorithms.refinement.parameterisation.crystal_parameters import \
#    CrystalOrientationParameterisation, CrystalUnitCellParameterisation
from cctbx.array_family import flex
from dials_refinement_helpers_ext import *

class ParameterReporter(object):
    """
    Keeps a record of all the ModelParameterisations and
    ScanVaryingModelParameterisations present and provides access to their
    Parameters and ScanVaryingParameterSets for reporting purposes.

    It is assumed that the provided model parameterisations will be one of four
    types:

    * Detector parameterisation
    * Beam parameterisation
    * Crystal orientation parameterisation
    * Crystal unit cell parameterisation
    """

    def __init__(self,
                 detector_parameterisations = None,
                 beam_parameterisations = None,
                 xl_orientation_parameterisations = None,
                 xl_unit_cell_parameterisations = None):

        # Keep references to all parameterised models
        self._detector_parameterisations = detector_parameterisations
        self._beam_parameterisations = beam_parameterisations
        self._xl_orientation_parameterisations = \
            xl_orientation_parameterisations
        self._xl_unit_cell_parameterisations = \
            xl_unit_cell_parameterisations

        self._length = self._len()

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

    def _indent(self, string):
        return "\n".join(["    " + e for e in str(string).split("\n")])

    def __str__(self):

        s =  "Parameter Report\n"
        s += "----------------\n"
        if self._detector_parameterisations:
            s += "Detector parameters:\n"
            det_plists = [x.get_params() for x in self._detector_parameterisations]
            params = [x for l in det_plists for x in l]
            for p in params:
                tmp = self._indent(p)
                s += tmp + "\n"

        if self._beam_parameterisations:
            s += "Beam parameters:\n"
            beam_plists = [x.get_params() for x in self._beam_parameterisations]
            params = [x for l in beam_plists for x in l]
            for p in params:
                tmp = self._indent(p)
                s += tmp + "\n"

        if self._xl_orientation_parameterisations:
            s += "Crystal orientation parameters:\n"
            xlo_plists = [x.get_params() for x in self._xl_orientation_parameterisations]
            params = [x for l in xlo_plists for x in l]
            for p in params:
                tmp = self._indent(p)
                s += tmp + "\n"

        if self._xl_unit_cell_parameterisations:
            s += "Crystal unit cell parameters:\n"
            xluc_plists = [x.get_params() for x in self._xl_unit_cell_parameterisations]
            params = [x for l in xluc_plists for x in l]
            for p in params:
                tmp = self._indent(p)
                s += tmp + "\n"

        return s

    def varying_params_vs_image_number(self, image_range):
        """Write a table of scan-varying parameter values vs image number to
        disk, if scan-varying parameters are present. Return boolean, whether
        this table was written or not"""

        image_numbers = range(image_range[0], image_range[1] + 1)
        columns = [TableColumn("Image", image_numbers)]

        if self._detector_parameterisations:
            for parameterisation in self._detector_parameterisations:
                for p in parameterisation.get_params():
                    try:
                        vals = [parameterisation.get_smoothed_parameter_value(i, p) \
                                for i in image_numbers]
                        columns.append(TableColumn(p.name_stem, vals))
                    except AttributeError:
                        continue

        if self._beam_parameterisations:
            for parameterisation in self._beam_parameterisations:
                for p in parameterisation.get_params():
                    try:
                        vals = [parameterisation.get_smoothed_parameter_value(i, p) \
                                for i in image_numbers]
                        columns.append(TableColumn(p.name_stem, vals))
                    except AttributeError:
                        continue

        if self._xl_orientation_parameterisations:
            for parameterisation in self._xl_orientation_parameterisations:
                for p in parameterisation.get_params():
                    try:
                        vals = [parameterisation.get_smoothed_parameter_value(i, p) \
                                for i in image_numbers]
                        columns.append(TableColumn(p.name_stem, vals))
                    except AttributeError:
                        continue

        if self._xl_unit_cell_parameterisations:
            for parameterisation in self._xl_unit_cell_parameterisations:
                for p in parameterisation.get_params():
                    try:
                        vals = [parameterisation.get_smoothed_parameter_value(i, p) \
                                for i in image_numbers]
                        columns.append(TableColumn(p.name_stem, vals))
                    except AttributeError:
                        continue

        if len(columns) > 1:
            f = open("varying_params.dat","w")
            header = "\t".join([e.title for e in columns])
            f.write(header + "\n")
            for i in range(len(columns[0])):
                vals = "\t".join(["%.6f" % e.values[i] for e in columns])
                f.write(vals + "\n")
            f.close()
            return True

        else:
            return False

    # FIXME Don't need this?
    def get_params(self):
        """return a concatenated list of parameters from each of the components
        in the global model"""

        global_p_list = []
        if self._detector_parameterisations:
            det_plists = [x.get_params() for x in self._detector_parameterisations]
            params = [x for l in det_plists for x in l]
            global_p_list.extend(params)

        if self._beam_parameterisations:
            src_plists = [x.get_params() for x in self._beam_parameterisations]
            params = [x for l in src_plists for x in l]
            global_p_list.extend(params)

        if self._xl_orientation_parameterisations:
            xlo_plists = [x.get_params() for x
                          in self._xl_orientation_parameterisations]
            params = [x for l in xlo_plists for x in l]
            global_p_list.extend(params)

        if self._xl_unit_cell_parameterisations:
            xluc_plists = [x.get_params() for x
                           in self._xl_unit_cell_parameterisations]
            params = [x for l in xluc_plists for x in l]
            global_p_list.extend(params)

        return global_p_list

    # FIXME Don't need this?
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
            src_param_name_lists = [x.get_param_names() for x in \
                               self._beam_parameterisations]
            params = ["Source%d" % i + x for i, l \
                      in enumerate(src_param_name_lists) for x in l]
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

class TableColumn(object):
    """Bucket to store data to be used for constructing tables to print."""

    def __init__(self, title, values):

        self._title = title
        self._values = values

    def __len__(self):
        return len(self._values)

    @property
    def title(self):
        return self._title

    @property
    def values(self):
        return self._values
