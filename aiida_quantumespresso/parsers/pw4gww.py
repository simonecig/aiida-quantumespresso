from .base import Parser
from aiida.orm import Dict
import re


class Pw4gwwParser(Parser):
    """This class is the implementation of the Parser class for Pw4gww."""

    def parse(self, **kwargs):
        """Parses the datafolder, stores results.

        Retrieves Pw4gww output, and some basic information from the out_file, such as num_points and wall_time
        """
        retrieved = self.retrieved

        # TODO: manage multiple states :(
        # TODO: use parse_output_base()... missing job done?
        # Read standard out
        try:
            filename_stdout = self.node.get_option('output_filename')
            with retrieved.open(filename_stdout, 'r') as fil:
                out_file = fil.readlines()
        except OSError:
            return self.exit(self.exit_codes.ERROR_OUTPUT_STDOUT_READ)

        max_point = 0
        min_point = 0
        computed_max_point = False
        times = []
        total_cpu = 0
        total_wall = 0
        import pdb
        for i, line in enumerate(out_file):
            line = line.strip()
            nonwhitespace_chars = re.findall(r'\S+', line)
            if 'DOING POINTS RANGE' in line:
                try:
                    max_point = int(nonwhitespace_chars[-1])
                    min_point = int(nonwhitespace_chars[-2])
                except (ValueError, IndexError):
                    return self.exit(self.exit_codes.ERROR_OUTPUT_STDOUT_PARSE)
            if 'POINT NUMBER' in line:
                try:
                    point = int(nonwhitespace_chars[-1])
                    if point == max_point:
                        computed_max_point = True
                    elif point == max_point - min_point + 1:
                        computed_max_point = True
                except (ValueError, IndexError):
                    return self.exit(self.exit_codes.ERROR_OUTPUT_STDOUT_PARSE)
            if 'CPU' in line or 'WALL' in line:
                cpu_time = 0
                wall_time = 0
                try:
                    for j, word in enumerate(nonwhitespace_chars):
                        if 'CPU' in word:
                            cpu_time = float(nonwhitespace_chars[j-1][:-1]) # TODO: add support for minutes/hours?
                            total_cpu += cpu_time
                        elif 'WALL' in word:
                            wall_time = float(nonwhitespace_chars[j-1][:-1]) # TODO: add support for minutes/hours?
                            total_wall += wall_time
                except (ValueError, IndexError):
                    return self.exit(self.exit_codes.ERROR_OUTPUT_STDOUT_PARSE)

                times.append((nonwhitespace_chars[0], cpu_time, wall_time))

        times.append(('total', total_cpu, total_wall))

        if not computed_max_point:
            return self.exit(self.exit_codes.ERROR_OUTPUT_STDOUT_INCOMPLETE)

        # TODO: store times as dict instead
        parsed_data = {'min_point': min_point, 'max_point': max_point, 'times': times}
        self.out('output_parameters', Dict(dict=parsed_data))
