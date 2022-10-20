import datetime
import time
from math import sqrt
from operator import itemgetter
from statistics import stdev

import backtrader as bt
from binance.client import Client

import get_data as gd
from config import COIN_REFER, COIN_TARGET


class AverageRage(bt.Indicator):
    params = (
        ('period', 14),
    )

    lines = ('averageRange',)
    plotinfo = dict(
        plot=True,
        plotname='averageRange',
        subplot=True,
        plotlinelabels=True)

    def __init__(self):
        self.addminperiod(self.p.period)
        self.ranger = bt.talib.SQRT((self.data.high - self.data.low) / self.data.open)
        self.lines.averageRange = bt.ind.EMA(self.ranger,period=self.p.period)

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

class MyStratV1(bt.Strategy):
    params=(('p0',0),('p1',0),('p2',0),('p3',0),('p4',0),('p5',0),('p6',0),('p7',0),('p8',0),('p9',0),('p10',0),('p11',0),('p12',0),('p13',0),('p14',0),('p15',0),('p16',0),('p17',0),('p18',0),('p19',0),('p20',0))
    def __init__(self):
        self.plot                      =  False
        self.params.p0                 =  max(self.params.p0,1)
        self.supertrend                =  SuperTrend(self.data,period=self.params.p0,multiplier=max(self.params.p1/100,1),plot=True)
        self.superisBull               =  bt.ind.CrossOver(self.data.close,self.supertrend,plot=False)
        self.tdnine                    =  TD9(plot=self.plot)
        self.adx                       =  bt.ind.AverageDirectionalMovementIndex(self.data,period = 13,plot=self.plot)
        self.atr                       =  bt.ind.AverageTrueRange(self.data,period=9,plot=self.plot)


        self.isbull                    =  False
        #BULL
        self.params.p2                 =  max(self.params.p2,1)
        self.bull_rsi                  =  bt.ind.RelativeStrengthIndex(self.data, period=self.params.p2,safediv=True,plot=self.plot)
        self.bull_rsi_high             =  self.params.p3 / 10
        self.bull_rsi_low              =  self.params.p4 / 10
        self.params.p5                 =  max(self.params.p5,1)
        self.bull_diff_ema             =  bt.ind.TripleExponentialMovingAverage(period=self.params.p5,plot=self.plot)
        self.bull_diff_ema_heigh       =  self.bull_diff_ema + (self.bull_diff_ema / self.params.p6 * 10) 
        self.bull_diff_ema_low         =  self.bull_diff_ema - (self.bull_diff_ema / self.params.p7 * 10)
        self.bull_takeprofit           =  self.params.p8 / 10000

        #BEAR
        self.params.p9                 =  max(self.params.p9,1)
        self.bear_rsi                  =  bt.ind.RelativeStrengthIndex(self.data, period=self.params.p9,safediv=True,plot=self.plot)
        self.bear_rsi_high             =  self.params.p10 / 10
        self.bear_rsi_low              =  self.params.p11 / 10
        self.params.p12                =  max(self.params.p12,1)
        self.bear_diff_ema             =  bt.ind.TripleExponentialMovingAverage(period=self.params.p12,plot=self.plot)
        self.bear_diff_ema_heigh       =  self.bear_diff_ema + (self.bear_diff_ema / self.params.p13 * 10) 
        self.bear_diff_ema_low         =  self.bear_diff_ema - (self.bear_diff_ema / self.params.p14 * 10)
        self.bear_takeprofit           =  self.params.p15 / 10000 
        self.stop_loss                 =  self.params.p16 / 10000
        self.timeProfitRetioDropRate   =  self.params.p17 / 1000000

        self.hardSTPDefault            =  self.params.p18
        self.buyprice                  =  -1
        self.ordered                   =  False

        self.posCandleCount            =  0
        self.buysize                   =  0
        self.isbuyready                =  False

        ##### INFO LINES #####
        #self.linea                     =  bt.ind.EMA(self.bear_diff_ema_low,period=1)
        #self.lineb                     =  bt.ind.EMA(self.bull_diff_ema_heigh,period=1)
        #self.RRatr                     =  AverageRage(self.data,period=201)
        #self.roc                       =  bt.ind.RateOfChange100(self.data,period=13)


    def orderer(self, isbuy):
        if(self.ordered):
            return
        
        if(isbuy and self.buyprice == -1 ):
            self.buyprice = self.data.close[0]
            self.buysize = int(self.broker.get_cash()*99/100) / self.data.close[0]
            self.buy(size=self.buysize)
            self.ordered =True

        elif(not isbuy and not self.buyprice == -1 ):
            self.buysize = 0
            self.buyprice = -1
            self.close()
            self.ordered =True
        
    def next(self):

        self.ordered                = False
        adxtrigger                  = self.adx             >=  26
        td9selltrigger              = self.tdnine          >=  10
        candleDiffbuytrigger        = 58/1000 >=  1 - (self.data.close[0]/self.data.open[0])
        isStop                      = self.data.close[0]   <=  self.buyprice - (self.buyprice * self.stop_loss) - (self.atr * 81 / 1000 )

        ### Momentum Strat ###
        ### Momentum Strat ###
        ### Momentum Strat ###

        if(not self.superisBull[0] == 0):
                self.isbull = (self.superisBull[0] == 1)

        if(self.isbull):
            bull_rsibuytrigger      = self.bull_rsi        <=  self.bull_rsi_low
            bull_rsiselltrigger     = self.bull_rsi        >=  self.bull_rsi_high 
            bull_avgdiffselltrigger = self.data.close[0]   >=  self.bull_diff_ema_heigh
            bull_avgdiffbuytrigger  = self.data.close[0]   <=  self.bull_diff_ema_low 
            bull_isTakeProfit       = self.data.close[0]   >=  self.buyprice + (self.buyprice * self.bull_takeprofit) and not self.buyprice == -1

            if(bull_rsibuytrigger    and bull_avgdiffbuytrigger):
                self.isbuyready = True
            elif(bull_rsiselltrigger and bull_avgdiffselltrigger and td9selltrigger):
                self.orderer(False)
            elif(bull_isTakeProfit):
                self.orderer(False)
            elif(isStop and adxtrigger):
                self.orderer(False)

        else:
            bear_rsiselltrigger     = self.bear_rsi        >=  self.bear_rsi_high 
            bear_rsibuytrigger      = self.bear_rsi        <=  self.bear_rsi_low
            bear_avgdiffselltrigger = self.data.close[0]   >=  self.bear_diff_ema_heigh
            bear_avgdiffbuytrigger  = self.data.close[0]   <=  self.bear_diff_ema_low
            bear_isTakeProfit       = self.data.close[0]   >=  self.buyprice + (self.buyprice * self.bear_takeprofit) and not self.buyprice == -1

            if(bear_rsibuytrigger    and bear_avgdiffbuytrigger):
                self.isbuyready = True            
            elif(bear_rsiselltrigger and bear_avgdiffselltrigger):
                self.orderer(False)
            elif(bear_isTakeProfit):
                self.orderer(False)
            elif(isStop and adxtrigger):
                self.orderer(False)

        #buyTriggerOfCandle
        if(candleDiffbuytrigger and  self.isbuyready):
            self.isbuyready=False
            self.orderer(True)

        if(not self.buyprice == -1):
            self.posCandleCount += 1
        else:
            self.posCandleCount  = 0

        ### NEW STUFF ###
        TimeProfitRatioSTP          = (self.data.close[0] - self.buyprice)/self.buyprice >= ((self.bull_takeprofit) - (self.timeProfitRetioDropRate * (self.posCandleCount))) and not self.isbull 
        hardSTP                     = self.data.close[0]    <= self.buyprice - (self.buyprice *  self.hardSTPDefault/1000) and not self.isbull
        
        if(TimeProfitRatioSTP):
            self.orderer(False)

        if(hardSTP and adxtrigger):
            self.orderer(False)

class BBMomentumStrat(bt.Strategy):#20,200,10,18,-1,-1,-1
    params=(('p0',0),('p1',0),('p2',0),('p3',0),('p4',0),('p5',0),('p6',0),('p7',0),('p8',0),('p9',0),('p10',0),('p11',0),('p12',0),('p13',0),('p14',0),('p15',0),('p16',0),('p17',0),('p18',0),('p19',0),('p20',0))
    def __init__(self):
        self.plot                      =  True
        self.buyprice                  =  -1
        self.ordered                   =  False
        self.buysize                   =  0

        self.params.p0                 =  max(self.params.p0,1)
        self.params.p1                 =  max(self.params.p1,1)
        self.bb                        =  bt.ind.BollingerBands(self.data.close,period=self.params.p0,devfactor=self.params.p1/100,movav=bt.ind.EMA)
        self.adx                       =  bt.ind.AverageDirectionalMovementIndex(self.data,period = 13,plot=self.plot)


        self.tpper                     =  self.params.p2/100
        self.stpper                    =  self.params.p3/100

        self.posCandleCount            =  0


    def orderer(self, isbuy):
        if(self.ordered):
            return
        
        if(isbuy and self.buyprice == -1 ):
            self.buyprice = self.data.close[0]
            self.buysize = int(self.broker.get_cash()*99/100) / self.data.close[0]
            self.buy(size=self.buysize)
            self.ordered =True

        elif(not isbuy and not self.buyprice == -1 ):
            self.buysize = 0
            self.buyprice = -1
            self.close()
            self.ordered =True

    def next(self):
        self.ordered                = False
        
        if(self.bb.top[0] < self.data.close[0]):
            self.orderer(True)

        if(self.bb.bot[0] > self.data.close[0]):
            self.orderer(False)

        if(self.data.close[0]  >  self.buyprice + (self.buyprice*self.tpper)):
            self.orderer(False)

        if(self.data.close[0] <   self.buyprice - (self.buyprice*self.stpper)):
            self.orderer(False)

class TStrat1(bt.Strategy):
    params=(('p0',0),('p1',0),('p2',0),('p3',0),('p4',0),('p5',0),('p6',0),('p7',0),('p8',0),('p9',0),('p10',0),('p11',0),('p12',0),('p13',0),('p14',0),('p15',0),('p16',0),('p17',0),('p18',0),('p19',0),('p20',0))
    def __init__(self):
        self.plot                      =  True
        self.buyprice                  =  -1
        self.ordered                   =  False
        self.buysize                   =  0


        self.params.p0                 = max(self.params.p0,1)

        self.rangePer                  =  bt.ind.EMA(10000*(self.data.close-self.data.open)/self.data.open,period=self.params.p0,subplot=True)
        self.buyLine                   =  -self.params.p1
        self.sellLine                  =  self.params.p2

        self.tpper                     =  self.params.p3
        self.stpper                    =  self.params.p4
        self.timestpper                =  self.params.p5

        self.posCandleCount            =  0

    def orderer(self, isbuy):
        if(self.ordered):
            return
        
        if(isbuy and self.buyprice == -1 ):
            self.buyprice = self.data.close[0]
            self.buysize = int(self.broker.get_cash()*99/100) / self.data.close[0]
            self.buy(size=self.buysize)
            self.ordered =True

        elif(not isbuy and not self.buyprice == -1 ):
            self.buysize = 0
            self.buyprice = -1
            self.close()
            self.ordered =True

    def next(self):
        self.ordered                = False
        #self.orderer(self.buyprice==-1)


        tp                   = self.data.close[0]  > self.buyprice + (self.buyprice * self.tpper / 1000)
        stp                  = self.data.close[0]  < self.buyprice - (self.buyprice * self.stpper / 1000)
        TimeProfitRatioSTP   = (self.data.close[0] - self.buyprice) / self.buyprice >= ((self.tpper / 1000) - (self.timestpper / 1000000 * (self.posCandleCount)))
        isbuy                = self.rangePer[0] <= self.buyLine  / 100
        isSell               = self.rangePer[0] >= self.sellLine / 100


        if(isbuy):
            self.orderer(True)
        
        if(isSell):
            self.orderer(False)



        if(tp):
            self.orderer(False)
        if(stp):
            self.orderer(False)
        if(not self.buyprice == -1):
            self.posCandleCount += 1
        else:
            self.posCandleCount  = 0
        if(TimeProfitRatioSTP):
            self.orderer(False)

class TestStrat(bt.Strategy):
    params=(('p0',0),('p1',0),('p2',0),('p3',0),('p4',0),('p5',0),('p6',0),('p7',0),('p8',0),('p9',0),('p10',0),('p11',0),('p12',0),('p13',0),('p14',0),('p15',0),('p16',0),('p17',0),('p18',0),('p19',0),('p20',0))
    def __init__(self):
        self.plot                      =  True
        self.buyprice                  =  -1
        self.ordered                   =  False
        self.buysize                   =  0

        self.params.p0                 =  max(self.params.p0,1)
        self.supertrend                =  SuperTrend(self.data,period=self.params.p0,multiplier=max(self.params.p1/100,1),plot=self.plot)
        self.superisBull               =  bt.ind.CrossOver(self.data.close,self.supertrend,plot=False)
        self.isbull                    =  False

        #BULL
        self.params.p2                 =  max(self.params.p2,1)
        self.bull_rangePer             =  bt.ind.EMA(10000*(self.data.close-self.data.open)/self.data.open,period=self.params.p2,subplot=self.plot)
        self.bull_buyLine              = -self.params.p3
        self.bull_sellLine             =  self.params.p4
        self.bull_tpper                =  self.params.p5
        self.bull_stpper               =  self.params.p6

        #BEAR
        self.params.p7                 =  max(self.params.p7,1)
        self.bear_rangePer             =  bt.ind.EMA(10000*(self.data.close-self.data.open)/self.data.open,period=self.params.p7,subplot=self.plot)
        self.bear_buyLine              = -self.params.p8
        self.bear_sellLine             =  self.params.p9
        self.bear_tpper                =  self.params.p10
        self.bear_stpper               =  self.params.p11

        self.timestpper                =  self.params.p12
        self.posCandleCount            =  0

    def orderer(self, isbuy):
        if(self.ordered):
            return
        
        if(isbuy and self.buyprice == -1 ):
            self.buyprice = self.data.close[0]
            self.buysize = int(self.broker.get_cash()*99/100) / self.data.close[0]
            self.buy(size=self.buysize)
            self.ordered =True

        elif(not isbuy and not self.buyprice == -1 ):
            self.buysize = 0
            self.buyprice = -1
            self.close()
            self.ordered =True

    def next(self):
        self.ordered                  = False
        #self.orderer(self.buyprice==-1)

        if(not self.superisBull[0] == 0):
            self.isbull = (self.superisBull[0] == 1)

        if(self.isbull):
            bull_tp                   = self.data.close[0]  > self.buyprice + (self.buyprice * self.bull_tpper / 1000)
            bull_stp                  = self.data.close[0]  < self.buyprice - (self.buyprice * self.bull_stpper / 1000)
            bull_isbuy                = self.bull_rangePer[0] <= self.bull_buyLine  / 100
            bull_isSell               = self.bull_rangePer[0] >= self.bull_sellLine / 100

            if(bull_isbuy):
                self.orderer(True)
            if(bull_isSell):
                self.orderer(False)
            if(bull_tp):
                self.orderer(False)
            if(bull_stp):
                self.orderer(False)
        
        else:
            bear_tp                   = self.data.close[0]  > self.buyprice + (self.buyprice * self.bear_tpper / 1000)
            bear_stp                  = self.data.close[0]  < self.buyprice - (self.buyprice * self.bear_stpper / 1000)
            bear_isbuy                = self.bear_rangePer[0] <= self.bear_buyLine  / 100
            bear_isSell               = self.bear_rangePer[0] >= self.bear_sellLine / 100
            if(bear_isbuy):
                self.orderer(True)
            if(bear_isSell):
                self.orderer(False)
            if(bear_tp):
                self.orderer(False)
            if(bear_stp):
                self.orderer(False)



        TimeProfitRatioSTP   = (self.data.close[0] - self.buyprice) / self.buyprice >= ((self.bull_tpper / 1000) - (self.timestpper / 1000000 * (self.posCandleCount)))
        if(not self.buyprice == -1):
            self.posCandleCount += 1
        else:
            self.posCandleCount  = 0
        if(TimeProfitRatioSTP):
            self.orderer(False)
       
############ ANALYZERZ ######################
def printTradeAnalysis(analyzer):
    '''
    Function to print the Technical Analysis results in a nice format.
    '''
    #Get the results we are interested in
    total_open = analyzer.total.open
    total_closed = analyzer.total.closed
    total_won = analyzer.won.total
    total_lost = analyzer.lost.total
    win_streak = analyzer.streak.won.longest
    lose_streak = analyzer.streak.lost.longest
    pnl_net = round(analyzer.pnl.net.total,2)
    strike_rate = (total_won / total_closed) * 100
    strike_rate = round(strike_rate,3)
    #Designate the rows
    h1 = ['Total Open', 'Total Closed', 'Total Won', 'Total Lost']
    h2 = ['Strike Rate','Win Streak', 'Losing Streak', 'PnL Net']
    r1 = [total_open, total_closed,total_won,total_lost]
    r2 = [strike_rate, win_streak, lose_streak, pnl_net]
    #Check which set of headers is the longest.
    if len(h1) > len(h2):
        header_length = len(h1)
    else:
        header_length = len(h2)
    #Print the rows
    print_list = [h1,r1,h2,r2]
    row_format ="{:<15}" * (header_length + 1)
    print("Trade Analysis Results:")
    for row in print_list:
        print(row_format.format('',*row))

def printSQN(analyzer):
    sqn = round(analyzer.sqn,3)
    print('SQN: {}'.format(sqn))

def printsharperatio(analyzer):
    print('Sharpe: {}'.format(analyzer['sharperatio']))

def addParamstoCerebro(cerebro,strategy,args):

    cnt = len(args)-1
    if(cnt==20):
        cerebro.addstrategy(strategy,p0=args[0],p1=args[1],p2=args[2],p3=args[3],p4=args[4],p5=args[5],p6=args[6],p7=args[7],p8=args[8],p9=args[9],p10=args[10],p11=args[11],p12=args[12],p13=args[13],p14=args[14],p15=args[15],p16=args[16],p17=args[17],p18=args[18],p19=args[19],p20=args[20])
    else:
        print(str(cnt) +" No array params match!")

### Runs Data at a strategy and its parameters can plot or give info about result returns end value of trades ###
def rundata(strategy, args,data, plot, info,optType='Return'):
    StartCash = 1000
    cerebro = bt.Cerebro()

    addParamstoCerebro(cerebro,strategy,args)

    cerebro.broker.setcash(StartCash)
    cerebro.adddata(data)
    # Add observers
    cerebro.addobserver(bt.observers.DrawDown)
    # Add the analyzers we are interested in
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="ta")
    cerebro.addanalyzer(bt.analyzers.SQN, _name="sqn")
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name="drawdown")
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharperatio')
    #cerebro.addsizer(PercentSizer,percents=99)
    broker = cerebro.getbroker()
    broker.setcommission(commission=0.001,name=COIN_TARGET)
    results = cerebro.run()

    val = cerebro.broker.getvalue()

    restr = ""
    for i in range(0, len(args)):
        restr += str(args[i]) + ","

    strat = results[0]
    if(optType=='Return'):
        val = strat.broker.getvalue()
    
    if(optType=='DrawDown'):
        ret = float(sqrt(strat.broker.getvalue()))
        ddown = strat.analyzers.drawdown.get_analysis().max.drawdown
        val = ret / ddown

    if(optType=='WinRate'):
        analyzer = strat.analyzers.ta.get_analysis()
        total_closed = analyzer.total.closed
        total_won = analyzer.won.total
        winrate = (total_won / total_closed)
        ret = float(sqrt(strat.broker.getvalue()))
        val = winrate * winrate * winrate * ret

    if(optType=='SQN'):
        analyzer = strat.analyzers.sqn.get_analysis()
        sqn = analyzer['sqn']
        ret = float(sqrt(strat.broker.getvalue()))
        val = sqn * sqn * sqn * ret

    if(optType=='Ado'):
       analyzer = strat.analyzers.ta.get_analysis()
       total_closed = analyzer.total.closed
       total_won    = analyzer.won.total
       winrate      = (total_won / total_closed)
       sqn          = strat.analyzers.sqn.get_analysis()['sqn']
       sharperatio  = strat.analyzers.sharperatio.get_analysis()['sharperatio']
       ret          = float(sqrt(strat.broker.getvalue()))
       ddown        = strat.analyzers.drawdown.get_analysis().max.drawdown
       val          = ret * sqn * sqn * winrate * winrate * total_won  / ddown       
                
    if(optType=='All'):
        analyzer = strat.analyzers.ta.get_analysis()
        total_closed = analyzer.total.closed
        total_won = analyzer.won.total
        winrate = (total_won / total_closed)
        sqn = strat.analyzers.sqn.get_analysis()['sqn']
        ret = float(sqrt(strat.broker.getvalue()))
        ddown = strat.analyzers.drawdown.get_analysis().max.drawdown
        val =  ret * sqn * winrate / ddown
    
    print(restr+":::"+str(val))
    #print("Confidance:" + str(conf))
    if(info):
        Market_ratio = (data[0]/data[-len(data)+1])
        Bot_ratio = (val/StartCash)
        Bot_Market_ratio = Bot_ratio/Market_ratio
        print("Strat: "+strategy.__name__)
        print("In Pos:" + str(cerebro.broker.getposition(data).size != 0))
        print("Market ratio:" + str(Market_ratio))
        print("Bot ratio:" + str(Bot_ratio))
        print("Bot / Market:" + str(Bot_Market_ratio))
        print("TradePerCandle:" + str(results[0].analyzers.ta.get_analysis().total.closed/(len(data.close))))
        print("DrawDown:" + str(results[0].analyzers.drawdown.get_analysis().max.drawdown))

        # print the analyzers
        printTradeAnalysis(results[0].analyzers.ta.get_analysis())
        printSQN(results[0].analyzers.sqn.get_analysis())
        printsharperatio(results[0].analyzers.sharperatio.get_analysis())

    if(plot):
        #cerebro.run()
        cerebro.plot(style='candlestick')
        #cerebro.plot()


    return val

#OptType =?= 'Return' , 'WinRate' ,'SQN' , 'Sharpe'
def optimizeStrat(strat,args,scan_range,data,startindex=0,optType='Return'):
    old_args = args.copy()
    res = OptRunData(strat,args,scan_range,data,startindex,optType)

    if(old_args == res):
        return res

    else:
        return optimizeStrat(strat,res,scan_range,data,startindex,optType)

def addParamstoOptCerebro(cerebro,strategy,args):

    cnt = len(args)-1

    if(cnt==20):
        cerebro.optstrategy(strategy,p0=args[0],p1=args[1],p2=args[2],p3=args[3],p4=args[4],p5=args[5],p6=args[6],p7=args[7],p8=args[8],p9=args[9],p10=args[10],p11=args[11],p12=args[12],p13=args[13],p14=args[14],p15=args[15],p16=args[16],p17=args[17],p18=args[18],p19=args[19],p20=args[20])
    else:
        print(str(cnt) +" No array params match!")

#OptType =?= 'Return' , 'WinRate' ,'SQN' , 'Sharpe' , 'All'
def OptRunData(strategy,default_args,my_scan_range,data,startindex=0,optType='Return'):
    print("Optimizing "+optType+" ...")
    print("Starting from index: "+str(startindex) +", val: "+str(default_args[startindex]))
    print(default_args)
    tstart = time.time()
    val_list = []
    args = default_args.copy()
    for i in range(startindex,len(default_args)):
        if(default_args[i] == -1):
            continue
        cerebro = bt.Cerebro(optreturn=False,maxcpus=16)

        scan_range = min(my_scan_range,(default_args[i]+1)*(default_args[i]+1))
        step    = int(max(abs(default_args[i]/100), 1))
        step    = 1
        diff    = step * scan_range
        heigh   = default_args[i]+diff+step
        low     = default_args[i]-diff-step
        low     = max(1,low)
        heigh   = max(1,heigh)
        args[i] =(range(int(low), int(heigh), int(step)))

        addParamstoOptCerebro(cerebro,strategy,args)

        StartCash = 1000
        cerebro.broker.setcash(StartCash)
        cerebro.adddata(data)
        cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="ta")
        cerebro.addanalyzer(bt.analyzers.SQN, _name="sqn")
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name="drawdown")
        cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharperatio')
        #cerebro.addsizer(PercentSizer,percents=99)
        broker = cerebro.getbroker()
        broker.setcommission(commission=0.001,name=COIN_TARGET)
        stratruns = cerebro.run()

    
        for stratrun in stratruns:
            pars = []
            for strat in stratrun:
                t=0
                if(t<len(args)):
                    pars.append(strat.params.p0)  
                    t=t+1
                if(t<len(args)):
                    pars.append(strat.params.p1)  
                    t=t+1
                if(t<len(args)):
                    pars.append(strat.params.p2)  
                    t=t+1
                if(t<len(args)):
                    pars.append(strat.params.p3)  
                    t=t+1
                if(t<len(args)):
                    pars.append(strat.params.p4)  
                    t=t+1
                if(t<len(args)):
                    pars.append(strat.params.p5)  
                    t=t+1
                if(t<len(args)):
                    pars.append(strat.params.p6)  
                    t=t+1
                if(t<len(args)):
                    pars.append(strat.params.p7)  
                    t=t+1
                if(t<len(args)):
                    pars.append(strat.params.p8)  
                    t=t+1
                if(t<len(args)):
                    pars.append(strat.params.p9)  
                    t=t+1
                if(t<len(args)):
                    pars.append(strat.params.p10) 
                    t=t+1
                if(t<len(args)):
                    pars.append(strat.params.p11) 
                    t=t+1
                if(t<len(args)):
                    pars.append(strat.params.p12) 
                    t=t+1
                if(t<len(args)):
                    pars.append(strat.params.p13) 
                    t=t+1
                if(t<len(args)):
                    pars.append(strat.params.p14) 
                    t=t+1
                if(t<len(args)):
                    pars.append(strat.params.p15) 
                    t=t+1
                if(t<len(args)):
                    pars.append(strat.params.p16) 
                    t=t+1
                if(t<len(args)):
                    pars.append(strat.params.p17) 
                    t=t+1
                if(t<len(args)):
                    pars.append(strat.params.p18) 
                    t=t+1
                if(t<len(args)):
                    pars.append(strat.params.p19) 
                    t=t+1
                if(t<len(args)):
                    pars.append(strat.params.p20) 
                    t=t+1
                if(t<len(args)):
                    pars.append(strat.params.p21) 
                    t=t+1
                if(t<len(args)):
                    pars.append(strat.params.p22) 
                    t=t+1
                if(t<len(args)):
                    pars.append(strat.params.p23) 
                    t=t+1
                if(t<len(args)):
                    pars.append(strat.params.p24) 
                    t=t+1
                if(t<len(args)):
                    pars.append(strat.params.p25) 
                    t=t+1
                if(t<len(args)):
                    pars.append(strat.params.p26) 
                    t=t+1
                
                val = 0
                if(optType=='Return'):
                    val = strat.broker.getvalue()

                if(optType=='WinRate'):
                    analyzer = strat.analyzers.ta.get_analysis()
                    total_closed = analyzer.total.closed
                    total_won = analyzer.won.total
                    winrate = (total_won / total_closed)
                    ret = float(sqrt(strat.broker.getvalue()))
                    val = winrate * winrate * ret

                if(optType=='SQN'):
                    analyzer = strat.analyzers.sqn.get_analysis()
                    sqn = analyzer['sqn']
                    ret = float(sqrt(strat.broker.getvalue()))
                    val = sqn * sqn * sqn * ret

                if(optType=='DrawDown'):
                    analyzer = strat.analyzers.ta.get_analysis()
                    total_closed = analyzer.total.closed
                    total_won = analyzer.won.total
                    winrate = (total_won / total_closed)
                    ret = float(sqrt(strat.broker.getvalue()))
                    ddown = strat.analyzers.drawdown.get_analysis().max.drawdown
                    val = ret * winrate / ddown

                if(optType=='Sharpe'):
                    sharperatio = strat.analyzers.sharperatio.get_analysis()['sharperatio']
                    ret = float(sqrt(strat.broker.getvalue()))
                    val = sharperatio * ret

                if(optType=='Ado'):
                    analyzer = strat.analyzers.ta.get_analysis()
                    total_closed = analyzer.total.closed
                    total_won    = analyzer.won.total
                    winrate      = (total_won / total_closed)
                    sqn          = strat.analyzers.sqn.get_analysis()['sqn']
                    sharperatio  = strat.analyzers.sharperatio.get_analysis()['sharperatio']
                    ret          = float(sqrt(strat.broker.getvalue()))
                    ddown        = strat.analyzers.drawdown.get_analysis().max.drawdown
                    val          = ret * sqn * sqn * winrate * winrate * total_won  / ddown
                
                if(optType=='All'):
                    analyzer = strat.analyzers.ta.get_analysis()
                    total_closed = analyzer.total.closed
                    total_won    = analyzer.won.total
                    winrate      = (total_won / total_closed)
                    sqn          = strat.analyzers.sqn.get_analysis()['sqn']
                    sharperatio  = strat.analyzers.sharperatio.get_analysis()['sharperatio']
                    ret          = float(sqrt(strat.broker.getvalue()))
                    ddown        = strat.analyzers.drawdown.get_analysis().max.drawdown
                    val          = ret * sqn * winrate / ddown

                print(str(pars) +" ::: "+ str(val))
                val_list.append([val,pars])
                res = max(val_list, key=itemgetter(0))
                args[i] = res[1][i]
        # print out the result
        print("Optimizing "+optType+" ..." +str(int(((i+1)/(len(default_args)-startindex))*100)) +"/100")
    tend = time.time()
    print('Time used:', str(tend - tstart))
    #print(args)
    return args
    
def initDataDate(fromdate,todate,timeframe,target=COIN_TARGET,refresh=False):
    ### Get Data ###
    path = gd.get_Date_Data(fromdate,todate,timeframe,target,refresh)
    ### Load Data ###
    data = bt.feeds.GenericCSVData(name=target, dataname=path, timeframe=bt.TimeFrame.Minutes, fromdate=fromdate, todate=todate)
    print("BackTesting Data of: "+ path)
    return data

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

def testCoinList(strat,args):
    val_coin_list =list()
    coinList = ["MATIC","NEAR"]
    for coin in coinList:
        Delay = 0
        Dayz = 999
        data = initData(Dayz,Delay,Client.KLINE_INTERVAL_15MINUTE,coin,False)
        val_coin_list.append(rundata(strat,args,data,False,True))

    print("Best value:"+str(max(val_coin_list)))
   
def StdDateInit(tf):
    fromdate = datetime.datetime.strptime('2021-01-17', '%Y-%m-%d')
    fromdate = fromdate.date()
    todate = datetime.date.today() + datetime.timedelta(days=1)
    return initDataDate(fromdate,todate,Client.KLINE_INTERVAL_15MINUTE,"AVAX",tf)

def StartDateInit(tf):
    fromdate = datetime.datetime.strptime('2022-09-01', '%Y-%m-%d')
    fromdate = fromdate.date()
    todate = datetime.date.today() + datetime.timedelta(days=1)
    return initDataDate(fromdate,todate,Client.KLINE_INTERVAL_15MINUTE,"AVAX",tf)

def getMontlyReturns():
    a = 8 * 3
    val =0
    for i in range (0,a):
        Delay = 30 * i
        Dayz = 33
        data = initData(Dayz,Delay,Client.KLINE_INTERVAL_15MINUTE,"AVAX",reget)
        val += (rundata(MyStratV1,[2,271,2,910,160,56,213,254,436,1617,19,530,346,101,175,340,568,1169,281],data,False,False))/1000
    print("Montly Return:" +str(val/a))

val_list =list()

if __name__ == '__main__':
    reget = False
    Delay = 0
    Dayz = 999
    #data = initData(Dayz,Delay,Client.KLINE_INTERVAL_15MINUTE,"AVAX",reget)
    #data = StartDateInit(True) #Standart Date to today test
    data = StdDateInit(reget) #Standart Date to today test

    #######  V1  #########
    #################### AVAX ####################
    #val_list.append(rundata(MyStratV1,optimizeStrat(MyStratV1,[2,271,2,910,160,56,259,254,1617,19,525,348,101,175,340,1161,572,280,160,-1,-1],7,data,optType="Ado"),data,True,True))
    
    val_list.append(rundata(MyStratV1,[2,271,2,910,160,56,213,254,1617,19,530,347,101,175,340,1169,569,280,149,-1,-1],data,False,True,"All"))
    val_list.append(rundata(MyStratV1,[2,271,2,910,160,56,259,254,1617,19,525,348,101,175,340,1161,572,280,160,-1,-1],data,False,True,"All"))

    #print("Best value:"+str(max(val_list))) 
    #getMontlyReturns()
    #testCoinList(MyStratV5,[2,271,2,910,160,56,213,254,436,1617,19,530,346,101,175,340,568,1169,281])

    # oversold or overbought TEMADiff based on volitliy
    
    #################### Tested Strats ####################
    #val_list.append(rundata(BBMomentumStrat,optimizeStrat(BBMomentumStrat,[20,200,10,18,10,10,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1],3,data,optType="All"),data,True,True))

    #val_list.append(rundata(BBMomentumStrat,[20,200,10,18,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1],data,True,True))
    #val_list.append(rundata(TStrat1,[19,3013,1640,71,100,225,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1],data,True,True))

    #################### Test Random Strat ####################
    #val_list.append(rundata(TestStrat,optimizeStrat(TestStrat,[2,271,19,3013,2000,71,100,19,3013,1640,71,100,225],3,data,optType="All"),data,True,True))
    #val_list.append(rundata(TestStrat,[2,271,19,3013,2000,71,100,19,3013,1640,71,100,225],data,True,True))


    #for i in range(1,60):
    #    val_list.append(rundata(TestStrat,[31,200*i,100*i,-1,-1,-1,-1], data,False,False))

    #val_list.append(rundata(TestStrat,[7,4335,2522,-1,-1,-1,-1], data,True,True))

    #val_list.append(rundata(TestStrat,optimizeStrat(TestStrat,[19,200,103,180,6,-1,-1],15,data,optType="Return"),data,True,True))
    #val_list.append(rundata(TestStrat,[19,200,103,180,6,-1,-1],data,True,True))

    #----------------------------- Diversification ------------------------------#
    # BTC, ETH, BNB, FTT, ADA, Matic, XTZ(has good data) -/Non Corrolated/- => Stocks, PAXGOLD , EURUSDT , GBPUSDT 

    #################### BTC ####################
    #data = initData(800,0,Client.KLINE_INTERVAL_15MINUTE,"BTC",False) 
    #val_list.append(rundata(MyStratV6,optimizeStrat(MyStratV6,[3,285,2,789,123,55,1565,1312,368,829,22,339,358,38,5280,6216,633,1152,75,153,356],15,data,optType="All"),data,True,True))
    
    #val_list.append(rundata(MyStratV6,[3,303,2,789,146,55,1565,1312,368,1159,22,345,358,38,5127,5280,633,1152,52,153,296],data,False,True))
    #val_list.append(rundata(MyStratV6,[3,285,2,999,123,55,1565,1312,368,829,22,339,358,38,5280,6216,633,1152,75,153,356],data,False,True))
    #val_list.append(rundata(MyStratV6,[4,277,2,873,107,55,1565,1312,368,829,22,339,358,38,5280,6216,585,1152,75,153,410],data,False,True))
    #val_list.append(rundata(MyStratV6,[4,277,2,873,107,55,1565,1312,368,709,22,339,358,38,5280,6216,585,1152,75,153,414],data,False,True))

    #for a in range (6,30):
    #    val_list.append(rundata(MyStratV6,[2,277,2,910,107,56,21*a,25*a,633,1617,19,530,346,101,289,578,568,1169,60,200,1],data,False,False))


    #################### PAXG ####################
    #data = initData(800,0,Client.KLINE_INTERVAL_1HOUR,"PAXG",False)    
    #val_list.append(rundata(MyStratV6,optimizeStrat(MyStratV6,[18,277,6,946,136,38,1899,1821,368,1264,16,509,331,74,3178,2793,568,1169,7,7,295],7,data,optType="All"),data,True,True))
    #val_list.append(rundata(MyStratV6,[18,277,6,946,136,38,1899,1821,368,1264,16,509,331,74,3178,2793,568,1169,7,7,295],data,True,True))

    print("Best value:"+str(max(val_list))) 


