import datetime
import time
from math import sqrt
from operator import itemgetter
from statistics import stdev
from indicators import SuperTrend, AverageRage, EWO
from strategies.MyStratV4 import MyStratV4
from strategies.MyStratV5 import MyStratV5

import backtrader as bt
from binance.client import Client

import get_data as gd
from config import COIN_REFER, COIN_TARGET

       
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

def addParamstoCerebro(cerebro, strategy, args):
    params = {f'p{i}': args[i] for i in range(len(args))}
    cerebro.addstrategy(strategy, **params)

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
        print("TradePerCandle:" + str(results[0].analyzers.ta.get_analysis().total.closed/(len(data.close) +1)))
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

def addParamstoOptCerebro(cerebro, strategy, args):
    params = {f'p{i}': args[i] for i in range(len(args))}
    cerebro.optstrategy(strategy, **params)

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
        stratruns = cerebro.run(maxcpus=8)

    
        for stratrun in stratruns:
            pars = []
            for strat in stratrun:
                pars.extend(getattr(strat.params, f'p{i}') for i in range(len(args)))

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

val_list =list()

if __name__ == '__main__':
    reget = False
    Delay = 0
    Dayz = 930
    data = initData(Dayz,Delay,Client.KLINE_INTERVAL_15MINUTE,"AVAX",reget)
    #data = StartDateInit(True) #Standart Date to today test
    #data = StdDateInit(reget) #Standart Date to today test

    val_list.append(rundata(MyStratV5,optimizeStrat(MyStratV5,[263,930,150,24,294,765,1382,20,570,330,126,139,204,1135,533,220,131,82,77,36,69],7,data,optType="All"),data,True,True))
    #val_list.append(rundata(MyStratV5,[263,930,150,24,294,765,1382,20,570,330,126,139,204,1135,533,220,131,82,77,36,69,51,21],data,True,True))

    print("Best value:"+str(max(val_list))) 


