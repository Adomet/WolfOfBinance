import backtrader as bt
import numpy as np

class AverageRage(bt.Indicator):
    params = (('period', 14),)
    lines = ('averageRange',)
    plotinfo = dict(plot=True, plotname='averageRange', subplot=True, plotlinelabels=True)

    def __init__(self):
        self.addminperiod(self.p.period)
        self.ranger = 100 * (self.data.high - self.data.low) / self.data.open
        self.lines.averageRange = bt.ind.SMA(self.ranger, period=self.p.period)

class NormalizedRange(bt.Indicator):
    params = (('period', 14),)
    lines = ('normalizedRange',)
    plotinfo = dict(plot=True, plotname='normalizedRange', subplot=True, plotlinelabels=True)

    def __init__(self):
        self.addminperiod(self.p.period)
        self.atr = bt.ind.AverageTrueRange(period=self.p.period)
        self.ranger = 100 * abs(self.data.close - self.data.open) / self.data.open
        self.lines.normalizedRange =  bt.ind.SMA(self.ranger, period=self.p.period)

class DiffIndicatorBase(bt.Indicator):
    """Base class for difference-based indicators to avoid code duplication"""
    params = (('period', 14), ('ATRperiod', 14),)
    
    def __init__(self):
        self.addminperiod(self.p.period)
        self.tema = bt.ind.TripleExponentialMovingAverage(period=self.p.period)
        self.diff = (self.data.close - self.tema)
        self.range = (self.data.high - self.data.low)
        self.matr = bt.ind.EMA(self.range, period=self.p.ATRperiod)
        self.atd = self.diff / self.matr


class AverageDiff(DiffIndicatorBase):
    params = (('period', 14),)
    lines = ('averageDiff', 'ATD')
    plotinfo = dict(plot=True, plotname='averageDiff', subplot=True, plotlinelabels=True)

    def __init__(self):
        super(AverageDiff, self).__init__()
        self.p.ATRperiod = self.p.period
        self.lines.ATD = self.atd
        self.lines.averageDiff = 100 * self.diff / self.data.close


class ATD(DiffIndicatorBase):
    lines = ('averageDiff',)
    plotinfo = dict(plot=True, plotname='averageDiff', subplot=True, plotlinelabels=True)

    def __init__(self):
        super(ATD, self).__init__()
        self.lines.averageDiff = self.atd


class TD9(bt.Indicator):
    lines = ('tdnine',)
    plotinfo = dict(plot=True, plotname='tdnine', subplot=True, plotlinelabels=True)

    def __init__(self):
        self.addminperiod(1)
        self.prvcandleclose = -1
        self.tdnine = 0

    def next(self):
        if self.data.high[-4] < self.data.close:
            self.prvcandleclose = self.data.close
            self.tdnine = self.tdnine + 1
        elif self.tdnine > 0:
            self.tdnine = 0
        
        if self.data.low[-4] > self.data.close:
            self.prvcandleclose = self.data.close
            self.tdnine = self.tdnine - 1
        elif self.tdnine < 0:
            self.tdnine = 0

        self.prvcandleclose = self.data.close
        self.lines.tdnine[0] = self.tdnine


class SuperTrendBand(bt.Indicator):
    params = (('period', 7), ('multiplier', 3))
    lines = ('basic_ub', 'basic_lb', 'final_ub', 'final_lb')

    def __init__(self):
        self.atr = bt.indicators.AverageTrueRange(period=self.p.period)
        self.l.basic_ub = ((self.data.high + self.data.low) / 2) + (self.atr * self.p.multiplier)
        self.l.basic_lb = ((self.data.high + self.data.low) / 2) - (self.atr * self.p.multiplier)

    def next(self):
        if len(self) - 1 == self.p.period:
            self.l.final_ub[0] = self.l.basic_ub[0]
            self.l.final_lb[0] = self.l.basic_lb[0]
        else:
            self.l.final_ub[0] = self.l.basic_ub[0] if (self.l.basic_ub[0] < self.l.final_ub[-1] or 
                                                       self.data.close[-1] > self.l.final_ub[-1]) else self.l.final_ub[-1]
            self.l.final_lb[0] = self.l.basic_lb[0] if (self.l.basic_lb[0] > self.l.final_lb[-1] or 
                                                       self.data.close[-1] < self.l.final_lb[-1]) else self.l.final_lb[-1]


class SuperTrend(bt.Indicator):
    params = (('period', 3), ('multiplier', 6))
    lines = ('super_trend',)
    plotinfo = dict(subplot=False)

    def __init__(self):
        self.stb = SuperTrendBand(period=self.p.period, multiplier=self.p.multiplier)

    def next(self):
        if len(self) - 1 == self.p.period:
            self.l.super_trend[0] = self.stb.final_ub[0]
            return

        if self.l.super_trend[-1] == self.stb.final_ub[-1]:
            self.l.super_trend[0] = self.stb.final_ub[0] if self.data.close[0] <= self.stb.final_ub[0] else self.stb.final_lb[0]
        else:
            self.l.super_trend[0] = self.stb.final_lb[0] if self.data.close[0] >= self.stb.final_lb[0] else self.stb.final_ub[0]


class EWO(bt.Indicator):
    """Elliott Wave Oscillator"""
    lines = ('ewo',)
    params = (('fper', 50), ('sper', 200))
    plotinfo = dict(subplot=True, plotname='EWO')
    
    def __init__(self):
        self.fast_ema = bt.ind.EMA(period=self.params.fper)
        self.slow_ema = bt.ind.EMA(period=self.params.sper)
        self.lines.ewo = (self.fast_ema - self.slow_ema) / self.data.close * 100 