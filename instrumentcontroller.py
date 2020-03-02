import ast
import time
from os.path import isfile
from PyQt5.QtCore import QObject, pyqtSlot

from instr.instrumentfactory import SourceFactory, GeneratorFactory, AnalyzerFactory, mock_enabled
from measureresult import MeasureResult, MeasureResultMock


class InstrumentController(QObject):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.requiredInstruments = {
            'Источник': SourceFactory('GPIB0::5::INSTR'),
            'Генератор 1': GeneratorFactory('GPIB0::19::INSTR'),
            'Генератор 2': GeneratorFactory('GPIB0::6::INSTR'),
            'Анализатор': AnalyzerFactory('GPIB0::18::INSTR'),
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
                'P2': 6,
                'Pcheck': -10,
                'level': -20,
                'Imin': None,
                'Imax': None
            },
        }

        self.secondaryParams = {
            'important': False,
        }

        self._instruments = dict()
        settings = dict()

        self.result = MeasureResultMock()
        self.found = False
        self.present = False
        self.span = 1

        if isfile('./params.ini'):
            with open('./params.ini', 'rt', encoding='utf-8') as f:
                raw = ''.join(f.readlines())
                self.deviceParams = ast.literal_eval(raw)

        if isfile('./instr.ini'):
            with open('./instr.ini', 'rt', encoding='utf-8') as f:
                raw = ''.join(f.readlines())
                self.requiredInstruments = eval(raw)

        if isfile('./settings.ini'):
            with open('./settings.ini', 'rt', encoding='utf-8') as f:
                for line in f.readlines():
                    if not line:
                        continue
                    key, value = line.strip().split('=')
                    settings[key] = value

        self.sleep_important = float(settings.get('important', '0.3'))
        self.sleep_unimportant = float(settings.get('unimportant', '0.3'))

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

        source = self._instruments['Источник']
        gen1 = self._instruments['Генератор 1']
        analyzer = self._instruments['Анализатор']

        imin = param['Imin']
        imax = param['Imax']
        level = param['level']

        read_curr = 0
        if imin is not None:
            source.send(f'DISPlay:WIND1:TEXT "REMOTE"')
            source.set_current(chan=1, value=imax, unit='mA')
            source.set_voltage(chan=1, value=5, unit='V')
            source.set_output(chan=1, state='ON')

            if not mock_enabled:
                read_curr = float(source.read_current(chan=1)) * 1_000

        f1 = param['F1']
        pcheck = param['Pcheck']
        gen1.set_modulation(state='OFF')
        gen1.set_freq(value=f1, unit='GHz')
        gen1.set_pow(value=pcheck, unit='dBm')
        gen1.set_output(state='ON')

        if not mock_enabled:
            time.sleep(1)

        analyzer.set_autocalibrate(state='OFF')
        analyzer.set_span(value=self.span, unit='MHz')
        analyzer.set_marker_mode(marker=1, mode='POS')
        analyzer.set_measure_center_freq(value=f1, unit='GHz')
        analyzer.set_marker1_x_center(value=f1, unit='GHz')
        read_pow = analyzer.read_pow(marker=1)

        analyzer.remove_marker(marker=1)
        gen1.set_output(state='OFF')
        gen1.set_modulation(state='ON')
        source.set_output(chan=1, state='OFF')
        analyzer.set_autocalibrate(state='ON')

        if imin is not None:
            pass_current = imin < read_curr < imax
        else:
            pass_current = True
        # read_pow = -10
        return read_pow > level and pass_current

    def measure(self, params):
        print(f'call measure with {params}')
        device, secondary = params
        res = self._measure(device, secondary)
        if res:
            self.result._only_important = self.secondaryParams['important']
            self.result.raw_data = [device]

    def _measure(self, device, secondary):
        param = self.deviceParams[device]
        dev_type = int(device[-2:])
        secondary = self.secondaryParams
        print(f'launch measure with {param} {secondary}')

        source = self._instruments['Источник']
        gen1 = self._instruments['Генератор 1']
        gen2 = self._instruments['Генератор 2']
        analyzer = self._instruments['Анализатор']

        imin = param['Imin']
        imax = param['Imax']

        if imin is not None:
            source.send(f'DISPlay:WIND1:TEXT "REMOTE"')
            source.set_current(chan=1, value=imax, unit='mA')
            source.set_voltage(chan=1, value=5, unit='V')
            source.set_output(chan=1, state='ON')

            read_curr = float(source.read_current(chan=1)) * 1_000
            if mock_enabled:
                read_curr = 10
            if read_curr >= imax:
                source.set_output(chan=1, state='OFF')
                print(f'supply current {read_curr} is bigger than max_current {imax}')
                return None

        analyzer.set_autocalibrate(state='OFF')
        analyzer.set_span(value=self.span, unit='MHz')
        analyzer.set_marker_mode(marker=1, mode='POS')

        gen1.set_modulation(state='OFF')
        gen1.set_output(state='ON')
        gen2.set_modulation(state='OFF')
        gen2.set_output(state='ON')

        for _ in range(5):
            self._measure_important(param)
        if not self.secondaryParams['important']:
            for _ in range(5):
                self._measure_unimportant(param, dev_type)

        analyzer.send('*RST')
        gen1.send('*RST')
        gen2.send('*RST')
        source.send('*RST')

        return [1]

    def _measure_important(self, param):
        print('measure important')
        sleep = self.sleep_important
        gen1 = self._instruments['Генератор 1']
        gen2 = self._instruments['Генератор 2']
        analyzer = self._instruments['Анализатор']

        f1 = param['F1']
        f3 = param['F3']
        f4 = param['F4']
        f6 = param['F6']
        f7 = param['F7']
        f8 = param['F8']
        p1 = param['P1']
        p2 = param['P2']

        gen1.set_freq(value=f1, unit='GHz')
        gen1.set_pow(value=p1, unit='dBm')
        gen2.set_freq(value=f4, unit='GHz')
        gen2.set_pow(value=p2, unit='dBm')

        analyzer.set_measure_center_freq(value=f1, unit='GHz')
        analyzer.set_marker1_x_center(value=f1, unit='GHz')
        if not mock_enabled:
            time.sleep(sleep)

        analyzer.set_measure_center_freq(value=f4, unit='GHz')
        analyzer.set_marker1_x_center(value=f4, unit='GHz')
        if not mock_enabled:
            time.sleep(sleep)

        analyzer.set_measure_center_freq(value=f7, unit='GHz')
        analyzer.set_marker1_x_center(value=f7, unit='GHz')
        if not mock_enabled:
            time.sleep(sleep)

        gen1.set_freq(value=f3, unit='GHz')
        gen1.set_pow(value=p1, unit='dBm')
        gen2.set_freq(value=f6, unit='GHz')
        gen2.set_pow(value=p2, unit='dBm')

        analyzer.set_measure_center_freq(value=f3, unit='GHz')
        analyzer.set_marker1_x_center(value=f3, unit='GHz')
        if not mock_enabled:
            time.sleep(sleep)

        analyzer.set_measure_center_freq(value=f6, unit='GHz')
        analyzer.set_marker1_x_center(value=f6, unit='GHz')
        if not mock_enabled:
            time.sleep(sleep)

        analyzer.set_measure_center_freq(value=f8, unit='GHz')
        analyzer.set_marker1_x_center(value=f8, unit='GHz')
        if not mock_enabled:
            time.sleep(sleep)

    def _measure_unimportant(self, param, dev_type):
        print('measure unimportant')
        sleep = self.sleep_unimportant
        gen1 = self._instruments['Генератор 1']
        gen2 = self._instruments['Генератор 2']
        analyzer = self._instruments['Анализатор']

        f1 = param['F1']
        f2 = param['F2']
        f3 = param['F3']
        f4 = param['F4']
        f5 = param['F5']
        f6 = param['F6']
        f7 = param['F7']
        f8 = param['F8']
        p1 = param['P1']
        p2 = param['P2']
        att = param['att']

        analyzer.send(f':POW:ATT {att}dB')
            
        gen1.set_freq(value=f2, unit='GHz')
        gen1.set_pow(value=p1, unit='dBm')
        gen2.set_freq(value=f5, unit='GHz')
        gen2.set_pow(value=p2, unit='dBm')

        analyzer.set_measure_center_freq(value=f5, unit='GHz')
        analyzer.set_marker1_x_center(value=f5, unit='GHz')
        if not mock_enabled:
            time.sleep(sleep)

        analyzer.set_measure_center_freq(value=f2, unit='GHz')
        analyzer.set_marker1_x_center(value=f2, unit='GHz')
        if not mock_enabled:
            time.sleep(sleep)

        # прогон IIP3 по мощности
        analyzer.set_measure_center_freq(value=f5, unit='GHz')
        analyzer.set_marker1_x_center(value=f5, unit='GHz')
        if not mock_enabled:
            time.sleep(sleep)

        gen1.set_freq(value=f2, unit='GHz')
        gen2.set_freq(value=f5, unit='GHz')

        for gen_pow in range(p2 - 30, (p2 - 2) + 2, 2):
            gen2.set_pow(value=gen_pow, unit='dBm')
            if not mock_enabled:
                time.sleep(sleep)

        analyzer.set_measure_center_freq(value=f5 - 0.005, unit='GHz')
        analyzer.set_marker1_x_center(value=f5 - 0.005, unit='GHz')
        if not mock_enabled:
            time.sleep(sleep)

        gen2.set_freq(value=f5 - 0.005, unit='GHz')
        for gen_pow in range(p2 - 30, (p2 - 2) + 2, 2):
            gen2.set_pow(value=gen_pow, unit='dBm')
            if not mock_enabled:
                time.sleep(sleep)

    @pyqtSlot(dict)
    def on_secondary_changed(self, params):
        self.secondaryParams = params

    @property
    def status(self):
        return [i.status for i in self._instruments.values()]
