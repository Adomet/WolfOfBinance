from ast import And, arg
from itertools import count
from math import fabs, log
from multiprocessing import set_forkserver_preload
from operator import isub, itemgetter, truth
from os import F_OK, name, stat
from re import S
from binance.client import Client
from backtrader import broker, cerebro, order,sizers
import backtrader as bt
from backtrader.sizers.percents_sizer import PercentSizer
from backtrader.utils import ordereddefaultdict
from numpy import busday_count, true_divide
from pandas import period_range
from sqlalchemy import false
import get_data as gd, backtrader as bt, datetime
import time
from config import COIN_REFER, COIN_TARGET

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
    params=(('p0',0),('p1',0),('p2',0),('p3',0),('p4',0),('p5',0),('p6',0),('p7',0),('p8',0),('p9',0),('p10',0),('p11',0),('p12',0),('p13',0),('p14',0),('p15',0),('p16',0),('p17',0),('p18',0),('p19',0),('p20',0),('p21',0))
    def __init__(self):
        self.params.p0                 =  max(self.params.p0,1)
        self.supertrend                =  SuperTrend(self.data,period=self.params.p0,multiplier=max(self.params.p1/10,1))
        self.superisBull               =  bt.ind.CrossOver(self.data.close,self.supertrend)
        self.tdnine                    =  TD9()
        self.isbull                    =  False

        #BULL
        self.params.p2                 =  max(self.params.p2,2)
        self.bull_rsi                  =  bt.ind.RelativeStrengthIndex(self.data, period=self.params.p2,safediv=True)
        self.bull_rsi_high             =  self.params.p3
        self.bull_rsi_low              =  self.params.p4
        self.bull_td9_high             =  self.params.p5
        self.bull_td9_low              =  self.params.p6
        self.params.p7                 =  max(self.params.p7,1)
        self.bull_diff_ema             =  bt.ind.TripleExponentialMovingAverage(period=self.params.p7)
        self.bull_avgselldiffactor     =  self.params.p8
        self.bull_avgbuydiffactor      =  self.params.p9
        self.bull_diff_ema_heigh       =  self.bull_diff_ema + (self.bull_diff_ema / self.bull_avgselldiffactor * 10) 
        self.bull_diff_ema_low         =  self.bull_diff_ema - (self.bull_diff_ema / self.bull_avgbuydiffactor  * 10)           
        self.bull_stop_loss            =  self.params.p10
        self.bull_RiskReward           =  self.params.p11
        self.bull_takeprofit           =  self.bull_stop_loss * self.bull_RiskReward / 100

        #BEAR
        self.params.p12                =  max(self.params.p12,2)
        self.bear_rsi                  =  bt.ind.RelativeStrengthIndex(self.data, period=self.params.p12,safediv=True)
        self.bear_rsi_high             =  self.params.p13
        self.bear_rsi_low              =  self.params.p14
        self.bear_td9_high             =  self.params.p15
        self.bear_td9_low              =  self.params.p16
        self.params.p17                =  max(self.params.p17,1)
        self.bear_diff_ema             =  bt.ind.TripleExponentialMovingAverage(period=self.params.p17)
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
            buysize = int(self.broker.get_cash()*99/100) / self.data.close[0]
            self.buy(size=buysize)
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
            bull_isStop             = (self.data.close[0] <   self.buyprice - (self.buyprice * self.bull_stop_loss/1000))
            bull_isTakeProfit       = (self.data.close[0] >   self.buyprice + (self.buyprice * self.bull_takeprofit/1000)) and not self.buyprice ==-1
            bull_td9selltrigger     = self.tdnine         >=  self.bull_td9_high
            bull_td9buytrigger      = self.tdnine         <= -self.bull_td9_low
            bull_rsiselltrigger     = self.bull_rsi       >=  self.bull_rsi_high 
            bull_rsibuytrigger      = self.bull_rsi       <=  self.bull_rsi_low
            bull_avgdiffselltrigger = self.data.close[0]  >=  self.bull_diff_ema_heigh
            bull_avgdiffbuytrigger  = self.data.close[0]  <=  self.bull_diff_ema_low


            if((bull_td9buytrigger     and bull_rsibuytrigger  and bull_avgdiffbuytrigger )):
                self.orderer(True)
            elif((bull_td9selltrigger  and bull_rsiselltrigger and bull_avgdiffselltrigger)):
                self.orderer(False)
            elif(bull_isStop):
                self.orderer(False)
            elif(bull_isTakeProfit):
                self.orderer(False)

        else:
            bear_isStop             = (self.data.close[0] <   self.buyprice - (self.buyprice * self.bear_stop_loss/1000))
            bear_isTakeProfit       = (self.data.close[0] >   self.buyprice + (self.buyprice * self.bear_takeprofit/1000)) and not self.buyprice ==-1
            bear_td9selltrigger     = self.tdnine         >=  self.bear_td9_high
            bear_td9buytrigger      = self.tdnine         <= -self.bear_td9_low
            bear_rsiselltrigger     = self.bear_rsi       >=  self.bear_rsi_high 
            bear_rsibuytrigger      = self.bear_rsi       <=  self.bear_rsi_low
            bear_avgdiffselltrigger = self.data.close[0]  >=  self.bear_diff_ema_heigh
            bear_avgdiffbuytrigger  = self.data.close[0]  <=  self.bear_diff_ema_low


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

class MyStratV2(bt.Strategy):
    params=(('p0',0),('p1',0),('p2',0),('p3',0),('p4',0),('p5',0),('p6',0),('p7',0),('p8',0),('p9',0),('p10',0),('p11',0),('p12',0),('p13',0),('p14',0),('p15',0),('p16',0),('p17',0),('p18',0),('p19',0),('p20',0),('p21',0),('p22',0))
    def __init__(self):
        self.params.p0                 =  max(self.params.p0,1)
        self.supertrend                =  SuperTrend(self.data,period=self.params.p0,multiplier=max(self.params.p1/10,1))
        self.superisBull               =  bt.ind.CrossOver(self.data.close,self.supertrend)
        self.tdnine                    =  TD9()
        self.params.p22                =  max(self.params.p22,1)
        self.roc                       =  bt.ind.RateOfChange100(self.data,period=13)
        self.roc_BuyTreshold           =  self.params.p22
        self.roc_minBuyTreshold        =  self.params.p22
        self.isbull                    =  False

        #BULL
        self.params.p2                 =  max(self.params.p2,2)
        self.bull_rsi                  =  bt.ind.RelativeStrengthIndex(self.data, period=self.params.p2,safediv=True)
        self.bull_rsi_high             =  self.params.p3
        self.bull_rsi_low              =  self.params.p4
        self.bull_td9_high             =  self.params.p5
        self.bull_td9_low              =  self.params.p6
        self.params.p7                 =  max(self.params.p7,1)
        self.bull_diff_ema             =  bt.ind.TripleExponentialMovingAverage(period=self.params.p7)
        self.bull_avgselldiffactor     =  self.params.p8
        self.bull_avgbuydiffactor      =  self.params.p9
        self.bull_diff_ema_heigh       =  self.bull_diff_ema + (self.bull_diff_ema / self.bull_avgselldiffactor * 10) 
        self.bull_diff_ema_low         =  self.bull_diff_ema - (self.bull_diff_ema / self.bull_avgbuydiffactor  * 10)           
        self.bull_stop_loss            =  self.params.p10
        self.bull_RiskReward           =  self.params.p11
        self.bull_takeprofit           =  self.bull_stop_loss * self.bull_RiskReward / 100

        #BEAR
        self.params.p12                =  max(self.params.p12,2)
        self.bear_rsi                  =  bt.ind.RelativeStrengthIndex(self.data, period=self.params.p12,safediv=True)
        self.bear_rsi_high             =  self.params.p13
        self.bear_rsi_low              =  self.params.p14
        self.bear_td9_high             =  self.params.p15
        self.bear_td9_low              =  self.params.p16
        self.params.p17                =  max(self.params.p17,1)
        self.bear_diff_ema             =  bt.ind.TripleExponentialMovingAverage(period=self.params.p17)
        self.bear_avgselldiffactor     =  self.params.p18
        self.bear_avgbuydiffactor      =  self.params.p19
        self.bear_diff_ema_heigh       =  self.bear_diff_ema + (self.bear_diff_ema / self.bear_avgselldiffactor * 10) 
        self.bear_diff_ema_low         =  self.bear_diff_ema - (self.bear_diff_ema / self.bear_avgbuydiffactor  * 10)           
        self.bear_stop_loss            =  self.params.p20
        self.bear_RiskReward           =  self.params.p21
        self.bear_takeprofit           =  self.bear_stop_loss * self.bear_RiskReward / 100

        self.buyprice                  =  -1
        self.ordered                   =  False

    def orderer(self, isbuy):
        if(self.ordered):
            return
        
        if(isbuy and not self.position):
            self.buyprice = self.data.close[0]
            buysize = int(self.broker.get_cash()*99/100) / self.data.close[0]
            self.buy(size=buysize)
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
            bull_isStop             = (self.data.close[0] <   self.buyprice - (self.buyprice * self.bull_stop_loss/1000))
            bull_isTakeProfit       = (self.data.close[0] >   self.buyprice + (self.buyprice * self.bull_takeprofit/1000)) and not self.buyprice ==-1
            bull_td9selltrigger     = self.tdnine         >=  self.bull_td9_high
            bull_td9buytrigger      = self.tdnine         <= -self.bull_td9_low
            bull_rsiselltrigger     = self.bull_rsi       >=  self.bull_rsi_high 
            bull_rsibuytrigger      = self.bull_rsi       <=  self.bull_rsi_low
            bull_avgdiffselltrigger = self.data.close[0]  >=  self.bull_diff_ema_heigh
            bull_avgdiffbuytrigger  = self.data.close[0]  <=  self.bull_diff_ema_low


            if((bull_td9buytrigger     and bull_rsibuytrigger  and bull_avgdiffbuytrigger )):
                self.orderer(True)
            elif((bull_td9selltrigger  and bull_rsiselltrigger and bull_avgdiffselltrigger)):
                self.orderer(False)
            elif(bull_isStop):
                self.orderer(False)
            elif(bull_isTakeProfit):
                self.orderer(False)

        else:
            bear_isStop             = (self.data.close[0] <   self.buyprice - (self.buyprice * self.bear_stop_loss/1000))
            bear_isTakeProfit       = (self.data.close[0] >   self.buyprice + (self.buyprice * self.bear_takeprofit/1000)) and not self.buyprice ==-1
            bear_td9selltrigger     = self.tdnine         >=  self.bear_td9_high
            bear_td9buytrigger      = self.tdnine         <= -self.bear_td9_low
            bear_rsiselltrigger     = self.bear_rsi       >=  self.bear_rsi_high 
            bear_rsibuytrigger      = self.bear_rsi       <=  self.bear_rsi_low
            bear_avgdiffselltrigger = self.data.close[0]  >=  self.bear_diff_ema_heigh
            bear_avgdiffbuytrigger  = self.data.close[0]  <=  self.bear_diff_ema_low

            if(bear_td9buytrigger     and bear_rsibuytrigger  and bear_avgdiffbuytrigger):
                self.orderer(True)
            elif((bear_td9selltrigger  and bear_rsiselltrigger and bear_avgdiffselltrigger)):
                self.orderer(False)
            elif(bear_isStop):
                self.orderer(False)
            elif(bear_isTakeProfit):
                self.orderer(False)
        
        ### NEW STUFF ###
        self.rocbuytrigger          = self.roc >= self.data.close[0] * self.roc_BuyTreshold /1000 and self.isbull
        if(self.rocbuytrigger):
            #print("roc: " + str(self.data.close[0] * 575 /1000))
            self.orderer(True)

class MyStratV3(bt.Strategy):
    params=(('p0',0),('p1',0),('p2',0),('p3',0),('p4',0),('p5',0),('p6',0),('p7',0),('p8',0),('p9',0),('p10',0),('p11',0))
    def __init__(self):
        self.params.p0                 =  max(self.params.p0,1)
        self.supertrend                =  SuperTrend(self.data,period=self.params.p0,multiplier=max(self.params.p1/10,1))
        self.superisBull               =  bt.ind.CrossOver(self.data.close,self.supertrend)
        self.isbull                    =  False
        
        ##roc##
        #self.params.p22                =  max(self.params.p22,1)
        #self.roc                       =  bt.ind.RateOfChange100(self.data,period=13)
        #self.roc_BuyTreshold           =  self.params.p22
        #self.roc_minBuyTreshold        =  self.params.p22

        #BULL
        self.params.p2                 =  max(self.params.p2,1)
        self.bull_diff_ema             =  bt.ind.TripleExponentialMovingAverage(period=self.params.p2)

        self.bullbuystep               =  max(self.params.p3,1)
        self.bullsellstep              =  max(self.params.p4,1)

        self.bull_stop_loss            =  self.params.p5
        self.bull_RiskReward           =  self.params.p6
        self.bull_takeprofit           =  self.bull_stop_loss * self.bull_RiskReward / 100

        #BEAR
        self.params.p7                 =  max(self.params.p7,1)
        self.bear_diff_ema             =  bt.ind.TripleExponentialMovingAverage(period=self.params.p7)
        
        self.bearbuystep               =  max(self.params.p8,1)
        self.bearsellstep              =  max(self.params.p9,1)

        self.bear_stop_loss            =  self.params.p10
        self.bear_RiskReward           =  self.params.p11
        self.bear_takeprofit           =  self.bear_stop_loss * self.bear_RiskReward / 100

        self.buyprice                  =  -1
        self.ordered                   =  False

        self.buycount                  = 1
        self.sellcount                 = 1


    def orderer(self, isbuy):
        if(self.ordered):
            return
        
        if(isbuy):
            self.buyprice = self.data.close[0]
            buysize = int(self.broker.get_cash()*self.buycount*8/128) / self.data.close[0]
            self.buy(size=buysize)
            self.ordered =True
            self.buycount +=1
            self.sellcount =0
            #print("buycount " +str(self.buycount))

        elif(not isbuy):
            sellsize = int((self.broker.get_value()-self.broker.get_cash()) *self.sellcount*8/128) / self.data.close[0]
            self.buyprice = -1
            self.sell(size=sellsize)
            self.ordered =True
            self.sellcount +=1
            self.buycount   =0
            #print("sellcount " +str(self.sellcount))
        

    def next(self):
        self.ordered = False
        if(not self.superisBull[0] == 0):
                self.isbull = (self.superisBull[0] == 1)

        if(self.isbull):
            bull_isStop             = (self.data.close[0] <   self.buyprice - (self.buyprice * self.bull_stop_loss/1000))
            bull_isTakeProfit       = (self.data.close[0] >   self.buyprice + (self.buyprice * self.bull_takeprofit/1000)) and not self.buyprice ==-1
            
            bull_buy                = (self.data.close[0] <   self.bull_diff_ema - (self.bull_diff_ema * self.bullbuystep  * self.buycount / 1000))
            bull_sell               = (self.data.close[0] >   self.bull_diff_ema + (self.bull_diff_ema * self.bullsellstep * self.sellcount / 1000))



            if((bull_buy)):
                self.orderer(True)
            elif((bull_sell)):
                self.orderer(False)
                
            elif(bull_isStop):
                self.orderer(False)
            elif(bull_isTakeProfit):
                self.orderer(False)

        else:
            bear_isStop             = (self.data.close[0] <   self.buyprice - (self.buyprice * self.bear_stop_loss/1000))
            bear_isTakeProfit       = (self.data.close[0] >   self.buyprice + (self.buyprice * self.bear_takeprofit/1000)) and not self.buyprice ==-1

            bear_buy                = (self.data.close[0] <   self.bear_diff_ema - (self.bear_diff_ema * self.bearbuystep * self.buycount  / 1000))
            bear_sell               = (self.data.close[0] >   self.bear_diff_ema + (self.bear_diff_ema * self.bearsellstep * self.sellcount / 1000))

            if(bear_buy):
                self.orderer(True)
            elif((bear_sell)):
                self.orderer(False)

            elif(bear_isStop):
                self.orderer(False)
            elif(bear_isTakeProfit):
                self.orderer(False)
        
        ### NEW STUFF ###
        #self.rocbuytrigger          = self.roc >= self.data.close[0] * self.roc_BuyTreshold /1000 and self.isbull
        #if(self.rocbuytrigger):
        #    #print("roc: " + str(self.data.close[0] * 575 /1000))
        #    self.orderer(True)


#### General Functions ####

trans =0
total_fee =0

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
    if(cnt==22):
        cerebro.addstrategy(strategy,p0=args[0],p1=args[1],p2=args[2],p3=args[3],p4=args[4],p5=args[5],p6=args[6],p7=args[7],p8=args[8],p9=args[9],p10=args[10],p11=args[11],p12=args[12],p13=args[13],p14=args[14],p15=args[15],p16=args[16],p17=args[17],p18=args[18],p19=args[19],p20=args[20],p21=args[21],p22=args[22])
    elif(cnt==21):
        cerebro.addstrategy(strategy,p0=args[0],p1=args[1],p2=args[2],p3=args[3],p4=args[4],p5=args[5],p6=args[6],p7=args[7],p8=args[8],p9=args[9],p10=args[10],p11=args[11],p12=args[12],p13=args[13],p14=args[14],p15=args[15],p16=args[16],p17=args[17],p18=args[18],p19=args[19],p20=args[20],p21=args[21])
    elif(cnt==11):
        cerebro.addstrategy(strategy,p0=args[0],p1=args[1],p2=args[2],p3=args[3],p4=args[4],p5=args[5],p6=args[6],p7=args[7],p8=args[8],p9=args[9],p10=args[10],p11=args[11])
    elif(cnt==6):
        cerebro.addstrategy(strategy,p0=args[0],p1=args[1],p2=args[2],p3=args[3],p4=args[4],p5=args[5],p6=args[6])
    else:
        print(str(cnt) +" No array params match!")

### Runs Data at a strategy and its parameters can plot or give info about result returns end value of trades ###
def rundata(strategy, args,data, plot, info):
    StartCash = 1000
    cerebro = bt.Cerebro()

    addParamstoCerebro(cerebro,strategy,args)

    cerebro.broker.setcash(StartCash)
    cerebro.adddata(data)
    # Add the analyzers we are interested in
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="ta")
    cerebro.addanalyzer(bt.analyzers.SQN, _name="sqn")
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharperatio')
    #cerebro.addsizer(PercentSizer,percents=99)
    broker = cerebro.getbroker()
    broker.setcommission(commission=0.001,name=COIN_TARGET)
    results = cerebro.run()

    val = cerebro.broker.getvalue()

    restr = ""
    for i in range(0, len(args)):
        restr += str(args[i]) + ","
    
    print(restr+" trans:"+str(trans)+":::"+str(val))
    #print("Confidance:" + str(conf))
    if(info):
        Market_ratio = (data[0]/data[-len(data)+1])*100
        Bot_ratio = (val/StartCash) * 100
        Bot_Market_ratio = Bot_ratio/Market_ratio
        BotMarketDiff = Bot_ratio-Market_ratio
        print("Strat: "+strategy.__name__)
        print("In Pos:" + str(cerebro.broker.getposition(data).size != 0))
        print("start value:" + str(StartCash))
        print("final value:" + str(val))
        print("Market ratio:" + str(Market_ratio))
        print("Bot ratio:" + str(Bot_ratio))
        print("BotMarketDiff:"+str(BotMarketDiff))
        print("Bot / Market:" + str(Bot_Market_ratio))
        # print the analyzers
        printTradeAnalysis(results[0].analyzers.ta.get_analysis())
        printSQN(results[0].analyzers.sqn.get_analysis())
        printsharperatio(results[0].analyzers.sharperatio.get_analysis())

    if(plot):
        #cerebro.run()
        #cerebro.plot(style='candlestick')
        cerebro.plot()


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
    if(cnt==22):
        cerebro.optstrategy(strategy,p0=args[0],p1=args[1],p2=args[2],p3=args[3],p4=args[4],p5=args[5],p6=args[6],p7=args[7],p8=args[8],p9=args[9],p10=args[10],p11=args[11],p12=args[12],p13=args[13],p14=args[14],p15=args[15],p16=args[16],p17=args[17],p18=args[18],p19=args[19],p20=args[20],p21=args[21],p22=args[22])
    elif(cnt==21):
        cerebro.optstrategy(strategy,p0=args[0],p1=args[1],p2=args[2],p3=args[3],p4=args[4],p5=args[5],p6=args[6],p7=args[7],p8=args[8],p9=args[9],p10=args[10],p11=args[11],p12=args[12],p13=args[13],p14=args[14],p15=args[15],p16=args[16],p17=args[17],p18=args[18],p19=args[19],p20=args[20],p21=args[21])
    elif(cnt==11):
        cerebro.optstrategy(strategy,p0=args[0],p1=args[1],p2=args[2],p3=args[3],p4=args[4],p5=args[5],p6=args[6],p7=args[7],p8=args[8],p9=args[9],p10=args[10],p11=args[11])
    elif(cnt==6):
        cerebro.optstrategy(strategy,p0=args[0],p1=args[1],p2=args[2],p3=args[3],p4=args[4],p5=args[5],p6=args[6])
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
        if(default_args[i] == -9999):
            continue
        cerebro = bt.Cerebro(optreturn=False,maxcpus=8)

        scan_range = min(my_scan_range,abs(default_args[i]))
        step    = int(max(abs(default_args[i]/100), 1))
        diff    = step * scan_range
        heigh   = default_args[i]+diff+step
        low     = default_args[i]-diff-step
        args[i] =(range(int(low), int(heigh), int(step)))

        addParamstoOptCerebro(cerebro,strategy,args)

        StartCash = 1000
        cerebro.broker.setcash(StartCash)
        cerebro.adddata(data)
        cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="ta")
        cerebro.addanalyzer(bt.analyzers.SQN, _name="sqn")
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
                
                val = 0
                if(optType=='Return'):
                    val = strat.broker.getvalue()

                if(optType=='WinRate'):
                    analyzer = strat.analyzers.ta.get_analysis()
                    total_closed = analyzer.total.closed
                    total_won = analyzer.won.total
                    val = (total_won / total_closed) * strat.broker.getvalue()

                if(optType=='SQN'):
                    analyzer = strat.analyzers.sqn.get_analysis()
                    sqn = analyzer['sqn']
                    val =sqn * strat.broker.getvalue()

                if(optType=='Sharpe'):
                    val = strat.analyzers.sharperatio.get_analysis()['sharperatio'] * strat.broker.getvalue()
                
                if(optType=='All'):
                    analyzer = strat.analyzers.ta.get_analysis()
                    total_closed = analyzer.total.closed
                    total_won = analyzer.won.total
                    winrate = (total_won / total_closed)
                    sqn = strat.analyzers.sqn.get_analysis()['sqn']
                    sharperatio = strat.analyzers.sharperatio.get_analysis()['sharperatio']
                    ret = strat.broker.getvalue()
                    val =  ret * sqn * winrate

                print(val)
                val_list.append([val,pars])
                res = max(val_list, key=itemgetter(0))
                args[i] = res[1][i]
        # print out the result
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
    


def SrtDateInit(tf):
    fromdate = datetime.datetime.strptime('2021-01-21', '%Y-%m-%d')
    fromdate = fromdate.date()
    todate = datetime.date.today() + datetime.timedelta(days=1)
    return initDataDate(fromdate,todate,Client.KLINE_INTERVAL_15MINUTE,"AVAX",tf)

val_list =list()
if __name__ == '__main__':
    reget = False
    
    Delay = 0
    #Dayz = 666
    #Dayz = 234
    Dayz =79
    data = initData(Dayz,Delay,Client.KLINE_INTERVAL_15MINUTE,"AVAX",reget)

    #data = SrtDateInit(reget) #Standart Date to today test

    #######  V1 #########
    #val_list.append(rundata(MyStratV1,optimizeStrat(MyStratV1,[2,32,2,91,17,10,1,78,174,268,99,155,14,55,34,7,2,102,218,303,57,216],64,data,17),data,True,False))
    #val_list.append(rundata(MyStratV1,optimizeStrat(MyStratV1,[2,32,2,91,17,10,1,78,174,268,99,155,14,55,34,7,2,102,218,303,57,216],1,data),data,True,False))
    #val_list.append(rundata(MyStratV1,[2,32,2,91,17,10,1,78,174,268,99,155,14,55,34,7,2,102,218,303,57,216],data,False,False))#410 day best

    #######  V2 #########
    #val_list.append(rundata(MyStratV2,optimizeStrat(MyStratV2,[2,32,2,91,17,10,1,78,174,268,99,155,14,55,34,7,2,102,218,303,57,216,502]  ,8,data,22),data,True,False))
    #val_list.append(rundata(MyStratV2,optimizeStrat(MyStratV2,[2,28,2,91,17,10,-1,56,213,254,105,154,19,22,34,-1,-1,99,171,342,58,195,502]  ,32,data,optType='All'),data,True,False))



    ##BEST##
    val_list.append(rundata(MyStratV2,[2,28,2,91,17,10,-1,56,213,254,105,154,19,22,34,-1,-1,99,171,342,58,195,502],data,True,True))

    ## Return BOSS ##
    #val_list.append(rundata(MyStratV2,[2,32,2,91,17,10,1,78,174,268,99,155,14,55,34,7,2,102,218,303,57,216,502],data,False,True))#420 day best

    #######  V3 #########
    #data = initData(Dayz,Delay,Client.KLINE_INTERVAL_15MINUTE,"AVAX",False)
    #val_list.append(rundata(MyStratV3,optimizeStrat(MyStratV3,[2,32,100,16,16,99,155,100,16,16,57,216],32,data),data,True,False))
    #val_list.append(rundata(MyStratV3,[2, 35, 43, 3, 32, 99, 155, 136, 28, 2, 43, 130],data,False,False))
    #val_list.append(rundata(MyStratV3,[2,32,100,16,16,59,244,100,16,16,59,244],data,False,False))

    #######  V4 #########
    #val_list.append(rundata(MyStratV2,optimizeStrat(MyStratV2,[2,32,2,91,17,10,1,78,174,268,99,155,14,55,34,7,2,102,218,303,57,216,502]  ,8,data,22),data,True,False))
    #val_list.append(rundata(MyStratV2,optimizeStrat(MyStratV2,[2,32,2,91,17,10,1,78,174,268,99,155,14,55,34,7,2,102,218,303,57,216,502]  ,8,data),data,True,False))
    #val_list.append(rundata(MyStratV2,[3,55,4,96,31,4,-1,91,157,226,118,172,17,22,34,9,0,77,226,357,59,197,472],data,False,False))
    ##BEST##
    #val_list.append(rundata(MyStratV2,[2,32,2,91,17,10,1,78,174,268,99,155,14,55,34,7,2,102,218,303,57,216,502],data,True,False))#250 day best

    ### todo ###
    # Trailing stop loss
    # Sell price when buy
    # Trading Rush MACD strat to code MACD + 200 EMA pullback stoploss ez %62 percent try
    # Check 15m is wide enough
    # MACD needs to be added to main strat
    # 1 month test input 246$
    # does not chatch big upwards momentums big sadge
    # restrainin with candle length improves for some reason
    # Detect tooooooooooo bullsh pattern some how
    # check roc periods for best one
    # support and resistance detection fibbonacchi linear regression 
    # ichimoku cloud 
    # 3 supertrend +201 ema 
    # atr
    # start of trend after under or blow ema with atr diff buy sell for trend following
    # Grid trading
    # Dynamic StopLoss
    ############################# >>>>>>>>> Recalculate avg each time <<<<<<
    # if we are not going up we are going down
    #### Notes #####
    #vwap hullema
    #bar içi olaylara görede reaksiyon verme
    #monte carlo similasyonu

    ############# 30 m ##############################

    #data = initData(Dayz,Delay,Client.KLINE_INTERVAL_30MINUTE,"AVAX",False)
    #val_list.append(rundata(MyStratV2,optimizeStrat(MyStratV2,[6,42,5,78,20,8,2,39,180,270,91,151,14,37,35,7,1,49,194,348,50,214,502],32,data),data,True,False))
    #val_list.append(rundata(MyStratV2,[6,42,5,78,20,8,2,39,180,270,91,151,14,37,35,7,1,49,194,348,50,214,502],data,True,False))#250 day best
    #val_list.append(rundata(MyStratV2,[6,42,5,92,20,6,2,39,192,270,91,151,14,64,35,7,1,49,194,348,50,214,552],data,True,False))#250 day best


    print("Best value:"+str(max(val_list)))

        


