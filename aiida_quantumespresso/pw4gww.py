from aiida import orm
from aiida.engine import ToContext, WorkChain
from aiida.plugins import CalculationFactory

EasyanalyserCalculation = CalculationFactory('quantumespresso.easyanalyser')
Pw4gwwCalculation = CalculationFactory('quantumespresso.pw4gww')
PwCalculation = CalculationFactory('quantumespresso.pw')


class Pw4gwwWorkChain(WorkChain):

    @classmethod
    def define(cls, spec):
        """Define the process specification."""
        # yapf: disable
        super().define(spec)
        spec.expose_inputs(PwCalculation, namespace='pw')
        spec.expose_inputs(Pw4gwwCalculation, namespace='pw4gww', exclude='parent_folder')
        spec.expose_inputs(EasyanalyserCalculation, namespace='easyanalyser', exclude=('pw4gww_node'))
        # spec.inputs.validator = validate_inputs
        spec.outline(
            cls.run_pw,
            cls.run_pw4gww,
            cls.run_easy,
            cls.results,
        )

        # spec.expose_outputs(EasyanalyserCalculation)

    def run_pw(self):
        inputs = self.exposed_inputs(PwCalculation, "pw")
        pw_calc = self.submit(
            PwCalculation,
            **inputs
        )
        return ToContext(pw_calc=pw_calc)

    def run_pw4gww(self):
        inputs = self.exposed_inputs(Pw4gwwCalculation, "pw4gww")
        pw4gww_calc = self.submit(
            Pw4gwwCalculation,
            **inputs,
            parent_folder=self.ctx.pw_calc.outputs.remote_folder
        )
        return ToContext(pw4gww_calc=pw4gww_calc)

    def run_easy(self):
        inputs = self.exposed_inputs(EasyanalyserCalculation, "easyanalyser")
        easy_calc = self.submit(
            EasyanalyserCalculation, **inputs,
            # parent_folder=self.ctx.pw4gww_calc.outputs.remote_folder,
            pw4gww_node=orm.Int(self.ctx.pw4gww_calc.pk)
        )
        return ToContext(easy=easy_calc)

    def results(self):
        pass
