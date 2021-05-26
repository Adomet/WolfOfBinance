import backtrader as bt
import datetime
from operator import itemgetter

NAN = float('NaN')


def is_nan(x):
    return (x != x)


trans = 0
total_fee = 0


class SmaCross(bt.Strategy):
    # list of parameters which are configurable for the strategy
    params = dict(
        pfast=60,  # period for the fast moving average
        pslow=240   # period for the slow moving average
    )

    def __init__(self, pfast, pslow, stop_loss, loss_treshold):
        self.p.pfast = pfast
        self.p.pslow = pslow
        sma1 = bt.ind.SMA(period=self.p.pfast)  # fast moving average
        sma2 = bt.ind.SMA(period=self.p.pslow)  # slow moving average
        self.crossover = bt.ind.CrossOver(sma1, sma2)  # crossover signal
        self.loss_treshold = loss_treshold
        self.buyprice = -1
        self.stop_loss = stop_loss

    def next(self):
        global trans
        global total_fee
        if self.crossover > 0 and not self.position:  # if fast crosses slow to the upside
            size = self.broker.get_cash() / self.data
            self.buyprice = self.data.close[0]
            self.buy(size=size)
            trans = trans + 1
            total_fee = total_fee + (self.broker.getvalue()/1000)

        elif self.crossover < 0 and self.data.close[0] > self.buyprice - (self.buyprice * self.loss_treshold/1000):
            self.buyprice = -1
            self.close()  # close long position
            trans = trans + 1
            total_fee = total_fee + (self.broker.getvalue()/1000)

        elif (self.data.close[0] < self.buyprice - (self.buyprice * self.stop_loss/1000)):
            self.buyprice = -1
            self.close()
            trans = trans + 1
            total_fee = total_fee + (self.broker.getvalue()/1000)


class RSIStrategy(bt.Strategy):

    def __init__(self, rsi_time_period, rsi_low, rsi_heigh, stop_loss, loss_treshold):
        self.rsi_time_period = rsi_time_period
        self.rsi_low = rsi_low
        self.rsi_heigh = rsi_heigh
        self.rsi = bt.ind.RSI(self.data, period=rsi_time_period)
        self.buyprice = -1
        self.loss_treshold = loss_treshold
        self.stop_loss = stop_loss

    def next(self):
        global trans
        global total_fee
        if self.rsi < self.rsi_low and not self.position:
            size = self.broker.get_cash() / self.data
            self.buyprice = self.data.close[0]
            self.buy(size=size)
            trans = trans + 1
            total_fee = total_fee + (self.broker.getvalue()/1000)

        if self.rsi > self.rsi_heigh and self.position and self.data.close[0] > self.buyprice - (self.buyprice * self.loss_treshold/1000):
            self.buyprice = -1
            self.close()
            trans = trans + 1
            total_fee = total_fee + (self.broker.getvalue()/1000)

        elif (self.data.close[0] < self.buyprice - (self.buyprice * self.stop_loss/1000)):
            self.buyprice = -1
            self.close()
            trans = trans + 1
            total_fee = total_fee + (self.broker.getvalue()/1000)


class MACDStrategy(bt.Strategy):

    def __init__(self, macd1, macd2, macdsig, smaperiod, dirperiod, stop_loss, loss_treshold):
        self.macd1 = macd1
        self.macd2 = macd2
        self.macdsig = macdsig
        self.smaperiod = smaperiod
        self.dirperiod = dirperiod
        self.macd = bt.indicators.MACD(
            self.data, period_me1=self.macd1, period_me2=self.macd2, period_signal=self.macdsig)
        self.pstop = 0
        ## GENERAL ##
        self.loss_treshold = loss_treshold
        self.buyprice = -1
        self.stop_loss = stop_loss

        # Cross of macd.macd and macd.signal
        self.mcross = bt.indicators.CrossOver(self.macd.macd, self.macd.signal)

        # Control market trend
        self.sma = bt.indicators.SMA(self.data, period=self.smaperiod)
        self.smadir = self.sma - self.sma(-self.dirperiod)

    def order(self, isbuy):
        global trans
        global total_fee
        trans = trans + 1
        total_fee = total_fee + (self.broker.getvalue()/1000)
        if(isbuy):
            self.buyprice = self.data.close[0]
        else:
            self.buyprice = -1

    def next(self):
        if not self.position:  # not in the market
            if self.mcross[0] > 0 and self.smadir < 0:
                size = self.broker.get_cash() / self.data
                self.order(True)
                self.buy(size=size)

        if self.position:  # not in the market
            if self.mcross[0] < 0 and self.smadir > 0 and self.data.close[0] > self.buyprice - (self.buyprice * self.loss_treshold/1000):
                self.order(False)
                self.close()

            if (self.data.close[0] < self.buyprice - (self.buyprice * self.stop_loss/1000)):
                self.order(False)
                self.close()


class AVGDiff(bt.Strategy):
    def __init__(self, pfast, avgselldiffactor, avgbuydiffactor, stop_loss, loss_treshold):
        ## SMA ##
        self.pfast = pfast
        self.ema = bt.ind.EMA(period=self.pfast)  # fast moving average
        self.loss_treshold = loss_treshold
        self.buyprice = -1
        self.stop_loss = stop_loss
        self.avgbuydiffactor = avgbuydiffactor
        self.avgselldiffactor = avgselldiffactor

    def order(self, isbuy):
        global trans
        global total_fee
        trans = trans + 1
        total_fee = total_fee + (self.broker.getvalue()/1000)
        if(isbuy):
            self.buyprice = self.data.close[0]
        else:
            self.buyprice = -1

    def next(self):
        self.avgdiff = self.data - self.ema

        if self.avgdiff < -self.ema/self.avgbuydiffactor and not self.position:
            self.order(True)
            size = self.broker.get_cash() / self.data
            self.buy(size=size)

        if self.avgdiff > self.ema/self.avgselldiffactor and self.position and self.data.close[0] > self.buyprice - (self.buyprice * self.loss_treshold/1000):
            self.order(False)
            self.close()

        if self.data.close[0] < self.buyprice - (self.buyprice * self.stop_loss/1000):
            self.order(False)
            self.close()


class MyStratV1(bt.Strategy):
    # list of parameters which are configurable for the strategy

    def __init__(self, rsi_time_period, rsi_low, rsi_heigh, pfast, pslow, stop_loss, loss_treshold):
        ## RSI ##
        self.rsi_time_period = rsi_time_period
        self.rsi_low = rsi_low
        self.rsi_heigh = rsi_heigh
        self.rsi = bt.ind.RSI(self.data, period=rsi_time_period)
        ## SMA ##
        self.pfast = pfast
        self.pslow = pslow
        self.smaf = bt.ind.SMA(period=self.pfast)  # fast moving average
        self.sma = bt.ind.SMA(period=self.pslow)  # slow moving average
        self.crossover = bt.ind.CrossOver(
            self.smaf, self.sma)  # crossover signal
        ## ATR STOP##
        self.atrdist = 30
        self.atr = bt.indicators.ATR(self.data, period=rsi_time_period)
        self.pstop = 0
        ## GENERAL ##
        self.loss_treshold = loss_treshold
        self.buyprice = -1
        self.stop_loss = stop_loss
        self.cross = 0

    def next(self):
        global trans
        global total_fee

        if self.rsi < self.rsi_low and self.sma-self.smaf < self.sma * 1615/100000 and not self.position:
            size = self.broker.get_cash() / self.data
            self.buyprice = self.data.close[0]
            self.buy(size=size)
            trans = trans + 1
            total_fee = total_fee + (self.broker.getvalue()/1000)
            pdist = self.atr[0] * self.atrdist
            self.pstop = self.data.close[0] - pdist

        elif self.rsi > self.rsi_heigh and self.smaf-self.sma < self.smaf * 25/100000 and self.position and self.data.close[0] > self.buyprice - (self.buyprice * self.loss_treshold/1000):
            trans = trans + 1
            total_fee = total_fee + (self.broker.getvalue()/1000)
            self.buyprice = -1
            self.close()

        elif self.data.close[0] < self.buyprice - (self.buyprice * self.stop_loss/1000):
            trans = trans + 1
            total_fee = total_fee + (self.broker.getvalue()/1000)
            self.buyprice = -1
            self.close()


class MyStratV2(bt.Strategy):
    # list of parameters which are configurable for the strategy

    def __init__(self, rsi_time_period, rsi_low, rsi_heigh, pfast, pslow, stop_loss, loss_treshold):
        ## RSI ##
        self.rsi_time_period = rsi_time_period
        self.rsi_low = rsi_low
        self.rsi_heigh = rsi_heigh
        self.rsi = bt.ind.RSI(self.data, period=rsi_time_period)
        ## SMA ##
        self.pfast = pfast
        self.pslow = pslow
        self.ema = bt.ind.EMA(period=self.pfast)  # fast moving average
        self.sma = bt.ind.SMA(period=self.pslow)  # slow moving average
        self.crossover = bt.ind.CrossOver(
            self.ema, self.sma)  # crossover signal
        ## GENERAL ##
        self.loss_treshold = loss_treshold
        self.buyprice = -1
        self.stop_loss = stop_loss

    def order(self, isbuy):
        global trans
        global total_fee
        trans = trans + 1
        total_fee = total_fee + (self.broker.getvalue()/1000)
        if(isbuy):
            self.buyprice = self.data.close[0]
        else:
            self.buyprice = -1

    def next(self):
        global trans
        global total_fee

        if self.rsi < self.rsi_low and not self.position:
            size = self.broker.get_cash() / self.data
            self.order(True)
            self.buy(size=size)

        elif self.rsi > self.rsi_heigh and self.ema-self.sma < self.sma * 15/10000 and self.position and self.data.close[0] > self.buyprice - (self.buyprice * self.loss_treshold/1000):
            self.order(False)
            self.close()

        elif self.data.close[0] < self.buyprice - (self.buyprice * self.stop_loss/1000):
            self.order(False)
            self.close()


class MyStratV3(bt.Strategy):
    def __init__(self, rsi_time_period, rsi_low, rsi_heigh, pfast, pslow, ema_ago_thhold, stop_loss, loss_treshold):
        ## RSI ##
        self.rsi_time_period = rsi_time_period
        self.rsi_low = rsi_low
        self.rsi_heigh = rsi_heigh
        self.rsi = bt.ind.RSI(self.data, period=rsi_time_period)
        ## SMA ##
        self.pfast = pfast
        self.pslow = pslow
        self.ema = bt.ind.EMA(period=self.pfast)  # fast moving average
        self.sma = bt.ind.SMA(period=self.pslow)  # slow moving average
        self.crossover = bt.ind.CrossOver(
            self.ema, self.sma)  # crossover signal
        ## GENERAL ##
        self.ema_ago_thhold = ema_ago_thhold
        self.loss_treshold = loss_treshold
        self.buyprice = -1
        self.stop_loss = stop_loss
        ## ATR STOP##
        self.atrdist = 30
        self.atr = bt.indicators.ATR(self.data, period=rsi_time_period*5) * 20
        self.pstop = 0

    def order(self, isbuy):
        global trans
        global total_fee
        trans = trans + 1
        total_fee = total_fee + (self.broker.getvalue()/1000)
        if(isbuy):
            self.buyprice = self.data.close[0]
        else:
            self.buyprice = -1

    def next(self):
        self.avgdiff = self.data - self.ema
        avgdiffactor = 80

        # self.ema_ago_thhold/1000
        if (self.rsi < self.rsi_low or self.avgdiff < -self.ema/avgdiffactor) and not self.position and self.sma - self.ema > 0 and abs(self.ema - self.ema[-5]) < self.ema_ago_thhold/1000:
            size = self.broker.get_cash() / self.data
            self.order(True)
            self.buy(size=size)

        if (self.rsi > self.rsi_heigh or self.avgdiff > self.ema/avgdiffactor) and self.position and self.sma - self.ema < 0 and self.data.close[0] > self.buyprice - (self.buyprice * self.loss_treshold/1000) and abs(self.ema - self.ema[-5]) < self.ema_ago_thhold/1000:
            self.order(False)
            self.close()

        if self.data.close[0] < self.buyprice - (self.buyprice * self.stop_loss/1000):
            self.order(False)
            self.close()


class MyStratV4(bt.Strategy):
    # val_list.append(rundata(MACDStrategy,60,130,45,30,10,0,0,200,10,False,False))
    #   def __init__(self,rsi_time_period,rsi_low,rsi_heigh,pfast,pslow,avgdiffactor,ema_ago_thhold,stop_loss,loss_treshold):
    #   def __init__(self,macd1,macd2,macdsig,smaperiod,dirperiod,stop_loss,loss_treshold):
    def __init__(self, timer, smadiffac, pfast, avgdiffactor, stop_loss, loss_treshold):
        ## GENERAL ##
        # self.ema = bt.ind.EMA(period=pfast)  # fast moving average
        self.avgdiffactor = avgdiffactor
        self.loss_treshold = loss_treshold
        self.buyprice = -1
        self.stop_loss = stop_loss
        self.sma = bt.indicators.SMA(self.data, period=pfast)
        self.timer = timer
        self.smadiffac = smadiffac

    def order(self, isbuy):
        global trans
        global total_fee
        trans = trans + 1
        total_fee = total_fee + (self.broker.getvalue()/1000)
        if(isbuy):
            self.buyprice = self.data.close[0]
        else:
            self.buyprice = -1

    def next(self):
        t = self.timer

        if not self.position:  # self.ema/2000000
            if self.sma - self.sma[-t*60] < self.sma/self.smadiffac and self.sma - self.sma[-t*30] < self.sma/self.smadiffac and self.sma - self.sma[-t*15] < self.sma/self.smadiffac and self.sma - self.sma[-t*10] > -self.sma/self.smadiffac and self.sma - self.sma[-t*5] > -self.sma/self.smadiffac and self.sma - self.sma[-t] > -self.sma/self.smadiffac:
                self.order(True)
                size = self.broker.get_cash() / self.data
                self.buy(size=size)

        elif self.position:
            if self.sma - self.sma[-t*60] > -self.sma/self.smadiffac and self.sma - self.sma[-t*30] > -self.sma/self.smadiffac and self.sma - self.sma[-t*15] > -self.sma/self.smadiffac and self.sma - self.sma[-t*10] < self.sma/self.smadiffac and self.sma - self.sma[-t*5] < self.sma/self.smadiffac and self.sma - self.sma[-t] < self.sma/self.smadiffac and self.data.close[0] > self.buyprice - (self.buyprice * self.loss_treshold/1000):
                self.order(False)
                self.close()

            elif self.data.close[0] < self.buyprice - (self.buyprice * self.stop_loss/1000):
                self.order(False)
                self.close()


class MyStratV5(bt.Strategy):
    def __init__(self, pfast, pslow, avgfemadiffactor, avgsemadiffactor, timer, semadiffac, stop_loss, loss_treshold):
        ## SMA ##
        self.pfast = pfast
        self.pslow = pslow
        self.fema = bt.ind.EMA(period=self.pfast)  # fast moving average
        self.sma = bt.ind.EMA(period=self.pslow)  # slow moving average
        self.loss_treshold = loss_treshold
        self.buyprice = -1
        self.stop_loss = stop_loss
        self.avgfemadiffactor = avgfemadiffactor
        self.avgsemadiffactor = avgsemadiffactor
        self.timer = timer
        self.smadiffac = semadiffac

    def order(self, isbuy):
        global trans
        global total_fee
        trans = trans + 1
        total_fee = total_fee + (self.broker.getvalue()/1000)
        if(isbuy):
            self.buyprice = self.data.close[0]
        else:
            self.buyprice = -1

    def next(self):
        t = self.timer

        if not self.position:
            if self.data - self.fema < -self.fema/self.avgfemadiffactor:
                self.order(True)
                size = self.broker.get_cash() / self.data
                self.buy(size=size)

        else:
            # if  self.data - self.fema > self.fema/self.avgfemadiffactor and self.data.close[0] > self.buyprice -(self.buyprice * self.loss_treshold/1000):
            if self.sma - self.sma[-t*60] > -self.sma/self.smadiffac and self.sma - self.sma[-t*30] > -self.sma/self.smadiffac and self.sma - self.sma[-t*15] > -self.sma/self.smadiffac and self.sma - self.sma[-t*10] < self.sma/self.smadiffac and self.sma - self.sma[-t*5] < self.sma/self.smadiffac and self.sma - self.sma[-t] < self.sma/self.smadiffac and self.data.close[0] > self.buyprice - (self.buyprice * self.loss_treshold/1000):
                self.order(False)
                self.close()

            if self.data.close[0] < self.buyprice - (self.buyprice * self.stop_loss/1000):
                self.order(False)
                self.close()


class MyStratV6(bt.Strategy):
    def __init__(self, dir_ema_period, dir_ago, bull_ema_period, bullavgselldiffactor, bullavgbuydiffactor, bear_ema_period, bearavgselldiffactor, bearavgbuydiffactor, stop_loss, loss_treshold):
        ## SMA ##
        self.bull_ema_period = bull_ema_period
        self.bear_ema_period = bear_ema_period
        self.dir_ema_period = dir_ema_period
        self.bull_ema = bt.ind.EMA(period=self.bull_ema_period)
        self.bear_ema = bt.ind.EMA(period=self.bear_ema_period)
        self.dir_ema =  bt.ind.DoubleExponentialMovingAverage(period=self.dir_ema_period)
        self.loss_treshold = loss_treshold
        self.buyprice = -1
        self.stop_loss = stop_loss
        self.bullavgbuydiffactor = bullavgbuydiffactor
        self.bullavgselldiffactor = bullavgselldiffactor
        self.bearavgbuydiffactor = bearavgbuydiffactor
        self.bearavgselldiffactor = bearavgselldiffactor
        self.dir_ago = dir_ago
        self.isBull = True

    def order(self, isbuy):
        global trans
        global total_fee
        trans = trans + 1
        total_fee = total_fee + (self.broker.getvalue()/1000)
        if(isbuy):
            self.buyprice = self.data.close[0]
            size = self.broker.get_cash() / self.data
            self.buy(size=size)
        else:
            self.buyprice = -1
            self.close()

    def next(self):
        bull_avgdiff = self.data - self.bull_ema
        bear_avgdiff = self.data - self.bear_ema
        tmp = (self.dir_ema - self.dir_ema[-self.dir_ago*2] > 0 and self.dir_ema -
               self.dir_ema[-self.dir_ago] > 0 and self.dir_ema - self.dir_ema[-5] > 0)
        #if self.isBull != tmp:
        #    print("isBull Switched to : "+str(not self.isBull) +":"+str(self.data.close[0]))

        self.isBull = tmp

        if(self.isBull):
            if bull_avgdiff < -self.bull_ema*10/self.bullavgbuydiffactor and not self.position:
                self.order(True)

            if bull_avgdiff > self.bull_ema*10/self.bullavgselldiffactor and self.position and self.data.close[0] > self.buyprice - (self.buyprice * self.loss_treshold/1000):
                self.order(False)
        else:
            if bear_avgdiff < -self.bear_ema*10/self.bearavgbuydiffactor and not self.position:
                self.order(True)

            if bear_avgdiff > self.bear_ema*10/self.bearavgselldiffactor and self.position and self.data.close[0] > self.buyprice - (self.buyprice * self.loss_treshold/1000):
                self.order(False)

        if self.data.close[0] < self.buyprice - (self.buyprice * self.stop_loss/1000):
            self.order(False)

class MyStratV7(bt.Strategy):
    def __init__(self, dir_ema_period, dir_ago, ema_period, bullavgselldiffactor, bullavgbuydiffactor, bearavgselldiffactor, bearavgbuydiffactor, stop_loss, loss_treshold):
        ## SMA ##
        self.ema_period = ema_period
        self.dir_ema_period = dir_ema_period
        self.ema = bt.ind.EMA(period=self.ema_period)
        self.dir_ema =  bt.ind.EMA(period=self.dir_ema_period)
        self.loss_treshold = loss_treshold
        self.buyprice = -1
        self.stop_loss = stop_loss
        self.bullavgbuydiffactor = bullavgbuydiffactor
        self.bullavgselldiffactor = bullavgselldiffactor
        self.bearavgbuydiffactor = bearavgbuydiffactor
        self.bearavgselldiffactor = bearavgselldiffactor
        self.dir_ago = dir_ago
        self.isBull = True

    def order(self, isbuy):
        global trans
        global total_fee
        trans = trans + 1
        total_fee = total_fee + (self.broker.getvalue()/1000)
        if(isbuy):
            self.buyprice = self.data.close[0]
            size = self.broker.get_cash() / self.data
            self.buy(size=size)
        else:
            self.buyprice = -1
            self.close()

    def next(self):
        avgdiff = self.data - self.ema
        tmp = (self.ema > self.dir_ema)

        #if self.isBull != tmp:
        #   print("isBull Switched to : "+str(not self.isBull) +":"+str(self.data.close[0]))

        self.isBull = tmp

        if(self.isBull):
            if avgdiff < -self.ema*10/self.bullavgbuydiffactor and not self.position:
                self.order(True)

            if avgdiff > self.ema*10/self.bullavgselldiffactor and self.position and self.data.close[0] > self.buyprice - (self.buyprice * self.loss_treshold/1000):
                self.order(False)
        else:
            if avgdiff < -self.ema*10/self.bearavgbuydiffactor and not self.position:
                self.order(True)

            if avgdiff > self.ema*10/self.bearavgselldiffactor and self.position and self.data.close[0] > self.buyprice - (self.buyprice * self.loss_treshold/1000):
                self.order(False)

        if self.data.close[0] < self.buyprice - (self.buyprice * self.stop_loss/1000):
            self.order(False)

val_list = list()

# i,j,x,y,s,e,a,stl,l
def rundata(strategy, args, plot, info):
    global trans
    global total_fee
    trans = 0
    total_fee = 0
    cerebro = bt.Cerebro(maxcpus=None)
    cerebro.adddata(data)

    if(strategy == RSIStrategy):
        cerebro.addstrategy(strategy, args[0], args[1], args[2], args[3], args[4])
    elif (strategy == SmaCross):
        cerebro.addstrategy(strategy, args[0], args[1], args[2], args[3])
    elif (strategy == MACDStrategy):
        cerebro.addstrategy(strategy, args[0], args[1], args[2], args[3], args[4], args[7], args[8])
    elif(strategy == AVGDiff):
        cerebro.addstrategy(strategy, args[0], args[1], args[2], args[3], args[4])
    elif(strategy == MyStratV1):
        cerebro.addstrategy(strategy, args[0], args[1], args[2], args[3], args[4], args[5], args[6])
    elif(strategy == MyStratV2):
        cerebro.addstrategy(strategy, args[0], args[1], args[2], args[3], args[4], args[5], args[6])
    elif(strategy == MyStratV3):
        cerebro.addstrategy(strategy, args[0], args[1], args[2], args[3], args[4], args[5], args[6], args[7])
    elif(strategy == MyStratV4):
        cerebro.addstrategy(strategy, args[0], args[1], args[2], args[3], args[4], args[5])
    elif(strategy == MyStratV5):
        cerebro.addstrategy(strategy, args[0], args[1], args[2], args[3], abs(args[4]), args[5], args[6], args[7])
    elif(strategy == MyStratV6):
        cerebro.addstrategy(strategy, args[0], args[1], args[2], args[3], args[4], args[5], args[6], args[7], args[8], args[9])
    elif(strategy == MyStratV7):
        cerebro.addstrategy(strategy, args[0], args[1], args[2], args[3], args[4], args[5], args[6], args[7], args[8])

    cerebro.run()
    val = cerebro.broker.getvalue()-total_fee

    restr = ""
    for i in range(0, len(args)):
        restr += str(args[i]) + ":"
    print(restr+" trans:"+str(trans)+":::"+str(val))

    StartCash = 10000
    Market_ratio = (data[0]/data[-len(data)+1])*100
    Bot_ratio = (val/StartCash) * 100
    Bot_Market_ratio = Bot_ratio/Market_ratio
    BotMarketDiff = Bot_ratio-Market_ratio

    if(info):
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
        cerebro.plot()

    return val


def Optimizer(strat, args):
    op_val_list = []
    op_args_list = []

    for arg in range(0, len(args)):
        new_arg = args[arg]
        old_arg = args[arg]
        old_val = -9999999
        new_val = rundata(strat, args, False, False)
        while old_val < new_val:
            old_val = new_val
            op_val_list = []
            args[arg] = new_arg
            op_val_list.append([rundata(strat, args, False, False), new_arg])

            step = max(abs(new_arg/100), 1)
            diff = step * 20
            heigh = new_arg+diff+step
            low = new_arg-diff-step
            
            if(old_arg > new_arg):
                heigh = new_arg+step
                low = new_arg-diff-diff-step
            elif(old_arg < new_arg):
                heigh = new_arg+diff+diff+step
                low = new_arg-step

            if(args[arg] > 0):
                low = max(low, 1)

            for i in range(int(low+1), int(heigh+1), int(step+1)):
                args[arg] = i
                op_val_list.append([rundata(strat, args, False, False), i])
            res = max(op_val_list, key=itemgetter(0))
            print("best:"+str(res[1])+":"+str(res[0]))
            old_arg = new_arg
            new_arg = res[1]
            new_val = res[0]

        op_args_list.append(new_arg)
        args[arg] = new_arg
        print("Optimized val:"+str(new_arg))
    print(op_args_list)
    return op_args_list


# 130:400:1:15:17630.459664127367
# print("RSI:")
# rundata(RSIStrategy,14,26,68,3,0,False) # RSI BEST
#print("RSI Size:")
# rundata(RSIStrategy,14,26,69,3,0,False)
# print("SmaCrossSize:")
# rundata(SmaCrossSize,111,375,3,15,0,False)
# rundata(SmaCross,30,220,0,3,0,False)
# rundata(SmaCross,30,90,0,14,0,False)
# val_list.append(rundata(MyStrat,14,27,68,131,1080,123,-5,True))
# val_list.append(rundata(MyStrat,14,27,68,131,1080,123,-5,False))
# val_list.append(rundata(MyStrat,13,27,65,57,1077,185,-5,True)) 5m down trend best
# val_list.append(rundata(MyStrat,13,26,67,462,1080,245,-1,False,False)) #5m up trend best
# val_list.append(rundata(MACDStrategy,13,24,9,12,3,44,12,True,False))  # MACD best
# val_list.append(rundata(MyStratV2,13,29,69,650,1100,110,-25,True,False)) #5m down trend best
# val_list.append(rundata(MyStratV1,13,29,69,600,1100,110,-25,True,False)) #5m down trend best
# val_list.append(rundata(MyStratV3,14,29,69,260,1000,100,100,-30,True,False)) #5m down trend best
# val_list.append(rundata(AVGDiff,14,29,69,195,1000,110,40,170,25,False,False))
# val_list.append(rundata(MyStratV5,300,1500,37,110,0,0,0,25,14,True,False))


# print("SmaCross")
# rundata(SmaCross,111,375,0,0,0,120,3,False) #SMA BEST
# for i in range(115,130,1):
# rundata(MyStrat,14,26,68,111,375,120,-5,False)
# val_list.append(rundata(MyStratV3,14,29,68,190,1000,110,70,-20,True,False)) #5m down trend best

#print("Last 15D bests")
# print("RSI:")
# val_list.append(rundata(RSIStrategy,14,30,70,0,0,0,0,110,-30,False,False))
# val_list.append(rundata(RSIStrategy,14,30,70,0,0,0,0,500,-10,False,False))
# print("SMA:")
# val_list.append(rundata(SmaCross,190,600,0,0,0,0,0,5,0,False,False))
# val_list.append(rundata(SmaCross,80,380,0,0,0,0,0,14,0,False,False))
# print("Macd:")
# val_list.append(rundata(MACDStrategy,20,130,45,30,10,0,0,140,10,False,False))
# val_list.append(rundata(MACDStrategy,60,130,45,30,10,0,0,200,10,False,False))
# print("AVGDiff:")
# val_list.append(rundata(AVGDiff,0,0,0,200,1000,110,50,170,25,False,False))
# val_list.append(rundata(AVGDiff,0,0,0,199,1000,110,37,170,14,False,False))
# print("MyStratV1:")
# val_list.append(rundata(MyStratV1,14,30,70,1250,1300,0,0,110,-25,False,False))
# val_list.append(rundata(MyStratV1,13,29,69,580,1100,0,0,110,-25,False,False))
# print("MyStratV2:")
# val_list.append(rundata(MyStratV2,14,30,70,1200,1300,0,0,80,-25,False,False))
# val_list.append(rundata(MyStratV2,13,29,69,400,1070,0,0,110,-25,False,False))
# print("MyStratV3:")
# val_list.append(rundata(MyStratV3,14,30,70,250,1000,80,0,60,-30,False,False))
# val_list.append(rundata(MyStratV3,14,29,69,260,1000,100,0,100,-30,False,False))
# print("MyStratV4:")
# val_list.append(rundata(MyStratV4,25,220000,0,0,0,450,0,120,10,False,False))
# val_list.append(rundata(MyStratV4,5,220000,0,0,0,325,0,120,10,False,False))
#
#print("2 M Bests")
# print("RSI:")
# val_list.append(rundata(RSIStrategy,14,30,70,0,0,0,0,500,-10,False,False))
# print("SMA")
# val_list.append(rundata(SmaCross,80,380,0,0,0,0,0,14,0,False,False))
# print("Macd:")
# val_list.append(rundata(MACDStrategy,60,130,45,30,10,0,0,200,10,False,False))
# print("AVGDiff:")
# val_list.append(rundata(AVGDiff,0,0,0,199,1000,110,37,170,14,False,False))
# print("MyStratV1:")
# val_list.append(rundata(MyStratV1,13,29,69,580,1100,0,0,110,-25,False,False))
# print("MyStratV2:")
# val_list.append(rundata(MyStratV2,13,29,69,400,1070,0,0,110,-25,False,False))
# print("MyStratV3:")
# val_list.append(rundata(MyStratV3,14,29,69,260,1000,100,0,100,-30,False,False))
# print("MyStratV4:")
# val_list.append(rundata(MyStratV4,5,220000,0,0,0,325,0,120,10,False,False))


# [181, 1396, 35, 87, 3, 184143, -1, 77, 17]   [-21, -21, -21, 189, 654, 67, 48, 154, 16] AVG


# val_list.append(rundata(MyStratV5,200,1500,37,110,0,0,0,75,14,False,False))
# val_list.append(rundata(MyStratV5,200,1500,50,110,0,0,0,25,14,False,False))
# val_list.append(rundata(MyStratV5,200,1500,50,110,0,0,0,75,14,False,False))
# val_list.append(rundata(MyStratV5,200,1500,50,150,0,0,0,75,25,False,False))
# val_list.append(rundata(MyStratV5,200,1500,50,150,0,0,0,170,25,False,False))
# val_list.append(rundata(MyStratV5,200,1500,50,150,0,0,0,170,14,False,False))


# val_list.append(rundata(AVGDiff,0,0,0,200,1000,0,50,170,25,False,False))
# val_list.append(rundata(AVGDiff,0,0,0,200,1500,110,50,75,14,False,False))
# val_list.append(rundata(AVGDiff,0,0,0,200,1500,110,37,170,14,False,False))
# val_list.append(rundata(AVGDiff,0,0,0,199,1000,110,37,170,14,False,False))


fromdate = datetime.datetime.strptime('2021-05-01', '%Y-%m-%d')
todate = datetime.datetime.strptime('2021-05-30', '%Y-%m-%d')
data = bt.feeds.GenericCSVData(dataname='data.csv', dtformat=2,timeframe=bt.TimeFrame.Minutes, fromdate=fromdate, todate=todate)


#print("RSI:")
#val_list.append(rundata(RSIStrategy,[14,30,70,110,-30],False,False))
#val_list.append(rundata(RSIStrategy,[14,30,70,500,-10],False,False))
#print("SMA:")
#val_list.append(rundata(SmaCross,[190,600,5,0],False,False))
#val_list.append(rundata(SmaCross,[80,380,14,0],False,False))
#print("Macd:")
#val_list.append(rundata(MACDStrategy,[20,130,45,30,10,0,0,140,10],False,False))
#val_list.append(rundata(MACDStrategy,[60,130,45,30,10,0,0,200,10],False,False))
#print("AVGDiff:")
#val_list.append(rundata(AVGDiff,[200,1000,50,170,25],False,False))
#val_list.append(rundata(AVGDiff,[199,1000,37,170,14],False,False))
#print("MyStratV1:")
#val_list.append(rundata(MyStratV1,[14,30,70,1250,1300,110,-25],False,False))
#val_list.append(rundata(MyStratV1,[13,29,69,580,1100,110,-25 ],False,False))
#print("MyStratV2:")
#val_list.append(rundata(MyStratV2,[14,30,70,1200,1300,80,-25],False,False))
#val_list.append(rundata(MyStratV2,[13,29,69,400,1070,110,-25],False,False))
#print("MyStratV3:")
#val_list.append(rundata(MyStratV3,[14,30,70,250,1000,80,60, -30],False,False))
#val_list.append(rundata(MyStratV3,[14,29,69,260,1000,100,100,-30],False,False))
#print("MyStratV4:")
#val_list.append(rundata(MyStratV4,[25,220000,450,120,10],False,False))
#val_list.append(rundata(MyStratV4,[5,220000,325,120,10 ],False,False))



#print("MyStratV4:")
#val_list.append(rundata(MyStratV4,Optimizer(MyStratV4,[5,22000,325,0,120,10]),False,False))
#val_list.append(rundata(MyStratV4,[10, 20018, 338, -10, 102, 1],False,False))
#
#print("MyStratV5:")
#val_list.append(rundata(MyStratV5,Optimizer(MyStratV5,[146, 1434, 13, 48, 24, 138803, -1, 57, -8]),False,False))
#val_list.append(rundata(MyStratV5,[146, 1290, 13, 38, 24, 124922, -1, 47, -18],False,False))
# FR [146, 1515, 13, 58, 24, 154226, -1, 67, 2] SR [146, 1434, 13, 48, 24, 138803, -1, 57, -8]+ [116, 1882, 13, 38, 24, 124922, -1, 47, -18]

#rundata(MyStratV5,[146, 1434, 13, 48, 24, 138803, -1, 57, -8],True,True)


# (self,pfast,pslow,dir_ago,bullavgselldiffactor,bullavgbuydiffactor,bearavgselldiffactor,bearavgbuydiffactor,stop_loss,loss_treshold):
# 05 11 05 30
#print("AVGDiff:")
#val_list.append(rundata(AVGDiff,Optimizer(AVGDiff,Optimizer(AVGDiff,[149, 67, 13, 99, -16])),False,False)) # To add trend dir trend dir spesific argsdiff low [149, 67, 13, 99, -16]
# To add trend dir trend dir spesific argsdiff low [149, 67, 13, 99, -16]
# [155, 49, 92, -12] [151, 52, 13, 105, -10]
#val_list.append(rundata(AVGDiff, [111, 33, 45, 95, 1], False, False))
#val_list.append(rundata(AVGDiff, [149, 67, 13, 99, -16], False, False))
#val_list.append(rundata(AVGDiff, [200, 37, 13, 170, 14], False, False))
#val_list.append(rundata(AVGDiff, [190, 37, 13, 152, 23], False, False))
#val_list.append(rundata(AVGDiff, [156, 37, 13, 131, 6], False, False))
#val_list.append(rundata(AVGDiff, [151, 52, 13, 105, -10], False, False))

print("MyStratV6:")
#val_list.append(rundata(MyStratV6,Optimizer(MyStratV6,Optimizer(MyStratV6,[1061, 38, 142, 160, 690, 141, 500, 130, 77, 25])),True,True)) #[1000, 100, 122, 29, 60, 494, 67, 13, 94, 10]
# 1 [1000, 100, 121, 32, 45, 177, 67, 13, 94, -1]
# 2 [1063, 60, 132, 16, 61, 148, 50, 13, 78, -3] 
# 3 [2128, 10, 194, 13, 14, 173, 50, 50, 112, 5]
# 4 [1061, 39, 142, 16, 69, 141, 50, 13, 77, 25]
# 5 [1059, 38, 142, 16, 69, 141, 50, 13, 77, 25]
# 6 [1057, 38, 142, 16, 69, 141, 50, 13, 77, 25]
# 7 [1061, 38, 142, 16, 69, 141, 50, 13, 77, 25]


#val_list.append(rundata(MyStratV6,[1064, 38, 142, 168, 680, 141, 500, 123, 78, 25],True,False))
#val_list.append(rundata(MyStratV6,[905,  38, 162, 160, 672, 146, 498, 130, 148, 27],True,False))


print("MyStratV7:")
#val_list.append(rundata(MyStratV7,Optimizer(MyStratV7,Optimizer(MyStratV7,[603, 27, 141, 151, 636, 518, 133, 78, 25])),True,True)) #[603, 27, 141, 151, 636, 518, 133, 78, 25]

val_list.append(rundata(MyStratV7,[603, 27, 141, 151, 636, 518, 133, 78, 25],True,False)) 
#val_list.append(rundata(MyStratV7,[1064, 38, 142, 168, 680, 500, 123, 78, 25],True,False))
#val_list.append(rundata(MyStratV7,[680, 27, 141, 172, 636, 518, 132, 78, 11],True,False)) 

# new 6 [905, 38, 162, 160, 672, 146, 498, 130, 148, 27]
# new 7 [680, 27, 141, 172, 636, 518, 132, 78, 11]
print("Best value:"+str(max(val_list)))

