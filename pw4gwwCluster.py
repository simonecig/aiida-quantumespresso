#!/usr/bin/env runaiida
from aiida import orm
from aiida.engine import ToContext, WorkChain
from aiida.plugins import CalculationFactory

EasyanalyserCalculation = CalculationFactory('quantumespresso.easyanalyser')
Pw4gwwCalculation = CalculationFactory('quantumespresso.pw4gww')
PwCalculation = CalculationFactory('quantumespresso.pw')


class Pw4gwwWorkChainCluster(WorkChain):

    @classmethod
    def define(cls, spec):
        """Define the process specification."""
        # yapf: disable
        super().define(spec)
        spec.input("pw_codes", valid_type=orm.List, required=True)
        spec.input("pw4gww_codes", valid_type=orm.List, required=True)

        spec.expose_inputs(PwCalculation, namespace='pw', exclude=("code"))
        spec.expose_inputs(Pw4gwwCalculation, namespace='pw4gww', exclude=('parent_folder', "code"))
        spec.expose_inputs(EasyanalyserCalculation, namespace='easyanalyser', exclude=('parent_folder', 'pw4gww_node'))

        spec.outline(
            cls.run_pw,
            cls.run_pw4gww,
            cls.run_easy,
            cls.results,
        )

        # spec.expose_outputs(EasyanalyserCalculation)

    def run_pw(self):
        inputs = self.exposed_inputs(PwCalculation, "pw")
        for i, code in enumerate(self.inputs.pw_codes.get_list()):
            pw_calc = self.submit(
                PwCalculation,
                code=orm.load_code(code),
                **inputs,
            )
            key = f"pw_calc_{i}"
            self.to_context(**{key: pw_calc})

    def run_pw4gww(self):
        inputs = self.exposed_inputs(Pw4gwwCalculation, "pw4gww")
        parameters = inputs.parameters.get_dict()
        parameters['INPUTPW4GWW']['easy_split_calc_n'] = len(self.inputs.pw4gww_codes.get_list())
        for i, code in enumerate(self.inputs.pw4gww_codes.get_list()):
            old_key = f"pw_calc_{i}"
            parameters['INPUTPW4GWW']['easy_split_calc_i'] = i+1 
            pw4gww_calc = self.submit(
                Pw4gwwCalculation,
                code=orm.load_code(code),
                parent_folder=self.ctx[old_key].outputs.remote_folder,
                parameters=orm.Dict(dict=parameters),
                cluster=orm.Bool(True),
                metadata=inputs.metadata
            )
            key = f"pw4gww_calc_{i}"
            self.to_context(**{key: pw4gww_calc})

    def run_easy(self):
        inputs = self.exposed_inputs(EasyanalyserCalculation, "easyanalyser")
        pw4gww_nodes = []
        for i, code in enumerate(self.inputs.pw4gww_codes.get_list()):
            key = f"pw4gww_calc_{i}"
            pw4gww_nodes.append(self.ctx[key].pk)
        easy_calc = self.submit(
            EasyanalyserCalculation,
            pw4gww_node=orm.List(list=pw4gww_nodes),
            **inputs
        )
        return ToContext(easy_calc=easy_calc)

    def results(self):
        pass
