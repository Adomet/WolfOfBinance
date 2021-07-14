from math import log
from multiprocessing import set_forkserver_preload
from operator import itemgetter, truth
from os import name, stat

from backtrader import broker, cerebro, order,sizers
from backtrader.sizers.percents_sizer import PercentSizer
import get_data as gd, backtrader as bt, datetime
import time
from config import COIN_REFER, COIN_TARGET

class RSIStrategy(bt.Strategy):
    params=(('p0',0),('p1',0),('p2',0),('p3',0),('p4',0),('p5',0),('p6',0),('p7',0),('p8',0))
    def __init__(self):
        self.rsi             = bt.ind.RSI(self.data, period=self.params.p0)
        self.rsi_low         = self.params.p1
        self.rsi_heigh       = self.params.p2
        self.loss_treshold   = self.params.p3
        self.stop_loss       = self.params.p4
        self.buyprice        = -1
        self.ordered =False

    def order(self, isbuy):
        if(self.ordered):
            return
        
        if(isbuy and not self.position):
            self.buyprice = self.data.close[0]
            size = self.broker.get_cash() / self.data
            self.buy(size=size)
            self.ordered =True
        elif(not isbuy and self.position):
            self.buyprice = -1
            self.close()
            self.ordered =True


    def next(self):
        self.ordered = False
        if self.rsi < self.rsi_low:
            self.order(True)


        if self.rsi > self.rsi_heigh:
            self.order(False)


class AVGDiff(bt.Strategy):
    params=(('p0',0),('p1',0),('p2',0),('p3',0),('p4',0),('p5',0),('p6',0),('p7',0),('p8',0))

    def __init__(self):
        ## SMA #
        self.ema              = bt.ind.EMA(period=self.params.p0) 
        self.avgselldiffactor = self.params.p1
        self.avgbuydiffactor  = self.params.p2
        self.stop_loss        = self.params.p3
        self.loss_treshold    = self.params.p4
        self.buyprice = -1

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

class MyStratV2(bt.Strategy):
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
        self.loss_treshold        =  self.params.p8

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
        avgdiff      = (self.data - self.diff_ema)
        tmp          = (self.trend_fast_ema > self.trend_slow_ema)
        isTrendSame  = (tmp==self.isBull)
        isSellable   = (self.data.close[0] > self.buyprice - (self.buyprice * self.loss_treshold/1000))
        isStop       = (self.data.close[0] < self.buyprice - (self.buyprice * self.stop_loss/1000))
        isProfitStop = (self.data.close[0] > self.buyprice - self.buyprice  * self.stop_loss*1.5/1000 and isSellable)
        self.ordered =False

        #if self.isBull != tmp:
        #   print("isBull Switched to : "+str(not self.isBull) +":"+str(self.data.close[0]))

        #if(isProfitStop):
        #    self.order(False)

        if (self.isBull and not isTrendSame and isSellable):
            self.orderer(False)
        
        if (not self.isBull and not isTrendSame):
            self.orderer(True)

        self.isBull = tmp

        if (self.isBull):
            if avgdiff < -self.diff_ema*10/self.bullavgbuydiffactor:
                self.orderer(True)

            if avgdiff > self.diff_ema*10/self.bullavgselldiffactor and isSellable:
                self.orderer(False)
        else:
            if avgdiff < -self.diff_ema*10/self.bearavgbuydiffactor:
                self.orderer(True)

            if avgdiff > self.diff_ema*10/self.bearavgselldiffactor and isSellable:
                self.orderer(False)

        if (isStop):
            self.orderer(False)


trans =0
total_fee =0

### Runs Data at a strategy and its parameters can plot or give info about result returns end value of trades ###
def rundata(strategy, args, plot, info):
    cerebro = bt.Cerebro()

    if(strategy == RSIStrategy):
        cerebro.addstrategy(strategy,p0=args[0],p1=args[1],p2=args[2],p3=args[3],p4=args[4])
    elif(strategy == AVGDiff):
        cerebro.addstrategy(strategy,p0=args[0],p1=args[1],p2=args[2],p3=args[3],p4=args[4])
    elif(strategy ==MyStratV2):
        cerebro.addstrategy(strategy,p0=args[0],p1=args[1],p2=args[2],p3=args[3],p4=args[4],p5=args[5],p6=args[6],p7=args[7],p8=args[8])

    restr = ""
    for i in range(0, len(args)):
        restr += str(args[i])

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

    StartCash = 10000
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
        cerebro = bt.Cerebro(optreturn=False,maxcpus=1)

        step    = int(max(abs(default_args[i]/100), 1))
        diff    = step * scan_range
        heigh   = default_args[i]+diff+step
        low     = default_args[i]-diff-step
        args[i] =(range(int(low), int(heigh), int(step)))

        if(strategy == RSIStrategy):
            cerebro.optstrategy(strategy,p0=args[0],p1=args[1],p2=args[2],p3=args[3],p4=args[4])
        elif(strategy == AVGDiff):
            cerebro.optstrategy(strategy,p0=args[0],p1=args[1],p2=args[2],p3=args[3],p4=args[4])
        elif(strategy ==MyStratV2):
            cerebro.optstrategy(strategy,p0=args[0],p1=args[1],p2=args[2],p3=args[3],p4=args[4],p5=args[5],p6=args[6],p7=args[7],p8=args[8])

    
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



def initData(traindays,testdays,refresh=False):
    ### Choose Time period of Backtest ###
    today    = datetime.date.today() #- datetime.timedelta(days=4)
    today    = today - datetime.timedelta(days=testdays)
    fromdate = today - datetime.timedelta(days=traindays)
    todate   = today + datetime.timedelta(days=1)
    
    #fromdate = datetime.datetime.strptime('2021-05-18', '%Y-%m-%d')
    #todate = datetime.datetime.strptime('2021-06-30', '%Y-%m-%d') #today #datetime.datetime.strptime('2021-05-30', '%Y-%m-%d')
    #fromdate = fromdate.date()
    #todate = todate.date()

    ### Get Data ###
    gd.get_Date_Data(fromdate,todate,refresh)
    path = str(fromdate)+"="+str(todate)+".csv"
    ### Load Data ###
    data = bt.feeds.GenericCSVData(name=COIN_TARGET, dataname=path,timeframe=bt.TimeFrame.Minutes, fromdate=fromdate, todate=todate)
    print("BackTesting Data of: "+ str(fromdate)+" --->> "+str(todate))
    return data




val_list =list()
if __name__ == '__main__':
   #lst = [14,15,16]

   #for t in lst:
   #    print("testing",t)
   #    data = initData(t,8)
   #    args = optimizeStrat(MyStratV2,[356, 454, 190, 79, 187, 178, 192, 13, -37], 20)
   #    data = initData(8,0)
   #    val = rundata(MyStratV2,args,False,False)
   #    val_list.append([val,t])
   # 
   #    print("Best value:"+str(max(val_list,key=itemgetter(0))))


       
    data = initData(47,0,False)

    val_list.append(rundata(MyStratV2,[356, 454, 193, 79, 122, 178, 191, 16, -37],False,False))
    val_list.append(rundata(MyStratV2,[356, 454, 190, 79, 187, 178, 192, 13, -37],False,False))
    val_list.append(rundata(MyStratV2,optimizeStrat(MyStratV2,[356, 454, 190, 79, 187, 178, 192, 13, -37], 20,data),False,False))


    print("Best value:"+str(max(val_list)))
