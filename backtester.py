from math import fabs, log
from multiprocessing import set_forkserver_preload
from operator import isub, itemgetter, truth
from os import name, stat
from binance.client import Client
from backtrader import broker, cerebro, order,sizers
import backtrader as bt
from backtrader.sizers.percents_sizer import PercentSizer
from backtrader.utils import ordereddefaultdict
import get_data as gd, backtrader as bt, datetime
import time
from config import COIN_REFER, COIN_TARGET


class SuperTrendBand(bt.Indicator):
    """
    Helper inidcator for Supertrend indicator
    """
    params = (('period',7),('multiplier',3))
    lines = ('basic_ub','basic_lb','final_ub','final_lb')


    def __init__(self):
        self.atr = bt.indicators.AverageTrueRange(period=self.p.period)
        self.l.basic_ub = ((self.data.high + self.data.low) / 2) + (self.atr * self.p.multiplier)
        self.l.basic_lb = ((self.data.high + self.data.low) / 2) - (self.atr * self.p.multiplier)

    def next(self):
        if len(self)-1 == self.p.period:
            self.l.final_ub[0] = self.l.basic_ub[0]
            self.l.final_lb[0] = self.l.basic_lb[0]
        else:
            #=IF(OR(basic_ub<final_ub*,close*>final_ub*),basic_ub,final_ub*)
            if self.l.basic_ub[0] < self.l.final_ub[-1] or self.data.close[-1] > self.l.final_ub[-1]:
                self.l.final_ub[0] = self.l.basic_ub[0]
            else:
                self.l.final_ub[0] = self.l.final_ub[-1]

            #=IF(OR(baisc_lb > final_lb *, close * < final_lb *), basic_lb *, final_lb *)
            if self.l.basic_lb[0] > self.l.final_lb[-1] or self.data.close[-1] < self.l.final_lb[-1]:
                self.l.final_lb[0] = self.l.basic_lb[0]
            else:
                self.l.final_lb[0] = self.l.final_lb[-1]

class SuperTrend(bt.Indicator):
    """
    Super Trend indicator
    """
    params = (('period', 3), ('multiplier', 6))
    lines = ('super_trend',)
    plotinfo = dict(subplot=False)

    def __init__(self):
        self.stb = SuperTrendBand(period = self.p.period, multiplier = self.p.multiplier)

    def next(self):
        if len(self) - 1 == self.p.period:
            self.l.super_trend[0] = self.stb.final_ub[0]
            return

        if self.l.super_trend[-1] == self.stb.final_ub[-1]:
            if self.data.close[0] <= self.stb.final_ub[0]:
                self.l.super_trend[0] = self.stb.final_ub[0]
            else:
                self.l.super_trend[0] = self.stb.final_lb[0]

        if self.l.super_trend[-1] == self.stb.final_lb[-1]:
            if self.data.close[0] >= self.stb.final_lb[0]:
                self.l.super_trend[0] = self.stb.final_lb[0]
            else:
                self.l.super_trend[0] = self.stb.final_ub[0]

class TD9(bt.Indicator):
    lines = ('tdnine',)
    plotinfo = dict(
        plot=True,
        plotname='tdnine',
        subplot=True,
        plotlinelabels=True)


    def __init__(self):
        self.addminperiod(1)
        self.prvcandleclose =-1
        self.tdnine = 0

    def next(self):
        if(self.data.high[-4] < self.data.close):
            self.prvcandleclose  = self.data.close
            self.tdnine          = self.tdnine +1
        
        elif(self.tdnine > 0):
            self.tdnine =0
        
        if(self.data.low[-4] > self.data.close):
            self.prvcandleclose  = self.data.close
            self.tdnine          = self.tdnine -1
        
        elif(self.tdnine < 0):
            self.tdnine =0


        self.prvcandleclose = self.data.close
        self.lines.tdnine[0]     = self.tdnine
        
class SSLChannel(bt.Indicator):
    lines = ('ssld', 'sslu')
    params = (('period', 30),)
    plotinfo = dict(
        plot=True,
        plotname='SSL Channel',
        subplot=False,
        plotlinelabels=True)

    def _plotlabel(self):
        return [self.p.period]

    def __init__(self):
        self.addminperiod(self.p.period)
        self.hma_hi = bt.indicators.HullMovingAverage(self.data.high*1.01, period=self.p.period)
        self.hma_lo = bt.indicators.HullMovingAverage(self.data.low*0.99,  period=self.p.period)

    def next(self):
        hlv = 1 if self.data.close > self.hma_hi[0] else -1
        if hlv == -1:
            self.lines.ssld[0] = self.hma_hi[0]
            self.lines.sslu[0] = self.hma_lo[0]

        elif hlv == 1:
            self.lines.ssld[0] = self.hma_lo[0]
            self.lines.sslu[0] = self.hma_hi[0]


        
class MyStratV1(bt.Strategy):
    params=(('p0',0),('p1',0),('p2',0),('p3',0),('p4',0),('p5',0),('p6',0),('p7',0),('p8',0))
    def __init__(self):
        self.trend_slow_ema       =  bt.ind.SMA(period=self.params.p0)
        self.trend_fast_ema       =  bt.ind.EMA(period=self.params.p1)
        self.diff_ema             =  bt.ind.EMA(period=self.params.p2)

        self.bullavgselldiffactor =  self.params.p3
        self.bullavgbuydiffactor  =  self.params.p4
        self.bearavgselldiffactor =  self.params.p5
        self.bearavgbuydiffactor  =  self.params.p6

        self.stop_loss            =  self.params.p7
        self.RiskReward           =  self.params.p8
        self.takeprofit           =  self.stop_loss * self.RiskReward / 100

        self.buyprice             =  -1
        self.isBull               =  False
        self.ordered              =  False

    def orderer(self, isbuy):
        if(self.ordered):
            return
        
        if(isbuy and not self.position):
            self.buyprice = self.data.close[0]
            size = self.broker.get_cash() / self.data
            self.buy()
            self.ordered =True
        elif(not isbuy and self.position):
            self.buyprice = -1
            self.close()
            self.ordered =True
        

    def next(self):
        self.ordered = False
        isStop       = (self.data.close[0] < self.buyprice - (self.buyprice * self.stop_loss/1000))
        isTakeProfit = (self.data.close[0] > self.buyprice + (self.buyprice * self.takeprofit/1000))
        tmp          = (self.trend_fast_ema > self.trend_slow_ema)
        isTrendSame  = (tmp==self.isBull)

        #if self.isBull != tmp:
        #   print("isBull Switched to : "+str(not self.isBull) +":"+str(self.data.close[0]))

        if(isTakeProfit):
            self.orderer(False)

        if (isStop):
            self.orderer(False)

        if (self.isBull and not isTrendSame):
            self.orderer(False)
        
        if (not self.isBull and not isTrendSame):
            self.orderer(True)


        self.isBull = tmp

        if (self.isBull):
            if self.data > self.diff_ema + (self.diff_ema*10 / self.bullavgselldiffactor):
                self.orderer(False)

            elif self.data < self.diff_ema - (self.diff_ema*10 / self.bullavgbuydiffactor): 
                self.orderer(True)

        else:
            if self.data > self.diff_ema + (self.diff_ema*10 / self.bearavgselldiffactor):
                self.orderer(False)

            elif self.data < self.diff_ema - (self.diff_ema*10 / self.bearavgbuydiffactor):
                self.orderer(True)




class MyStratV2(bt.Strategy):
    params=(('p0',0),('p1',0),('p2',0),('p3',0),('p4',0),('p5',0),('p6',0),('p7',0),('p8',0),('p9',0))
    def __init__(self):

        self.avgselldiffactor     =  self.params.p1
        self.avgbuydiffactor      =  self.params.p2
        self.diff_ema             =  bt.ind.TripleExponentialMovingAverage(period=self.params.p0)
        self.diff_ema_heigh       =  self.diff_ema + (self.diff_ema / self.avgselldiffactor * 10) 
        self.diff_ema_low         =  self.diff_ema - (self.diff_ema / self.avgbuydiffactor  * 10) 



        self.buyprice             =  -1
        self.isBull               =  False
        self.ordered              =  False

    def orderer(self, isbuy):
        if(self.ordered):
            return
        
        if(isbuy and not self.position):
            self.buyprice = self.data.close[0]
            size = self.broker.get_cash() / self.data
            self.buy()
            self.ordered =True
        elif(not isbuy and self.position):
            self.buyprice = -1
            self.close()
            self.ordered =True
        

    def next(self):
        self.ordered = False
        
        avgdiffselltrigger = self.data.close[0] > self.diff_ema_heigh
        avgdiffbuytrigger  = self.data.close[0] < self.diff_ema_low

        if(avgdiffselltrigger):
            self.orderer(False)
        
        elif(avgdiffbuytrigger):
            self.orderer(True)





    
        #if self.isBull != tmp:
        #   print("isBull Switched to : "+str(not self.isBull) +":"+str(self.data.close[0]))

        #if(isProfitStop):
        #    self.order(False)

class MyStratV3(bt.Strategy):
    params=(('p0',0),('p1',0),('p2',0),('p3',0),('p4',0),('p5',0),('p6',0),('p7',0),('p8',0),('p9',0))
    def __init__(self):
        self.rsi                  =  bt.ind.RelativeStrengthIndex(self.data, period=self.params.p0)
        self.rsi_high             =  self.params.p1
        self.rsi_low              =  self.params.p2
        self.td9_high             =  self.params.p3
        self.td9_low              =  self.params.p4               

        self.rsibuytrigger        =  False
        self.rsiselltrigger       =  False
        self.td9buytrigger        =  False
        self.td9selltrigger       =  False

        

        self.stop_loss            =  self.params.p5
        self.RiskReward           =  self.params.p6
        self.takeprofit           =  self.stop_loss * self.RiskReward / 100
        self.tdnine               =  TD9()
        #self.sslchannel           =  SSLChannel(period=10)

        self.buyprice             =  -1
        self.isBull               =  False
        self.ordered              =  False

    def orderer(self, isbuy):
        if(self.ordered):
            return
        
        if(isbuy and not self.position):
            self.buyprice = self.data.close[0]
            size = self.broker.get_cash() / self.data
            self.buy()
            self.ordered =True

        elif(not isbuy and self.position):
            self.buyprice = -1
            self.close()
            self.ordered =True
        

    def next(self):
        self.ordered = False
        isStop       = (self.data.close[0] < self.buyprice - (self.buyprice * self.stop_loss/1000))
        isTakeProfit = (self.data.close[0] > self.buyprice + (self.buyprice * self.takeprofit/1000))

        self.td9selltrigger = self.tdnine >=  self.td9_high
        self.td9buytrigger  = self.tdnine <= -self.td9_low
        self.rsiselltrigger = self.rsi    >=  self.rsi_high 
        self.rsibuytrigger  = self.rsi    <=  self.rsi_low


        if(self.td9selltrigger  and self.rsiselltrigger):
            self.orderer(False)

        elif(self.td9buytrigger and self.rsibuytrigger):
            self.orderer(True)
        
        elif(isStop):
            self.orderer(False)

        elif(isTakeProfit):
            self.orderer(False)
        

        
        #if self.isBull != tmp:
        #   print("isBull Switched to : "+str(not self.isBull) +":"+str(self.data.close[0]))

class MyStratV4(bt.Strategy):

    params=(('p0',0),('p1',0),('p2',0),('p3',0),('p4',0),('p5',0),('p6',0),('p7',0),('p8',0),('p9',0))

    def __init__(self):

        self.rsi                  =  bt.ind.RelativeStrengthIndex(self.data, period=self.params.p0)
        self.rsi_high             =  self.params.p1
        self.rsi_low              =  self.params.p2
        
        self.tdnine               =  TD9()
        self.td9_high             =  self.params.p3
        self.td9_low              =  self.params.p4

        self.diff_ema             =  bt.ind.TripleExponentialMovingAverage(period=self.params.p5)
        self.avgselldiffactor     =  self.params.p6
        self.avgbuydiffactor      =  self.params.p7
        self.diff_ema_heigh       =  self.diff_ema + (self.diff_ema / self.avgselldiffactor * 10) 
        self.diff_ema_low         =  self.diff_ema - (self.diff_ema / self.avgbuydiffactor  * 10)           

        self.stop_loss            =  self.params.p8
        self.RiskReward           =  self.params.p9
        self.takeprofit           =  self.stop_loss * self.RiskReward / 100

        self.buyprice             =  -1
        self.isBull               =  False
        self.ordered              =  False

    def orderer(self, isbuy):
        if(self.ordered):
            return
        
        if(isbuy and not self.position):
            self.buyprice = self.data.close[0]
            size = self.broker.get_cash() / self.data
            self.buy()
            self.ordered =True

        elif(not isbuy and self.position):
            self.buyprice = -1
            self.close()
            self.ordered =True
        

    def next(self):
        self.ordered = False
        isStop       = (self.data.close[0] < self.buyprice - (self.buyprice * self.stop_loss/1000))
        isTakeProfit = (self.data.close[0] > self.buyprice + (self.buyprice * self.takeprofit/1000))

        td9selltrigger     = self.tdnine        >=  self.td9_high
        td9buytrigger      = self.tdnine        <= -self.td9_low
        rsiselltrigger     = self.rsi           >=  self.rsi_high 
        rsibuytrigger      = self.rsi           <=  self.rsi_low
        avgdiffselltrigger = self.data.close[0] >= self.diff_ema_heigh
        avgdiffbuytrigger  = self.data.close[0] <= self.diff_ema_low

        
        if(avgdiffbuytrigger):
            self.orderer(True)
        elif(avgdiffselltrigger):
            self.orderer(False)

        if((td9buytrigger and rsibuytrigger)):
            self.orderer(True)
        elif((td9selltrigger  and rsiselltrigger)):
            self.orderer(False)
        elif(isStop):
            self.orderer(False)
        elif(isTakeProfit):
            self.orderer(False)
        

        
        #if self.isBull != tmp:
        #   print("isBull Switched to : "+str(not self.isBull) +":"+str(self.data.close[0]))

class MyStratV5(bt.Strategy):
    params=(('p0',0),('p1',0),('p2',0),('p3',0),('p4',0),('p5',0),('p6',0),('p7',0),('p8',0),('p9',0))
    def __init__(self):

        self.rsi                  =  bt.ind.RelativeStrengthIndex(self.data, period=int(self.params.p0/10))
        self.rsi_high             =  self.params.p1
        self.rsi_low              =  self.params.p2
        
        self.tdnine               =  TD9()
        self.td9_high             =  self.params.p3
        self.td9_low              =  self.params.p4

        self.diff_ema             =  bt.ind.TripleExponentialMovingAverage(period=self.params.p5)
        self.avgselldiffactor     =  self.params.p6
        self.avgbuydiffactor      =  self.params.p7
        self.diff_ema_heigh       =  self.diff_ema + (self.diff_ema / self.avgselldiffactor * 10) 
        self.diff_ema_low         =  self.diff_ema - (self.diff_ema / self.avgbuydiffactor  * 10)           

        self.stop_loss            =  self.params.p8
        self.RiskReward           =  self.params.p9
        self.takeprofit           =  self.stop_loss * self.RiskReward / 100

        self.buyprice             =  -1
        self.isBull               =  False
        self.ordered              =  False

    def orderer(self, isbuy):
        if(self.ordered):
            return
        
        if(isbuy and not self.position):
            self.buyprice = self.data.close[0]
            size = self.broker.get_cash() / self.data
            self.buy()
            self.ordered =True

        elif(not isbuy and self.position):
            self.buyprice = -1
            self.close()
            self.ordered =True
        

    def next(self):
        self.ordered = False
        isStop       = (self.data.close[0] < self.buyprice - (self.buyprice * self.stop_loss/1000))
        isTakeProfit = (self.data.close[0] > self.buyprice + (self.buyprice * self.takeprofit/1000))

        td9selltrigger     = self.tdnine        >=  self.td9_high
        td9buytrigger      = self.tdnine        <= -self.td9_low
        rsiselltrigger     = self.rsi           >=  self.rsi_high 
        rsibuytrigger      = self.rsi           <=  self.rsi_low
        avgdiffselltrigger = self.data.close[0] >= self.diff_ema_heigh
        avgdiffbuytrigger  = self.data.close[0] <= self.diff_ema_low

        

        if((td9buytrigger and rsibuytrigger and avgdiffbuytrigger)):
            self.orderer(True)
        elif((td9selltrigger  and rsiselltrigger and avgdiffselltrigger)):
            self.orderer(False)
        elif(isStop):
            self.orderer(False)
        elif(isTakeProfit):
            self.orderer(False)
        

        
        #if self.isBull != tmp:
        #   print("isBull Switched to : "+str(not self.isBull) +":"+str(self.data.close[0]))


class MyStratV6(bt.Strategy):
    params=(('p0',0),('p1',0),('p2',0),('p3',0),('p4',0),('p5',0),('p6',0),('p7',0),('p8',0),('p9',0),('p10',0),('p11',0),('p12',0),('p13',0),('p14',0),('p15',0),('p16',0),('p17',0),('p18',0),('p19',0),('p20',0),('p21',0))
    def __init__(self):

        self.supertrend           =  SuperTrend(self.data,period=max(self.params.p0,1),multiplier=max(self.params.p1/10,1))
        self.superisBull          =  bt.ind.CrossOver(self.data.close,self.supertrend)
        self.isbull               =  False

        #BULL
        self.bull_rsi                  =  bt.ind.RelativeStrengthIndex(self.data, period=max(self.params.p2,3))
        self.bull_rsi_high             =  self.params.p3
        self.bull_rsi_low              =  self.params.p4
        self.bull_tdnine               =  TD9()
        self.bull_td9_high             =  self.params.p5
        self.bull_td9_low              =  self.params.p6
        self.bull_diff_ema             =  bt.ind.ExponentialMovingAverage(period=max(self.params.p7,1))
        self.bull_avgselldiffactor     =  self.params.p8
        self.bull_avgbuydiffactor      =  self.params.p9
        self.bull_diff_ema_heigh       =  self.bull_diff_ema + (self.bull_diff_ema / self.bull_avgselldiffactor * 10) 
        self.bull_diff_ema_low         =  self.bull_diff_ema - (self.bull_diff_ema / self.bull_avgbuydiffactor  * 10)           
        self.bull_stop_loss            =  self.params.p10
        self.bull_RiskReward           =  self.params.p11
        self.bull_takeprofit           =  self.bull_stop_loss * self.bull_RiskReward / 100

        #BEAR
        self.bear_rsi                  =  bt.ind.RelativeStrengthIndex(self.data, period=max(self.params.p12,3))
        self.bear_rsi_high             =  self.params.p13
        self.bear_rsi_low              =  self.params.p14
        self.bear_tdnine               =  TD9()
        self.bear_td9_high             =  self.params.p15
        self.bear_td9_low              =  self.params.p16
        self.bear_diff_ema             =  bt.ind.ExponentialMovingAverage(period=max(self.params.p17,1))
        self.bear_avgselldiffactor     =  self.params.p18
        self.bear_avgbuydiffactor      =  self.params.p19
        self.bear_diff_ema_heigh       =  self.bear_diff_ema + (self.bear_diff_ema / self.bear_avgselldiffactor * 10) 
        self.bear_diff_ema_low         =  self.bear_diff_ema - (self.bear_diff_ema / self.bear_avgbuydiffactor  * 10)           
        self.bear_stop_loss            =  self.params.p20
        self.bear_RiskReward           =  self.params.p21
        self.bear_takeprofit           =  self.bear_stop_loss * self.bear_RiskReward / 100
        

        self.buyprice             =  -1
        self.ordered              =  False

    def orderer(self, isbuy):
        if(self.ordered):
            return
        
        if(isbuy and not self.position):
            self.buyprice = self.data.close[0]
            size = self.broker.get_cash() / self.data
            self.buy()
            self.ordered =True

        elif(not isbuy and self.position):
            self.buyprice = -1
            self.close()
            self.ordered =True
        

    def next(self):
        self.ordered = False
        if(not self.superisBull[0] == 0):
                self.isbull = (self.superisBull[0] == 1)

        if(self.isbull):
            bull_isStop             = (self.data.close[0] < self.buyprice - (self.buyprice * self.bull_stop_loss/1000))
            bull_isTakeProfit       = (self.data.close[0] > self.buyprice + (self.buyprice * self.bull_takeprofit/1000)) and not self.buyprice ==-1
            bull_td9selltrigger     = self.bull_tdnine   >=  self.bull_td9_high
            bull_td9buytrigger      = self.bull_tdnine   <= -self.bull_td9_low
            bull_rsiselltrigger     = self.bull_rsi      >=  self.bull_rsi_high 
            bull_rsibuytrigger      = self.bull_rsi      <=  self.bull_rsi_low
            bull_avgdiffselltrigger = self.data.close[0] >= self.bull_diff_ema_heigh
            bull_avgdiffbuytrigger  = self.data.close[0] <= self.bull_diff_ema_low


            if((bull_td9buytrigger     and bull_rsibuytrigger  and bull_avgdiffbuytrigger )):
                self.orderer(True)
            elif((bull_td9selltrigger  and bull_rsiselltrigger and bull_avgdiffselltrigger)):
                self.orderer(False)
            elif(bull_isStop):
                self.orderer(False)
            elif(bull_isTakeProfit):
                self.orderer(False)

        else:
            bear_isStop             = (self.data.close[0] < self.buyprice - (self.buyprice * self.bear_stop_loss/1000))
            bear_isTakeProfit       = (self.data.close[0] > self.buyprice + (self.buyprice * self.bear_takeprofit/1000)) and not self.buyprice ==-1
            bear_td9selltrigger     = self.bear_tdnine   >=  self.bear_td9_high
            bear_td9buytrigger      = self.bear_tdnine   <= -self.bear_td9_low
            bear_rsiselltrigger     = self.bear_rsi      >=  self.bear_rsi_high 
            bear_rsibuytrigger      = self.bear_rsi      <=  self.bear_rsi_low
            bear_avgdiffselltrigger = self.data.close[0] >= self.bear_diff_ema_heigh
            bear_avgdiffbuytrigger  = self.data.close[0] <= self.bear_diff_ema_low


            if((bear_td9buytrigger     and bear_rsibuytrigger  and bear_avgdiffbuytrigger )):
                self.orderer(True)
            elif((bear_td9selltrigger  and bear_rsiselltrigger and bear_avgdiffselltrigger)):
                self.orderer(False)
            elif(bear_isStop):
                self.orderer(False)
            elif(bear_isTakeProfit):
                self.orderer(False)

        

        
        #if self.isBull != tmp:
        #   print("isBull Switched to : "+str(not self.isBull) +":"+str(self.data.close[0]))


class MyStratV7(bt.Strategy):
    params=(('p0',0),('p1',0),('p2',0),('p3',0),('p4',0),('p5',0),('p6',0),('p7',0),('p8',0),('p9',0),('p10',0),('p11',0),('p12',0),('p13',0),('p14',0),('p15',0),('p16',0),('p17',0),('p18',0),('p19',0),('p20',0),('p21',0))
    def __init__(self):

        self.supertrend           =  SuperTrend(self.data,period=max(self.params.p0,1),multiplier=max(self.params.p1/10,1))
        self.superisBull          =  bt.ind.CrossOver(self.data.close,self.supertrend)
        self.isbull               =  False

        #BULL
        self.bull_rsi                  =  bt.ind.RelativeStrengthIndex(self.data, period=max(self.params.p2,3))
        self.bull_rsi_high             =  self.params.p3
        self.bull_rsi_low              =  self.params.p4
        self.bull_tdnine               =  TD9()
        self.bull_td9_high             =  self.params.p5
        self.bull_td9_low              =  self.params.p6
        self.bull_diff_ema             =  bt.ind.TripleExponentialMovingAverage(period=max(self.params.p7,1))
        self.bull_avgselldiffactor     =  self.params.p8
        self.bull_avgbuydiffactor      =  self.params.p9
        self.bull_diff_ema_heigh       =  self.bull_diff_ema + (self.bull_diff_ema / self.bull_avgselldiffactor * 10) 
        self.bull_diff_ema_low         =  self.bull_diff_ema - (self.bull_diff_ema / self.bull_avgbuydiffactor  * 10)           
        self.bull_stop_loss            =  self.params.p10
        self.bull_RiskReward           =  self.params.p11
        self.bull_takeprofit           =  self.bull_stop_loss * self.bull_RiskReward / 100

        #BEAR
        self.bear_rsi                  =  bt.ind.TripleExponentialMovingAverage(self.data, period=max(self.params.p12,3))
        self.bear_rsi_high             =  self.params.p13
        self.bear_rsi_low              =  self.params.p14
        self.bear_tdnine               =  TD9()
        self.bear_td9_high             =  self.params.p15
        self.bear_td9_low              =  self.params.p16
        self.bear_diff_ema             =  bt.ind.WeightedMovingAverage(period=max(self.params.p17,1))
        self.bear_avgselldiffactor     =  self.params.p18
        self.bear_avgbuydiffactor      =  self.params.p19
        self.bear_diff_ema_heigh       =  self.bear_diff_ema + (self.bear_diff_ema / self.bear_avgselldiffactor * 10) 
        self.bear_diff_ema_low         =  self.bear_diff_ema - (self.bear_diff_ema / self.bear_avgbuydiffactor  * 10)           
        self.bear_stop_loss            =  self.params.p20
        self.bear_RiskReward           =  self.params.p21
        self.bear_takeprofit           =  self.bear_stop_loss * self.bear_RiskReward / 100
        

        self.buyprice             =  -1
        self.ordered              =  False

    def orderer(self, isbuy):
        if(self.ordered):
            return
        
        if(isbuy and not self.position):
            self.buyprice = self.data.close[0]
            size = self.broker.get_cash() / self.data
            self.buy()
            self.ordered =True

        elif(not isbuy and self.position):
            self.buyprice = -1
            self.close()
            self.ordered =True
        

    def next(self):
        self.ordered = False
        if(not self.superisBull[0] == 0):
                self.isbull = (self.superisBull[0] == 1)

        if(self.isbull):
            bull_isStop             = (self.data.close[0] < self.buyprice - (self.buyprice * self.bull_stop_loss/1000))
            bull_isTakeProfit       = (self.data.close[0] > self.buyprice + (self.buyprice * self.bull_takeprofit/1000)) and not self.buyprice ==-1
            bull_td9selltrigger     = self.bull_tdnine   >=  self.bull_td9_high
            bull_td9buytrigger      = self.bull_tdnine   <= -self.bull_td9_low
            bull_rsiselltrigger     = self.bull_rsi      >=  self.bull_rsi_high 
            bull_rsibuytrigger      = self.bull_rsi      <=  self.bull_rsi_low
            bull_avgdiffselltrigger = self.data.close[0] >= self.bull_diff_ema_heigh
            bull_avgdiffbuytrigger  = self.data.close[0] <= self.bull_diff_ema_low


            if((bull_td9buytrigger     and bull_rsibuytrigger  and bull_avgdiffbuytrigger )):
                self.orderer(True)
            elif((bull_td9selltrigger  and bull_rsiselltrigger and bull_avgdiffselltrigger)):
                self.orderer(False)
            elif(bull_isStop):
                self.orderer(False)
            elif(bull_isTakeProfit):
                self.orderer(False)

        else:
            bear_isStop             = (self.data.close[0] < self.buyprice - (self.buyprice * self.bear_stop_loss/1000))
            bear_isTakeProfit       = (self.data.close[0] > self.buyprice + (self.buyprice * self.bear_takeprofit/1000)) and not self.buyprice ==-1
            bear_td9selltrigger     = self.bear_tdnine   >=  self.bear_td9_high
            bear_td9buytrigger      = self.bear_tdnine   <= -self.bear_td9_low
            bear_rsiselltrigger     = self.bear_rsi      >=  self.bear_rsi_high 
            bear_rsibuytrigger      = self.bear_rsi      <=  self.bear_rsi_low
            bear_avgdiffselltrigger = self.data.close[0] >= self.bear_diff_ema_heigh
            bear_avgdiffbuytrigger  = self.data.close[0] <= self.bear_diff_ema_low


            if((bear_td9buytrigger     and bear_rsibuytrigger  and bear_avgdiffbuytrigger )):
                self.orderer(True)
            elif((bear_td9selltrigger  and bear_rsiselltrigger and bear_avgdiffselltrigger)):
                self.orderer(False)
            elif(bear_isStop):
                self.orderer(False)
            elif(bear_isTakeProfit):
                self.orderer(False)

        

        
        #if self.isBull != tmp:
        #   print("isBull Switched to : "+str(not self.isBull) +":"+str(self.data.close[0]))


trans =0
total_fee =0

### Runs Data at a strategy and its parameters can plot or give info about result returns end value of trades ###
def rundata(strategy, args,data, plot, info):
    StartCash = 1000
    cerebro = bt.Cerebro()

    cerebro.addstrategy(strategy,p0=args[0],p1=args[1],p2=args[2],p3=args[3],p4=args[4],p5=args[5],p6=args[6],p7=args[7],p8=args[8],p9=args[9]
                                ,p10=args[10],p11=args[11],p12=args[12],p13=args[13],p14=args[14],p15=args[15],p16=args[16],p17=args[17],p18=args[18],p19=args[19]
                                ,p20=args[20],p21=args[21])

    cerebro.broker.setcash(StartCash)
    cerebro.adddata(data)
    cerebro.addsizer(PercentSizer,percents=99)
    broker = cerebro.getbroker()
    broker.setcommission(commission=0.001,name=COIN_TARGET)
    cerebro.run()

    val = cerebro.broker.getvalue()

    restr = ""
    for i in range(0, len(args)):
        restr += str(args[i]) + ","
    print(restr+" trans:"+str(trans)+":::"+str(val))

    Market_ratio = (data[0]/data[-len(data)+1])*100
    Bot_ratio = (val/StartCash) * 100
    Bot_Market_ratio = Bot_ratio/Market_ratio
    BotMarketDiff = Bot_ratio-Market_ratio

    if(info):
        print("Strat: "+strategy.__name__)
        #print("Backtested Data of: "+ str(fromdate)+" ---->> "+str(todate))
        print("In Pos:" + str(cerebro.broker.getposition(data).size != 0))
        print("start value:" + str(StartCash))
        print("final value:" + str(val))
        print("Transaction:" + str(trans))
        print("Total fee:" + str(total_fee))
        print("Market ratio:" + str(Market_ratio))
        print("Bot ratio:" + str(Bot_ratio))
        print("BotMarketDiff:"+str(BotMarketDiff))
        print("Bot / Market:" + str(Bot_Market_ratio))
    if(plot):
        #cerebro.run()
        cerebro.plot()

    return val

def optimizeStrat(strat,args,scan_range,data):
    old_args = args.copy()
    res = OptRunData(strat,args,scan_range,data)

    if(old_args == res):
        return res

    else:
        return optimizeStrat(strat,res,scan_range,data)

def OptRunData(strategy,default_args,scan_range,data):
    print("Optimizing...")
    print(default_args)
    tstart = time.time()
    val_list = []
    args = default_args.copy()
    for i in range(0,len(default_args)):
        if(default_args[i] == -9999):
            continue
        cerebro = bt.Cerebro(optreturn=False,maxcpus=6)

        step    = int(max(abs(default_args[i]/100), 1))
        diff    = step * scan_range
        heigh   = default_args[i]+diff+step
        low     = default_args[i]-diff-step
        args[i] =(range(int(low), int(heigh), int(step)))

        cerebro.optstrategy(strategy,p0=args[0],p1=args[1],p2=args[2],p3=args[3],p4=args[4],p5=args[5],p6=args[6],p7=args[7],p8=args[8],p9=args[9]
                                ,p10=args[10],p11=args[11],p12=args[12],p13=args[13],p14=args[14],p15=args[15],p16=args[16],p17=args[17],p18=args[18],p19=args[19]
                                ,p20=args[20],p21=args[21])

        StartCash = 1000
        cerebro.broker.setcash(StartCash)
        cerebro.adddata(data)
        cerebro.addsizer(PercentSizer,percents=99)
        broker = cerebro.getbroker()
        broker.setcommission(commission=0.001,name=COIN_TARGET)
        stratruns = cerebro.run()

        val = cerebro.broker.getvalue()
    
        for stratrun in stratruns:
            pars = []
            for strat in stratrun:
                pars.append(strat.params.p0)
                pars.append(strat.params.p1)
                pars.append(strat.params.p2)
                pars.append(strat.params.p3)
                pars.append(strat.params.p4)
                pars.append(strat.params.p5)
                pars.append(strat.params.p6)
                pars.append(strat.params.p7)
                pars.append(strat.params.p8)
                pars.append(strat.params.p9)
                pars.append(strat.params.p10)
                pars.append(strat.params.p11)
                pars.append(strat.params.p12)
                pars.append(strat.params.p13)
                pars.append(strat.params.p14)
                pars.append(strat.params.p15)
                pars.append(strat.params.p16)
                pars.append(strat.params.p17)
                pars.append(strat.params.p18)
                pars.append(strat.params.p19)
                pars.append(strat.params.p20)
                pars.append(strat.params.p21)
                

                val = strat.broker.getvalue()
                print(val)
                val_list.append([val,pars])
                res = max(val_list, key=itemgetter(0))
                args[i] = res[1][i]
        # print out the result
    tend = time.time()
    print('Time used:', str(tend - tstart))
    #print(args)
    return args

def initData(traindays,testdays,timeframe,target=COIN_TARGET,refresh=False):
    ### Choose Time period of Backtest ###
    today    = datetime.date.today() #- datetime.timedelta(days=4)
    today    = today - datetime.timedelta(days=testdays)
    fromdate = today - datetime.timedelta(days=traindays)
    todate   = today + datetime.timedelta(days=1)
    ### Get Data ###
    path = gd.get_Date_Data(fromdate,todate,timeframe,target,refresh)
    ### Load Data ###
    data = bt.feeds.GenericCSVData(name=target, dataname=path, timeframe=bt.TimeFrame.Minutes, fromdate=fromdate, todate=todate)
    print("BackTesting Data of: "+ path)
    return data

def TestStratAllCoins(dayz,coins,strat,params):
    res =0
    for coin in coins:
        data = initData(dayz,0,coin,False)
        res+=rundata(strat,params,data,False,False)

    restr = ""
    for i in range(0, len(params)):
        restr += str(params[i]) + ","
    print("TestStratAllCoins ["+restr+"] ==> "+str(res))
    return res

def getBestParam(start,end,strat,params,paramindex,data,step=1):
    print("Getting best param...")
    maxval=0
    maxindex=start
    for i in range(start,end,step):
        params[paramindex]=i
        res=rundata(strat,params,data,False,False)
        if(res>maxval):
            maxval=res
            maxindex=i
    
    print("Best param : " + str(maxindex) +" ==> "+ str(maxval))
    return maxindex



val_list =list()
if __name__ == '__main__':

    Dayz = 242
    #Dayz = 275

    #15min
    data = initData(Dayz,0,Client.KLINE_INTERVAL_15MINUTE,"AVAX",False) 
    #5min
    #data = initData(Dayz,0,Client.KLINE_INTERVAL_5MINUTE,"AVAX",False)

    #val_list.append(rundata(MyStratV6,optimizeStrat(MyStratV6,[8,56,3,84,62,3,-15,170,164,270,80,160,12,74,35,9,-7,220,185,228,79,175], 32,data),data,True,False))
    #val_list.append(rundata(MyStratV6,optimizeStrat(MyStratV6,[5,50,12,67,45,4,1,197,158,264,52,101,13,74,37,9,-2,319,185,270,47,161], 64,data),data,True,False))
    #val_list.append(rundata(MyStratV6,optimizeStrat(MyStratV6,[3,54,5,82,29,3,-15,137,160,268,80,160,13,74,55,9,-7,246,185,228,73,179], 32,data),data,True,False))
    #val_list.append(rundata(MyStratV6,optimizeStrat(MyStratV6,[3,52,23,82,40,7,-29,123,142,268,112,172,15,74,55,9,-40,148,185,262,96,152], 32,data),data,True,False))
    #val_list.append(rundata(MyStratV6,optimizeStrat(MyStratV6,[8,56,3,84,62,3,-15,40,164,270,80,160,12,74,35,9,-7,110,185,228,79,175], 16,data),data,True,False))
    val_list.append(rundata(MyStratV6,optimizeStrat(MyStratV6,[10,88,19,84,41,3,-15,34,182,236,90,161,12,77,36,-8,-7,123,191,260,89,174], 16,data),data,True,False))

    #val_list.append(rundata(MyStratV6,[10,88,19,84,41,3,-15,34,182,236,90,161,12,77,36,-8,-7,123,191,260,89,174],data,False,False))





    ### Production ### 
    #val_list.append(rundata(MyStratV3,[17,66,34,8,3,158,188,1,1,1],data,False,False))
    #val_list.append(rundata(MyStratV4,[21,71,35,10,2,434,125,341,132,238],data,False,False)) 
    #val_list.append(rundata(MyStratV5,[18,65,35,9,2,301,185,230,95,256],data,True,False)) 
    #val_list.append(rundata(MyStratV6,[3,50,3,84,62,3,-15,272,164,270,50,100,12,74,35,9,-7,349,185,228,50,100],data,True,False))
    #val_list.append(rundata(MyStratV6,[10,88,19,84,41,3,-15,34,182,236,90,161,12,77,36,-8,-7,123,191,260,89,174],data,False,False))

    #print("Best value:"+str(max(val_list)))

