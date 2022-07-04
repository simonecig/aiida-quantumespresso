import os

from aiida import orm
from aiida.common import datastructures, exceptions
from aiida.orm import FolderData, RemoteData, SinglefileData, load_node
from aiida.plugins import DataFactory

from aiida_quantumespresso.calculations import _lowercase_dict, _pop_parser_options, _uppercase_dict
from aiida_quantumespresso.calculations.namelists import NamelistsCalculation

LegacyUpfData = DataFactory("upf")
UpfData = DataFactory("pseudo.upf")


class EasyanalyserCalculation(NamelistsCalculation):
    """`CalcJob` implementation for the Easyanalyser.py code of QE."""

    _DEFAULT_SECOND_INPUT_FILE = "easy.in"
    _DEFAULT_INPUT_FILE = "aiida_fit.in"
    _default_namelists = ["INPUTGWW"]
    _RESULT_FILE = "results.out"
    _DEFAULT_OUTPUT_FILE = "easy.out"
    _internal_retrieve_list = ["fitdir/results.out"]  # stuff to retrieve
    _default_parser = "quantumespresso.easyanalyser"

    @classmethod
    def define(cls, spec):
        """Define the process specification."""

        super().define(spec)
        spec.input("python_parameters", valid_type=orm.Dict)
        spec.input("parameters", valid_type=orm.Dict)
        spec.input("metadata.options.withmpi", valid_type=bool, default=False)
        spec.input(
            "pw4gww_node", valid_type=(orm.Int, orm.Str, orm.List), required=True
        )
        spec.input(
            "parent_folder",
            valid_type=(orm.RemoteData, orm.FolderData, orm.List),
            required=False,
        )
        spec.inputs["metadata"]["options"]["resources"].default = {"num_machines": 1}
        spec.output("output_parameters", valid_type=orm.Dict)
        spec.default_output_node = "output_parameters"
        spec.exit_code(
            310,
            "ERROR_OUTPUT_STDOUT_READ",
            message="The stdout output file could not be read.",
        )
        spec.exit_code(
            312,
            "ERROR_OUTPUT_STDOUT_INCOMPLETE",
            message="The stdout output file was incomplete probably because the calculation got interrupted.",
        )
        spec.exit_code(
            310,
            "ERROR_OUTPUT_STDOUT_PARSE",
            message="The stdout output could not be interpreted.",
        )  # TODO: improve
        spec.exit_code(330, "ERROR_READING_RESULT_FILE", message="")

    @staticmethod
    def generate_second_input_file(parameters):
        """Generate a second input_file content given a dict of parameters.

        Like `generate_input_file` but for when fortran namelists aren't needed
        TODO: modify easyanalyser to work with fortran namelists instead

        :param parameters: 'dict' containing the parameters to be used
            e.g.: {'key1: value1, 'key2': value2}

        :return: 'str' containing the input_file content in a plain text.
        """

        file_lines = []
        for key, value in parameters.items():
            file_lines.append(f"{key}={value}")
        return "\n".join(file_lines)


    def prepare_for_submission(self, folder):
        """FIXME: this method is very similar to the one already implemented
        inside of the parent class `namelist`. However, we can't simply call:
        `super().prepare_for_submission(folder)`
        because we need to drastically change (among other things)
        the local_copy_list, which by default is unable to retrieve
        subfolders included in the FolderData provided as input.
        When aiida will allow to transfer data from different machine inside
        of the remote_copy_list,
        this workaround will not be necessary.

        """
        # pylint: disable=too-many-branches,too-many-statements
        if "settings" in self.inputs:
            settings = _uppercase_dict(
                self.inputs.settings.get_dict(), dict_name="settings"
            )
        else:
            settings = {}

        following_text = self._get_following_text()
        parent_node_pk = self.inputs.get("pw4gww_node", None)

        # pylint: disable=too-many-branches,too-many-statements
        if "parameters" in self.inputs:
            parameters = _uppercase_dict(
                self.inputs.parameters.get_dict(), dict_name="parameters"
            )
            parameters = {
                k: _lowercase_dict(v, dict_name=k) for k, v in parameters.items()
            }
        else:
            parameters = {}

        # =================== NAMELISTS AND CARDS ========================
        try:
            namelists_toprint = settings.pop("NAMELISTS")
            if not isinstance(namelists_toprint, list):
                raise exceptions.InputValidationError(
                    "The 'NAMELISTS' value, if specified in the settings input node, must be a list of strings"
                )
        except KeyError:  # list of namelists not specified; do automatic detection
            namelists_toprint = self._default_namelists

        parameters = self.set_blocked_keywords(parameters)
        parameters = self.filter_namelists(parameters, namelists_toprint)
        file_content = self.generate_input_file(parameters)
        file_content += "\n" + following_text
        input_filename = self.inputs.metadata.options.input_filename
        with folder.open(input_filename, "w") as infile:
            infile.write(file_content)

        symlink = settings.pop("PARENT_FOLDER_SYMLINK", False)

        remote_copy_list = []
        local_copy_list = []
        remote_symlink_list = []

        file_content = self.generate_second_input_file(
            self.inputs.python_parameters.get_dict()
        )
        input_filename = self._DEFAULT_SECOND_INPUT_FILE
        with folder.open(input_filename, "w") as infile:
            infile.write(file_content)

        ptr = remote_symlink_list if symlink else remote_copy_list

        def recursive_copy(folder, obj):
            for filename in obj.list_object_names(folder):
                name_and_path = os.path.join(folder, filename)
                if "DIRECTORY" in str(obj.get_object(name_and_path).file_type):
                    recursive_copy(name_and_path, obj)
                else:
                    local_copy_list.append((obj.uuid, name_and_path, name_and_path))


        if isinstance(parent_node_pk, orm.List):
            parent_calc_folder = []
            for node_pk in parent_node_pk.get_list():
                parent_calc_folder.append(load_node(node_pk).outputs.retrieved)
        else:
            parent_calc_folder = load_node(parent_node_pk.value).outputs.remote_folder

        if isinstance(parent_calc_folder, RemoteData):
            parent_calc_out_subfolder = settings.pop(
                "PARENT_CALC_OUT_SUBFOLDER", self._INPUT_SUBFOLDER
            )
            ptr.append(
                (
                    parent_calc_folder.computer.uuid,
                    os.path.join(
                        parent_calc_folder.get_remote_path(),
                        parent_calc_out_subfolder,
                    ),
                    self._OUTPUT_SUBFOLDER,
                )
            )

        elif isinstance(parent_calc_folder, FolderData):
            recursive_copy("", parent_calc_folder)

        elif isinstance(parent_calc_folder, list):
            for folder in parent_calc_folder:
                recursive_copy("", folder)

        elif isinstance(parent_calc_folder, SinglefileData):
            single_file = parent_calc_folder
            local_copy_list.append(
                (single_file.uuid, single_file.filename, single_file.filename)
            )

        codeinfo = datastructures.CodeInfo()
        codeinfo.cmdline_params = settings.pop("CMDLINE", [])
        codeinfo.stdin_name = self.inputs.metadata.options.input_filename
        codeinfo.stdout_name = self.inputs.metadata.options.output_filename
        codeinfo.code_uuid = self.inputs.code.uuid

        calcinfo = datastructures.CalcInfo()
        calcinfo.uuid = str(self.uuid)
        calcinfo.codes_info = [codeinfo]
        calcinfo.local_copy_list = local_copy_list
        calcinfo.remote_copy_list = remote_copy_list
        calcinfo.remote_symlink_list = remote_symlink_list

        # Retrieve by default the output file and the xml file
        calcinfo.retrieve_list = []
        calcinfo.retrieve_list.append(self.inputs.metadata.options.output_filename)
        calcinfo.retrieve_list += settings.pop("ADDITIONAL_RETRIEVE_LIST", [])
        calcinfo.retrieve_list += self._internal_retrieve_list

        calcinfo.retrieve_temporary_list = self._retrieve_temporary_list
        calcinfo.retrieve_singlefile_list = self._retrieve_singlefile_list

        # We might still have parser options in the settings dictionary: pop them.
        _pop_parser_options(self, settings)

        if settings:
            unknown_keys = ", ".join(list(settings.keys()))
            raise exceptions.InputValidationError(
                f"`settings` contained unexpected keys: {unknown_keys}"
            )

        def save_output_to_file(fname, node, mode):
            with folder.open(fname, mode) as f:
                f.write(node.outputs.retrieved.get_object_content("aiida.out"))

        pw4gww_output_filename = "aiida.out"
        if isinstance(parent_node_pk, orm.List):
            out = ""
            for node_pk in parent_node_pk:
                new_out = load_node(node_pk).outputs.retrieved.get_object_content("aiida.out")
                out = "\n".join([out, new_out])
            with folder.open(pw4gww_output_filename, "w") as file:
                file.write(out)

                # save_output_to_file(pw4gww_output_filename, load_node(node_pk), "a")
        else:
            save_output_to_file(
                pw4gww_output_filename, load_node(parent_node_pk.value), "w"
            )

        return calcinfo
