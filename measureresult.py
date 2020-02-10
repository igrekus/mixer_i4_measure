import os
import random
from collections import defaultdict

import openpyxl as openpyxl


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

    @property
    def raw_data(self):
        return self._raw_data

    @raw_data.setter
    def raw_data(self, data):
        self._raw_data = data


class MeasureResultMock(MeasureResult):
    def __init__(self):
        super().__init__()
        self._gens = defaultdict(dict)

    def init(self):
        res = super().init()
        files = self._list_xlsx()
        if len(files) != 1:
            return False
        self._parse_xlsx(files[0])
        return res

    def _list_xlsx(self):
        return [f for f in os.listdir('.') if os.path.isfile(f) and f.endswith('.xlsx')]

    def _parse_xlsx(self, file):
        wb = openpyxl.load_workbook(file)
        ws = wb.active

        rows = list(ws.rows)
        self.headers = [row.value for row in rows[0][2:]]

        for i in range(1, len(rows), 3):
            index = rows[i][0].value
            for j in range(2, ws.max_column):
                self._gens[index][rows[0][j].value] = [rows[i][j].value, rows[i + 1][j].value, rows[i + 2][j].value]

    @property
    def ready(self):
        return True

    @property
    def raw_data(self):
        return self._raw_data

    @raw_data.setter
    def raw_data(self, data):
        index = int(data[0][-2:])
        self._raw_data = [gen_value(col) for col in self._gens[index].values()]


def gen_value(data):
    if not data:
        return '-'
    if '-' in data:
        return '-'
    span, step, mean = data
    start = mean - span
    stop = mean + span
    if span == 0 or step == 0:
        return mean
    return round(random.randint(0, int((stop - start) / step)) * step + start, 2)
