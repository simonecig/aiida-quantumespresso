from aiida import orm
from aiida.plugins import DataFactory

from aiida_quantumespresso.calculations.namelists import NamelistsCalculation

LegacyUpfData = DataFactory("upf")
UpfData = DataFactory("pseudo.upf")


class Pw4gwwCalculation(NamelistsCalculation):
    """`CalcJob` implementation for the pw4gww.x code of Quantum ESPRESSO."""

    _default_namelists = ["INPUTPW4GWW"]
    # _internal_retrieve_list = [('./out/*', '.', 0)]  # retrieve EVERYTHING
    _internal_retrieve_list = []  # stuff to retrieve
    _blocked_keywords = [
        (
            "INPUTPW4GWW",
            "prefix",
            NamelistsCalculation._INPUT_SUBFOLDER + NamelistsCalculation._PREFIX,
        ),
    ]
    _default_parser = "quantumespresso.pw4gww"

    @classmethod
    def define(cls, spec):
        """Define the process specification."""

        super().define(spec)
        spec.input(
            "parent_folder", valid_type=(orm.RemoteData, orm.FolderData), required=True
        )
        spec.input("cluster", valid_type=orm.Bool, required=False)
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

    def prepare_for_submission(self, folder):
        if "cluster" in self.inputs:  # FIXME: always true... or not?
            # retrieve EVERYTHING
            self._internal_retrieve_list = ["out", "aiida-bands.dat"]
        calcinfo = super().prepare_for_submission(folder)
        return calcinfo
