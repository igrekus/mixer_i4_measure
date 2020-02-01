import os
import random


class MeasureResult:

    def __init__(self):
        self.headers = ['F', 'P', 'K']
        self._raw_data = list()

    def init(self):
        self._clear()
        return True

    def _clear(self):
        self._raw_data.clear()

    def generateValue(self, data):
        if data:
            span, step, mean = data
            if span and step and mean:
                start = mean - span
                stop = mean + span
                return round(random.randint(0, int((stop - start) / step)) * step + start, 2)
            else:
                return mean
        else:
            return '-'

    @property
    def ready(self):
        return bool(self._raw_data)

    @property
    def data(self):
        return self._raw_data


class MeasureResultMock(MeasureResult):
    def __init__(self):
        super().__init__()

    def init(self):
        res = super().init()
        files = self._list_xlsx()
        if len(files) != 1:
            return False
        print(files)
        return res

    def _list_xlsx(self):
        return [f for f in os.listdir('.') if os.path.isfile(f) and f.endswith('.xlsx')]

    @property
    def ready(self):
        return True
