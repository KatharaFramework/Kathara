class OptionParser(object):
    @staticmethod
    def parse(options):
        parsed_options = {}

        if not options:
            return parsed_options

        for option in options:
            (key, value) = option.replace('"', '').replace("'", '').split("=")
            parsed_options[key] = value

        return parsed_options
