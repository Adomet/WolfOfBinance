from operator import itemgetter, truth
import get_data as gd, backtrader as bt, datetime

trans = 0
total_fee = 0


### Trade Strategies ###
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
    def __init__(self, dir_ema_period, ema_period, bullavgselldiffactor, bullavgbuydiffactor, bearavgselldiffactor, bearavgbuydiffactor, stop_loss, loss_treshold):
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
        
class MyStratV8(bt.Strategy):
    def __init__(self, dir_ema_period,ema_period, bullavgselldiffactor, bullavgbuydiffactor, bearavgselldiffactor, bearavgbuydiffactor, stop_loss, loss_treshold):
        ## SMA ##
        self.dir_ema_period = dir_ema_period
        self.ema_period = ema_period
        self.bullavgselldiffactor = bullavgselldiffactor
        self.bullavgbuydiffactor = bullavgbuydiffactor
        self.bearavgselldiffactor = bearavgselldiffactor
        self.bearavgbuydiffactor = bearavgbuydiffactor
        self.stop_loss = stop_loss
        self.loss_treshold = loss_treshold
        self.ema = bt.ind.EMA(period=self.ema_period)
        self.dir_ema =  bt.ind.EMA(period=self.dir_ema_period)
        self.buyprice = -1
        self.isBull = True

    def UpdateParams(self):
        print("UpdatingParams...")
        today = self.datetime.date(ago=0)
        print("today:"+str(today))
        fromdate = today - datetime.timedelta(days=14)
        todate = today
        paramsList = Optimizer_Date(MyStratV7,[self.dir_ema_period, self.ema_period, self.bullavgselldiffactor, self.bullavgbuydiffactor, self.bearavgselldiffactor, self.bearavgbuydiffactor, self.stop_loss, self.loss_treshold],fromdate,todate)
        self.dir_ema_period = paramsList[0]
        self.ema_period = paramsList[1]
        self.bullavgselldiffactor = paramsList[2]
        self.bullavgbuydiffactor = paramsList[3]
        self.bearavgselldiffactor = paramsList[4]
        self.bearavgbuydiffactor = paramsList[5]
        self.stop_loss = paramsList[6]
        self.loss_treshold = paramsList[7]

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

        if(str(self.datetime.time()) == "00:01:00"):
            self.UpdateParams()
            return

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

class MyStratV9(bt.Strategy):
    def __init__(self, dir_ema_period, ema_period,bullavgselldiffactor, bullavgbuydiffactor, bearavgselldiffactor, bearavgbuydiffactor, stop_loss, loss_treshold):
        ## SMA ##
        self.dir_ema_period = dir_ema_period
        self.ema_period = ema_period
        self.ema = bt.ind.EMA(period=self.ema_period)
        self.dir_ema =  bt.ind.EMA(period=self.dir_ema_period)
        self.loss_treshold = loss_treshold
        self.buyprice = -1
        self.stop_loss = stop_loss
        self.bullavgbuydiffactor = bullavgbuydiffactor
        self.bullavgselldiffactor = bullavgselldiffactor
        self.bearavgbuydiffactor = bearavgbuydiffactor
        self.bearavgselldiffactor = bearavgselldiffactor
        self.isBull = True
        self.ema_list = []

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
        if self.isBull:
            avgbuydiffactor  = self.bullavgbuydiffactor
            avgselldiffactor = self.bullavgselldiffactor
        else:
            avgbuydiffactor  = self.bearavgbuydiffactor
            avgselldiffactor = self.bearavgselldiffactor
        

        if(not self.position):
            self.ema_list = []
            if avgdiff < -self.ema*10/avgbuydiffactor:
                self.order(True)
        else:
            self.ema_list.append(self.ema[0])
            max_ema = max(self.ema_list)
            if(self.data.close[0] > self.buyprice*102/100 and self.data.close[0] < max_ema*98/100):
                self.order(False)
            


            if avgdiff > self.ema*10/avgselldiffactor and self.data.close[0] > self.buyprice - (self.buyprice * self.loss_treshold/1000):
                self.order(False)


        if self.data.close[0] < self.buyprice - (self.buyprice * self.stop_loss/1000):
            self.order(False)
class MyStratV10(bt.Strategy):
    def __init__(self, dir_ema_period, ema_period, bullavgselldiffactor, bullavgbuydiffactor, bearavgselldiffactor, bearavgbuydiffactor, stop_loss, loss_treshold):
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

        if(self.isBull and not (tmp==self.isBull) and self.data.close[0] > self.buyprice - (self.buyprice * self.loss_treshold/1000)):
            self.order(False)

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


### value list to compare different strats ###
val_list = list()

### Runs Data at a strategy and its parameters can plot or give info about result returns end value of trades ###
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
        cerebro.addstrategy(strategy, args[0], args[1], args[2], args[3], args[4], args[5], args[6], args[7])
    elif(strategy == MyStratV8):
        cerebro.addstrategy(strategy, args[0], args[1], args[2], args[3], args[4], args[5], args[6], args[7])
    elif(strategy == MyStratV9):
        cerebro.addstrategy(strategy, args[0], args[1], args[2], args[3], args[4], args[5], args[6], args[7])
    elif(strategy == MyStratV10):
        cerebro.addstrategy(strategy, args[0], args[1], args[2], args[3], args[4], args[5], args[6], args[7])

    cerebro.run()
    val = cerebro.broker.getvalue()-total_fee

    restr = ""
    for i in range(0, len(args)):
        restr += str(args[i]) + ","
    print(restr+" trans:"+str(trans)+":::"+str(val))

    StartCash = 10000
    Market_ratio = (data[0]/data[-len(data)+1])*100
    Bot_ratio = (val/StartCash) * 100
    Bot_Market_ratio = Bot_ratio/Market_ratio
    BotMarketDiff = Bot_ratio-Market_ratio

    if(info):
        print("Strat: "+strategy.__name__)
        print("Backtested Data of: "+ str(fromdate)+" ---->> "+str(todate))
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

### Strategy optimizer takes strat and default values list returns optimized values list for a time period ### 
def Optimizer(strat, args):
    op_val_list = []
    op_args_list = []
    print("Optimizing...")
    print(args)

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
            diff = step * 25
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


def Optimizer_Date(strat, args, fromdate, todate):
    op_val_list = []
    op_args_list = []
    print("Optimizing...")
    print(args)
    
    ### Get Data ###
    gd.get_Date_Data(fromdate,todate,False)
    path = str(fromdate)+"="+str(todate)+".csv"
    ### Load Data ###
    global data
    data = bt.feeds.GenericCSVData(dataname=path, dtformat=2,timeframe=bt.TimeFrame.Minutes, fromdate=fromdate, todate=todate)
    print("BackTesting Data of: "+ str(fromdate)+" --->> "+str(todate))


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
            diff = step * 25
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



### Choose Time period of Backtest ###
today = datetime.date.today()
fromdate = today - datetime.timedelta(days=7)
todate = today

fromdate = datetime.datetime.strptime('2021-05-26', '%Y-%m-%d')
todate = datetime.datetime.strptime('2021-06-11', '%Y-%m-%d') #today #datetime.datetime.strptime('2021-05-30', '%Y-%m-%d')
fromdate = fromdate.date()
todate = todate.date()

### Get Data ###
gd.get_Date_Data(fromdate,todate,False)
path = str(fromdate)+"="+str(todate)+".csv"
### Load Data ###
data = bt.feeds.GenericCSVData(dataname=path, dtformat=2,timeframe=bt.TimeFrame.Minutes, fromdate=fromdate, todate=todate)
print("BackTesting Data of: "+ str(fromdate)+" --->> "+str(todate))

### Optimizer ###
#val_list.append(rundata(MyStratV7,Optimizer(MyStratV7,Optimizer(MyStratV7,Optimizer(MyStratV7,Optimizer(MyStratV7,[568, 160, 200, 561, 1446, 200, 68, -22])))),True,True))


### MyStratV7 ###
#dir_ema_period, ema_period, bullavgselldiffactor, bullavgbuydiffactor, bearavgselldiffactor, bearavgbuydiffactor, stop_loss, loss_treshold
#print("MyStratV7:")
#print("Live")  

val_list.append(rundata(MyStratV7,[432, 146, 169, 540, 1030, 126, 174, 8], False,False))
val_list.append(rundata(MyStratV7,[432, 148, 198, 559, 896 , 339, 174, 8], False,False)) 
val_list.append(rundata(MyStratV7,[432, 160, 198, 561, 4954, 186, 174, 2], False,False)) 
val_list.append(rundata(MyStratV7,[432, 160, 198, 561, 1251, 186, 174, 2], False,False)) 
val_list.append(rundata(MyStratV7,[432, 146, 169, 540, 1030, 126, 174, 8],False,False))  
val_list.append(rundata(MyStratV7,[432, 148, 198, 559, 896, 339, 174, 8],False,False))
val_list.append(rundata(MyStratV7,[514, 148, 198, 471, 896, 131, 148, 8],False,False))
val_list.append(rundata(MyStratV7,[432, 148, 170, 559, 1035, 127, 174, 8],False,False))
val_list.append(rundata(MyStratV7,[432, 160, 198, 561, 1251, 186, 174, 2],False,False))
val_list.append(rundata(MyStratV7,[432, 160, 198, 561, 1251, 186, 174, 8],False,False))
val_list.append(rundata(MyStratV7,[379, 160, 198, 561, 1215, 186, 20, 8],False,False)) 
val_list.append(rundata(MyStratV7,[432, 160, 200, 561, 1251, 200, 75, -17],False,False))
val_list.append(rundata(MyStratV7,[432, 160, 200, 561, 1251, 210, 75, -7],False,False)) 
val_list.append(rundata(MyStratV7,[571, 160, 200, 561, 1446, 200, 68, -22],False,False)) 
val_list.append(rundata(MyStratV7,[329,204,174,571,1251,119,124,-5],False,False)) 

#
val_list.append(rundata(MyStratV10,[433, 160, 149, 561, 1506, 185, 68, -15],True,False))

print("Best value:"+str(max(val_list)))

