import os

from cctbx import sgtbx, uctbx
from iotbx import file_reader
from libtbx import Auto
from libtbx.utils import Usage

import freephil.command_line
from freephil import tokenizer


class unit_cell_converter:
    phil_type = "unit_cell"

    def __str__(self):
        return self.phil_type

    def from_words(self, words, master):
        s = freephil.str_from_words(words=words)
        if s is None:
            return None
        if s is Auto:
            return Auto
        return uctbx.unit_cell(str(s))

    def as_words(self, python_object, master):
        if python_object is None:
            return [tokenizer.word(value="None")]
        if python_object is Auto:
            return [tokenizer.word(value="Auto")]
        return [tokenizer.word(value="%.10g" % v) for v in python_object.parameters()]


class space_group_converter:
    phil_type = "space_group"

    def __str__(self):
        return self.phil_type

    def from_words(self, words, master):
        symbol = freephil.str_from_words(words)
        if symbol is None:
            return None
        if symbol is Auto:
            return Auto
        return sgtbx.space_group_info(symbol=str(symbol))

    def as_words(self, python_object, master):
        if python_object is None:
            return [tokenizer.word(value="None")]
        if python_object is Auto:
            return [tokenizer.word(value="Auto")]
        return [tokenizer.word(value=str(python_object), quote_token='"')]


class atom_selection_converter(freephil.qstr_converters):

    phil_type = "atom_selection"

    def __str__(self):
        return self.phil_type

    def from_words(self, words, master):
        if len(words) == 1:
            word = words[0]
            if word.quote_token is not None:
                return word.value  # mainly for backward compatibility
        return freephil.qstr_converters.from_words(self, words, master)


default_converter_registry = freephil.extended_converter_registry(
    additional_converters=[
        unit_cell_converter,
        space_group_converter,
        atom_selection_converter,
    ]
)


def _parse(
    input_string=None,
    source_info=None,
    file_name=None,
    converter_registry=None,
    process_includes=False,
):
    if converter_registry is None:
        converter_registry = default_converter_registry
    return freephil.parse(
        input_string=input_string,
        source_info=source_info,
        file_name=file_name,
        converter_registry=converter_registry,
        process_includes=process_includes,
    )


parse = _parse


def read_default(
    caller_file_name,
    params_extension=".params",
    converter_registry=None,
    process_includes=True,
):
    if converter_registry is None:
        converter_registry = default_converter_registry
    return freephil.read_default(
        caller_file_name=caller_file_name,
        params_extension=params_extension,
        converter_registry=converter_registry,
        process_includes=process_includes,
    )


def process_command_line(args, master_string, parse=None):
    if parse is None:
        parse = _parse
    return freephil.process_command_line(
        args=args, master_string=master_string, parse=parse
    )


class process_command_line_with_files:
    def __init__(
        self,
        args,
        master_phil=None,
        master_phil_string=None,
        pdb_file_def=None,
        reflection_file_def=None,
        map_file_def=None,
        cif_file_def=None,
        seq_file_def=None,
        pickle_file_def=None,
        ncs_file_def=None,
        directory_def=None,
        integer_def=None,
        float_def=None,
        space_group_def=None,
        unit_cell_def=None,
        usage_string=None,
    ):
        assert (master_phil is not None) or (master_phil_string is not None)
        if master_phil_string is not None:
            assert master_phil is None
            master_phil = _parse(input_string=master_phil_string, process_includes=True)
        if usage_string is not None:
            if (len(args) == 0) or ("--help" in args):
                raise Usage(
                    """
%s

Full parameters:

%s"""
                    % (
                        usage_string,
                        master_phil.as_str(prefix="  ", attributes_level=1),
                    )
                )
        self.master = master_phil
        self.pdb_file_def = pdb_file_def
        self.reflection_file_def = reflection_file_def
        self.cif_file_def = cif_file_def
        self.cif_objects = []
        self.map_file_def = map_file_def
        self.seq_file_def = seq_file_def
        self.pickle_file_def = pickle_file_def
        self.ncs_file_def = ncs_file_def
        self.directory_def = directory_def
        self.integer_def = integer_def
        self.float_def = float_def
        self.space_group_def = space_group_def
        self.unit_cell_def = unit_cell_def
        self._type_counts = {}
        self._cache = {}
        cai = freephil.command_line.argument_interpreter(master_phil=self.master)
        self.unused_args = []
        self.work = cai.process_and_fetch(args=args, custom_processor=self)

    def get_file_type_count(self, file_type):
        return self._type_counts.get(file_type, 0)

    def __call__(self, arg):
        file_arg = None
        is_shelx_file = False
        if os.path.isfile(arg):
            file_arg = arg
        # handle SHELX format hack
        elif (
            arg.endswith("=hklf3")
            or arg.endswith("=hklf4")
            or arg.endswith("=amplitudes")
            or arg.endswith("=intensities")
        ):
            base_arg = "".join(arg.split("=")[:-1])
            if (base_arg != "") and os.path.isfile(base_arg):
                file_arg = arg
                is_shelx_file = True
        if file_arg is not None:
            f = file_reader.any_file(
                os.path.abspath(file_arg), raise_sorry_if_not_expected_format=True
            )
            if f.file_type is not None:
                if f.file_type not in self._type_counts:
                    self._type_counts[f.file_type] = 0
                self._type_counts[f.file_type] += 1
                self._cache[f.file_name] = f
            file_def_name = None
            if (f.file_type == "pdb") and (self.pdb_file_def is not None):
                file_def_name = self.pdb_file_def
            elif (f.file_type == "hkl") and (self.reflection_file_def is not None):
                file_def_name = self.reflection_file_def
            elif (f.file_type == "ccp4_map") and (self.map_file_def is not None):
                file_def_name = self.map_file_def
            elif (f.file_type == "cif") and (self.cif_file_def is not None):
                file_def_name = self.cif_file_def
                self.cif_objects.append((f.file_name, f.file_object.model()))
            elif (f.file_type == "seq") and (self.seq_file_def is not None):
                file_def_name = self.seq_file_def
            elif (f.file_type == "ncs") and (self.ncs_file_def is not None):
                file_def_name = self.ncs_file_def
            elif (f.file_type == "pkl") and (self.pickle_file_def is not None):
                file_def_name = self.pickle_file_def
            if file_def_name is not None:
                file_name = f.file_name
                if is_shelx_file:
                    file_name = file_arg
                return freephil.parse(f"{file_def_name}={file_name}")
            else:
                return False
        elif os.path.isdir(arg):
            if self.directory_def is not None:
                return freephil.parse(f"{self.directory_def}={arg}")
        else:
            int_value = float_value = None
            if self.integer_def is not None:
                try:
                    int_value = int(arg)
                except ValueError:
                    pass
                else:
                    return freephil.parse("%s=%d" % (self.integer_def, int_value))
            if self.float_def is not None:
                try:
                    float_value = float(arg)
                except ValueError:
                    pass
                else:
                    return freephil.parse(f"{self.float_def}={float_value:g}")
            if self.space_group_def is not None:
                try:
                    space_group_info = sgtbx.space_group_info(arg)
                except RuntimeError:  # XXX should really be ValueError
                    pass
                else:
                    return freephil.parse(f"{self.space_group_def}={space_group_info}")
            if (self.unit_cell_def is not None) and (arg.count(",") >= 2):
                try:
                    uc_params = tuple([float(x) for x in arg.split(",")])
                    unit_cell = uctbx.unit_cell(uc_params)
                except Exception:  # XXX should really be ValueError
                    pass
                else:
                    return freephil.parse(
                        "%s=%s"
                        % (
                            self.unit_cell_def,
                            ",".join(["%g" % x for x in unit_cell.parameters()]),
                        )
                    )
        return self.process_other(arg)

    def process_other(self, arg):
        self.unused_args.append(arg)
        return True

    def get_cached_file(self, file_name):
        return self._cache.get(file_name, None)

    def get_file(self, file_name, force_type=None):
        if file_name is None:
            return None
        input_file = self._cache.get(file_name)
        if input_file is None:
            input_file = file_reader.any_file(
                file_name, force_type=force_type, raise_sorry_if_errors=True
            )
        elif force_type is not None:
            input_file.assert_file_type(force_type)
        return input_file
