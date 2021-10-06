from typing import List, Dict, Any


class OptionParser(object):
    """
    Class responsible for parsing the network scenario options from CLI.
    """
    @staticmethod
    def parse(options: List[str]) -> Dict[str, Any]:
        """
        Parse the CLI options and return a Dict containing their values.
        
        Args:
            options (List[str]): A list of string taken from CLI.

        Returns:
            Dict[str, Any]: Keys are option name and values are option value.
        """
        try:
            parsed_options = {}

            if not options:
                return parsed_options

            for option in options:
                (key, value) = option.replace('"', '').replace("'", '').split("=")
                parsed_options[key] = value

            return parsed_options
        except Exception as e:
            raise ValueError("Option parameter not valid: %s." % str(e))
