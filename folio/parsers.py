from rest_framework.exceptions import ParseError
from rest_framework.parsers import JSONParser


class SafeJSONParser(JSONParser):
    """Absurdly nested JSON overflows the stack inside json.load: answer 400, not 500."""

    def parse(self, *args, **kwargs):
        try:
            return super().parse(*args, **kwargs)
        except RecursionError:
            raise ParseError('JSON is nested too deeply.')
