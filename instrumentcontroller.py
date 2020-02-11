from os.path import isfile
from PyQt5.QtCore import QObject, pyqtSlot

from instr.instrumentfactory import SourceFactory, GeneratorFactory, AnalyzerFactory
from measureresult import MeasureResult, MeasureResultMock


class InstrumentController(QObject):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.requiredInstruments = {
            'Источник': SourceFactory('GPIB0::9::INSTR'),
            'Генератор 1': GeneratorFactory('GPIB0::10::INSTR'),
            'Генератор 2': GeneratorFactory('GPIB0::11::INSTR'),
            'Анализатор': AnalyzerFactory('GPIB0::12::INSTR'),
        }

        self.deviceParams = {
            'Тип 1': {
                'F1': 3.899,
                'F2': 2.5,
                'F3': 4.59,
                'F4': 0.001,
                'F5': 2.1,
                'F6': 4.6,
                'F7': 3.9,
                'F8': 0.001,
                'P1': 13,
                'P2': 6
            }
        }

        if isfile('./params.ini'):
            import ast
            with open('./params.ini', 'rt', encoding='utf-8') as f:
                raw = ''.join(f.readlines())
                self.deviceParams = ast.literal_eval(raw)

        self.secondaryParams = {
            'important': False,
        }

        self._instruments = dict()

        self.result = MeasureResultMock()
        self.found = False
        self.present = False
        self.span = 10

    def __str__(self):
        return f'{self._instruments}'

    def connect(self, addrs):
        print(f'searching for {addrs}')
        for k, v in addrs.items():
            self.requiredInstruments[k].addr = v
        self.found = self._find()

    def _find(self):
        self._instruments = {
            k: v.find() for k, v in self.requiredInstruments.items()
        }
        return all(self._instruments.values())

    def check(self, params):
        print(f'call check with {params}')
        device, secondary = params
        self.present = self._check(device, secondary)
        print('sample pass')

    def _check(self, device, secondary):
        print(f'launch check with {self.deviceParams[device]} {self.secondaryParams}')
        return self.result.init() and self._runCheck(self.deviceParams[device], self.secondaryParams)

    def _runCheck(self, param, secondary):
        print(f'run check with {param}, {secondary}')

        level = -20
        ini = 'settings.ini'
        if isfile(ini):
            with open(ini, mode='rt', encoding='utf-7') as f:
                level = int(f.readlines()[0].split('=')[1])

        source = self._instruments['Источник']
        gen1 = self._instruments['Генератор 1']
        analyzer = self._instruments['Анализатор']

        source.set_current(chan=1, value=500, unit='mA')
        source.set_voltage_limit(chan=1, value=5, unit='V')
        source.set_output(chan=1, state='ON')

        f1 = secondary['F1']
        gen1.set_modulation(state='OFF')
        gen1.set_freq(value=f1, unit='GHz')
        gen1.set_pow(value=0, unit='dBm')
        gen1.set_output(state='ON')

        analyzer.set_autocalibrate(state='OFF')
        analyzer.set_span(value=self.span, unit='MHz')
        analyzer.set_measure_center_freq(value=f1, unit='GHz')
        analyzer.set_marker1_x_center(value=f1, unit='GHz')
        analyzer.set_marker_mode(marker=1, mode='POS')
        read_pow = analyzer.read_pow(marker=1)
        analyzer.remove_marker(marker=1)

        gen1.set_output(state='OFF')

        source.set_output(chan=1, state='OFF')

        # read_pow = -10

        return read_pow > level

    def measure(self, params):
        print(params)
        print(f'call measure with {params}')
        device, secondary = params
        self._measure(device, secondary)
        self.result._only_important = self.secondaryParams['important']
        self.result.raw_data = [device]

    def _measure(self, device, secondary):
        param = self.deviceParams[device]
        secondary = self.secondaryParams
        print(f'launch measure with {param} {secondary}')

        pna = self._instruments['Анализатор']
        pna.query('*OPC?')

    @pyqtSlot(dict)
    def on_secondary_changed(self, params):
        self.secondaryParams = params

    @property
    def status(self):
        return [i.status for i in self._instruments.values()]
