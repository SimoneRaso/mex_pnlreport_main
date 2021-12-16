from json import JSONEncoder

class BotSummaryEncoder(JSONEncoder):
    def default(self, o):
        return o.__dict__