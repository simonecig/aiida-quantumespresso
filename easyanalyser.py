from .base import Parser
from aiida.orm import Dict


class EasyanalyserParser(Parser):
    """This class is the implementation of the Parser class for Easyanalyser."""

    def parse(self, **kwargs):
        """Parses the datafolder, stores results.

        Retrieves Easyanalyser output, and some basic information from the out_file, such as the computed energies.
        """
        retrieved = self.retrieved

        # Read standard out
        try:
            filename_stdout = self.node.get_option('output_filename')
            with retrieved.open(filename_stdout, 'r') as fil:
                out_file = fil.readlines()
        except OSError:
            return self.exit(self.exit_codes.ERROR_OUTPUT_STDOUT_READ)

        try:
            with retrieved.open(self.node.process_class._RESULT_FILE, 'r') as fil:
                res = fil.readlines()
        except OSError:
            return self.exit(self.exit_codes.ERROR_READING_RESULT_FILE)

        parsed_data = {}
        for line in res:
            sections = line.split(':')
            if 'LDA' in sections[1]:
                state = str(sections[1].split('L')[0]).strip()
                parsed_data[state] = {'Re':{}, 'Im':{}}
                lda = float(sections[2].split('G')[0])
                gw_pert = float(sections[3].split('G')[0])
                gw = float(sections[4].split('H')[0])
                hf_pert = float(sections[5].strip())
                parsed_data[state]['Re'] = {
                    'LDA': lda,
                    'GW-PERT': gw_pert,
                    'GW': gw,
                    'HF-PERT': hf_pert
                }

            elif 'GW' in sections[1]:
                state = str(sections[1].split('G')[0]).strip()
                gw = float(sections[2].strip())
                parsed_data[state]['Im'] = {
                    'GW': gw
                }
            else:
                return self.exit(self.exit_codes.ERROR_READING_RESULT_FILE)

        self.out('output_parameters', Dict(dict=parsed_data))
