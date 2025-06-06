import datetime, time
from math import sqrt
from operator import itemgetter
import backtrader as bt
from binance.client import Client
import get_data as gd
from config import COIN_TARGET
from analyzers import AVGDD, GLP
import PPO.trainer as trainer
# Import strategies directly from their files
from strategies.AIStratDis import AIStratDis
from strategies.MyStratV1 import MyStratV1
from strategies.MyStratV2 import MyStratV2
from strategies.MyStratV3 import MyStratV3
from strategies.MyStratV4 import MyStratV4
from strategies.MyStratAI import MyStratAI, global_agent
from strategies.SMAOffsetV1 import SMAOffsetV1
from analysis import StrategyAnalysis
from optimization import OptimizationType, calculate_optimization_value
from Debug import log
import random
import numpy as np
import torch as T
import gc

def add_strategy_params_to_cerebro(cerebro, strategy, args, is_optimization=False):
    params = {f'p{i}': args[i] for i in range(len(args))}
    cerebro.optstrategy(strategy, **params) if is_optimization else cerebro.addstrategy(strategy, **params)

def setup_cerebro(strategy, args, data, StartCash=1000, is_optimization=False):
    cerebro = bt.Cerebro(maxcpus=10, optdatas=True, optreturn=False, preload=True, runonce=True)
    if not is_optimization:
        bt.observers.BuySell = MyBuySell
        cerebro.addobserver(bt.observers.DrawDown)
    add_strategy_params_to_cerebro(cerebro, strategy, args, is_optimization)
    cerebro.broker.setcash(StartCash)
    cerebro.adddata(data)
    cerebro.addanalyzer(GLP, _name="glp")
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="ta")
    cerebro.addanalyzer(bt.analyzers.SQN, _name="sqn")
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name="drawdown")
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharperatio')
    cerebro.addanalyzer(bt.analyzers.Returns)
    cerebro.addanalyzer(bt.analyzers.TimeReturn, _name='timereturn', timeframe=bt.TimeFrame.Days)
    cerebro.addanalyzer(AVGDD, _name="avgdd")
    cerebro.getbroker().setcommission(commission=0.001, name=COIN_TARGET)
    return cerebro

def rundata(strategy, args, data, plot, info, optType=OptimizationType.RETURN):
    cerebro = setup_cerebro(strategy, args, data)
    results = cerebro.run()
    strat = results[0]
    
    val = calculate_optimization_value(strat, optType)
            
    print(",".join(str(x) for x in args) + ":::" + str(val))
    if info:
        analysis = StrategyAnalysis(strat, data, 1000)
        analysis.print_summary()
    if plot: 
        cerebro.plot(style='candlestick')
    return float(val)

#OptType =?= 'Return' , 'WinRate' ,'SQN' , 'Sharpe'
def optimizeStrat(strat,args,scan_range,data,startindex=0,optType=OptimizationType.RETURN):
    old_args = args.copy()
    res = OptRunData(strat,args,scan_range,data,startindex,optType)
    
    # Force garbage collection after optimization run
    gc.collect()

    if(old_args == res):
        return res

    else:
        return optimizeStrat(strat,res,scan_range,data,startindex,optType)

def addParamstoOptCerebro(cerebro,strategy,args):
    param_dict = {}
    for i, value in enumerate(args):
        param_dict[f'p{i}'] = value
    cerebro.optstrategy(strategy, **param_dict)

#OptType =?= 'Return' , 'WinRate' ,'SQN' , 'Sharpe'
def OptRunData(strategy,default_args,my_scan_range,data,startindex=0,optType=OptimizationType.RETURN):
    print(f"Optimizing {optType}...")
    print(f"Starting from index: {startindex}, val: {default_args[startindex]}")
    print(default_args)

    stepdiv = 1200
    print("searching... %" + str(100*my_scan_range/stepdiv))

    tstart = time.time()
    val_list = []
    args = default_args.copy()
    for i in range(startindex,len(default_args)):
        if(default_args[i] == -1):
            continue
        cerebro = bt.Cerebro(optreturn=False,maxcpus=6)

        scan_range = min(my_scan_range,(default_args[i]+1)*(default_args[i]+1))
        step    = int(max(abs(default_args[i]/stepdiv), 1))
        diff    = step * scan_range
        heigh   = default_args[i]+diff
        low     = default_args[i]-diff
        low     = max(1,low)
        heigh   = max(1,heigh)
        args[i] =(range(int(low), int(heigh), int(step)))

        addParamstoOptCerebro(cerebro,strategy,args)

        StartCash = 1000
        cerebro.broker.setcash(StartCash)
        cerebro.adddata(data)
        cerebro.addanalyzer(GLP, _name="glp")
        cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="ta")
        cerebro.addanalyzer(bt.analyzers.SQN, _name="sqn")
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name="drawdown")
        cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharperatio')
        cerebro.addanalyzer(bt.analyzers.Returns)
        cerebro.addanalyzer(AVGDD, _name="avgdd")

        #cerebro.addsizer(PercentSizer,percents=99)
        broker = cerebro.getbroker()
        broker.setcommission(commission=0.001,name=COIN_TARGET)
        stratruns = cerebro.run()
        
        # Force garbage collection after each cerebro run
        gc.collect()

    
        for stratrun in stratruns:
            pars = []
            for strat in stratrun:
                for i in range(min(len(args), 27)):  # Up to p26 (27 parameters)
                    param_name = f'p{i}'
                    pars.append(getattr(strat.params, param_name))
                val = 0
                if(optType==OptimizationType.RETURN):
                    val = strat.broker.getvalue()

                if(optType==OptimizationType.ADO):
                   analyzer = strat.analyzers.ta.get_analysis()
                   total_closed = analyzer.total.closed
                   total_won    = analyzer.won.total
                   winrate      = (total_won / total_closed)
                   sqn          = strat.analyzers.sqn.get_analysis()['sqn']
                   sharperatio  = strat.analyzers.sharperatio.get_analysis()['sharperatio']
                   ret          = float(sqrt(strat.broker.getvalue()))
                   ddown        = strat.analyzers.drawdown.get_analysis().max.drawdown
                   won_pnl_avg  = round(analyzer.won.pnl.total,2)
                   lost_pnl_avg = round(analyzer.lost.pnl.total,2)
                   pnlRet       = won_pnl_avg /-(lost_pnl_avg+0.0001)
                   glp          = strat.analyzers.glp.get_analysis().glp
                   calmar       = strat.analyzers.returns.get_analysis()['rnorm']
                   avgdd        = strat.analyzers.avgdd.get_analysis().avgdd

                   avg_win = analyzer.won.pnl.average
                   avg_loss = analyzer.lost.pnl.average
        
                   expectancy = (winrate * avg_win) + ((1 - winrate) * avg_loss)

                   val          = ret * calmar * expectancy * sqn * sharperatio * pnlRet * glp / (ddown*ddown*avgdd)
       
                
                if(optType==OptimizationType.ALL):
                    analyzer = strat.analyzers.ta.get_analysis()
                    total_closed = analyzer.total.closed
                    total_won    = analyzer.won.total
                    winrate      = (total_won / total_closed)
                    sqn          = strat.analyzers.sqn.get_analysis()['sqn']
                    sharperatio  = strat.analyzers.sharperatio.get_analysis()['sharperatio']
                    ret          = float(sqrt(strat.broker.getvalue()))
                    ddown        = strat.analyzers.drawdown.get_analysis().max.drawdown
                    won_pnl_avg  = round(analyzer.won.pnl.average,2)
                    lost_pnl_avg = round(analyzer.lost.pnl.average,2)
                    #pnlRet       = won_pnl_avg /-(lost_pnl_avg+0.001)
                    glp          = strat.analyzers.glp.get_analysis().glp
                    val          = glp * ret * sqn / (ddown*ddown)


                print(str(pars) +" ::: "+ str(val))
                val_list.append([val,pars])
                res = max(val_list, key=itemgetter(0))
                args[i] = res[1][i]
        
        # Force garbage collection after each parameter optimization
        gc.collect()
        # print out the result
        #print("Optimizing "+optType+" ..." +str(int(((i+1)/(len(default_args)-startindex))*100)) +"/100")
    tend = time.time()
    print('Time used:', str(tend - tstart))
    print(args)
    return args

def initData(traindays, testdays, timeframe, target=COIN_TARGET, refresh=False):
    today = datetime.date.today() - datetime.timedelta(days=testdays)
    fromdate = today - datetime.timedelta(days=traindays)
    todate = today + datetime.timedelta(days=1)
    path = gd.get_Date_Data(fromdate, todate, timeframe, target, refresh)
    data = bt.feeds.GenericCSVData(name=target, dataname=path, timeframe=bt.TimeFrame.Minutes, 
                                 fromdate=fromdate, todate=todate)
    print(f"BackTesting Data of: {path}")
    return data

class MyBuySell(bt.observers.BuySell):
    plotlines = dict(
    buy=dict(marker='^', markersize=8.0),
    sell=dict(marker='v', markersize=8.0)
)


def walkforward(strategy, initial_params, data, train_days=365, test_days=90, step_days=30, opt_type=OptimizationType.ADO):
    """
    Walk Forward optimizasyonu yapan fonksiyon
    
    Args:
        strategy: Strateji sınıfı
        initial_params: Başlangıç parametreleri
        data: Referans veri seti (sadece tarih aralığı için kullanılacak)
        train_days: Eğitim periyodu (gün)
        test_days: Test periyodu (gün)
        step_days: Adım boyutu (gün)
        opt_type: Optimizasyon tipi
    """
    print(f"\nWalk Forward Optimizasyonu Başlıyor...")
    print(f"Eğitim Periyodu: {train_days} gün")
    print(f"Test Periyodu: {test_days} gün")
    print(f"Adım Boyutu: {step_days} gün")
    
    # Sonuçları saklamak için liste
    results = []
    best_params = initial_params.copy()
    
    try:
        # Her adım için
        current_delay = 0
        while current_delay < train_days + test_days:  # Toplam periyot boyunca
            try:
                print(f"\nDelay: {current_delay} gün")
                print(f"Data Boyutu: {test_days} gün")
                
                # Her periyot için yeni data indir
                period_data = initData(
                    traindays=test_days,
                    testdays=current_delay,
                    timeframe=Client.KLINE_INTERVAL_15MINUTE,
                    target="AVAX",
                    refresh=False
                )
                
                # Optimizasyon yap
                print("Optimizasyon yapılıyor...")
                optimized_params = optimizeStrat(strategy, best_params, 6, period_data, 0, opt_type)
                
                # Test yap
                print("Test yapılıyor...")
                test_value = rundata(strategy, optimized_params, period_data, False, False, opt_type)
                
                # Sonuçları kaydet
                results.append({
                    'delay': current_delay,
                    'params': optimized_params,
                    'value': test_value
                })
                
                print(f"Test Sonucu: {test_value:.4f}")
                
                # Bir sonraki adıma geç
                current_delay += step_days
                
                # En iyi parametreleri güncelle
                if test_value > results[-2]['value'] if len(results) > 1 else True:
                    best_params = optimized_params.copy()
                    
            except Exception as e:
                print(f"Periyot işlenirken hata oluştu: {e}")
                # Bir sonraki adıma geç
                current_delay += step_days
                continue
        
        if not results:
            print("Hiç sonuç elde edilemedi!")
            return initial_params, []
        
        # Sonuçları analiz et ve raporla
        print("\nWalk Forward Sonuçları:")
        print("=" * 50)
        
        # Ortalama performans
        avg_value = sum(r['value'] for r in results) / len(results)
        print(f"Ortalama Performans: {avg_value:.4f}")
        
        # En iyi ve en kötü performans
        best_result = max(results, key=lambda x: x['value'])
        worst_result = min(results, key=lambda x: x['value'])
        print(f"En İyi Performans: {best_result['value']:.4f} (Delay: {best_result['delay']} gün)")
        print(f"En Kötü Performans: {worst_result['value']:.4f} (Delay: {worst_result['delay']} gün)")
        
        # Performans standart sapması
        std_dev = sqrt(sum((r['value'] - avg_value) ** 2 for r in results) / len(results))
        print(f"Performans Standart Sapması: {std_dev:.4f}")
        
        return best_params, results
        
    except Exception as e:
        print(f"Walk Forward optimizasyonu sırasında hata oluştu: {e}")
        return initial_params, []

def monte_carlo_simulation(strategy, params, data, n_runs=100, train_days=365, test_days=90, opt_type=OptimizationType.ADO):
    """
    Comprehensive Monte Carlo simulation for trading strategy analysis
    
    Args:
        strategy: Strategy class
        params: Strategy parameters
        data: Data feed
        n_runs: Number of simulations
        train_days: Training period (days)
        test_days: Test period (days)
        opt_type: Optimization type
    """
    print(f"\nStarting Monte Carlo Simulation...")
    print(f"Number of Simulations: {n_runs}")
    
    results = []
    equity_curves = []
    best_params = params.copy()
    
    try:
        # Get original trades from initial run
        cerebro = setup_cerebro(strategy, params, data)
        initial_results = cerebro.run()
        initial_strat = initial_results[0]
        
        # Extract trade data
        original_trades = []
        trade_analysis = initial_strat.analyzers.ta.get_analysis()
        
        # Process winning trades
        if hasattr(trade_analysis, 'won') and hasattr(trade_analysis.won, 'pnl'):
            won_total = trade_analysis.won.total
            won_pnl_avg = trade_analysis.won.pnl.average
            for _ in range(won_total):
                original_trades.append({
                    'pnl': won_pnl_avg,
                    'is_win': True
                })
        
        # Process losing trades
        if hasattr(trade_analysis, 'lost') and hasattr(trade_analysis.lost, 'pnl'):
            lost_total = trade_analysis.lost.total
            lost_pnl_avg = trade_analysis.lost.pnl.average
            for _ in range(lost_total):
                original_trades.append({
                    'pnl': lost_pnl_avg,
                    'is_win': False
                })
        
        if not original_trades:
            print("Warning: No trades found in initial run!")
            return params, []
            
        print(f"Found {len(original_trades)} original trades")
        print(f"Initial Win Rate: {sum(1 for t in original_trades if t['is_win'])/len(original_trades):.2%}")
        
        # Run simulations
        for i in range(n_runs):
            try:
                print(f"\nSimulation {i+1}/{n_runs}")
                
                # Randomly shuffle trades
                randomized_trades = original_trades.copy()
                random.shuffle(randomized_trades)
                
                # Randomly skip some trades (10-20%)
                skip_probability = random.uniform(0.1, 0.2)
                randomized_trades = [t for t in randomized_trades if random.random() > skip_probability]
                
                # Apply small random changes to PnL
                for trade in randomized_trades:
                    pnl_change = random.uniform(-0.001, 0.001)  # ±0.1% change
                    trade['pnl'] *= (1 + pnl_change)
                
                # Calculate equity curve
                initial_capital = 1000.0
                current_capital = initial_capital
                equity_curve = [initial_capital]
                
                for trade in randomized_trades:
                    current_capital += trade['pnl']
                    equity_curve.append(current_capital)
                
                # Calculate performance metrics
                max_drawdown = 0
                peak = equity_curve[0]
                for value in equity_curve:
                    if value > peak:
                        peak = value
                    drawdown = (peak - value) / peak
                    max_drawdown = max(max_drawdown, drawdown)
                
                # Calculate risk of ruin (probability of dropping below 50% of initial capital)
                risk_of_ruin = sum(1 for x in equity_curve if x < initial_capital * 0.5) / len(equity_curve)
                
                # Store results
                results.append({
                    'run': i + 1,
                    'final_capital': current_capital,
                    'max_drawdown': max_drawdown,
                    'risk_of_ruin': risk_of_ruin,
                    'total_trades': len(randomized_trades),
                    'win_rate': sum(1 for t in randomized_trades if t['is_win']) / len(randomized_trades) if randomized_trades else 0
                })
                
                equity_curves.append(equity_curve)
                
                print(f"Final Capital: ${current_capital:.2f}")
                print(f"Max Drawdown: {max_drawdown:.2%}")
                print(f"Risk of Ruin: {risk_of_ruin:.2%}")
                print(f"Total Trades: {len(randomized_trades)}")
                print(f"Win Rate: {results[-1]['win_rate']:.2%}")
                    
            except Exception as e:
                print(f"Error during simulation: {e}")
                continue
        
        if not results:
            print("No results obtained!")
            return params, []
        
        # Analyze and report results
        print("\nMonte Carlo Simulation Results:")
        print("=" * 50)
        
        # Calculate statistics
        final_capitals = [r['final_capital'] for r in results]
        max_drawdowns = [r['max_drawdown'] for r in results]
        risk_of_ruins = [r['risk_of_ruin'] for r in results]
        win_rates = [r['win_rate'] for r in results]
        
        # Calculate mean and standard deviation
        avg_capital = sum(final_capitals) / len(final_capitals)
        std_capital = sqrt(sum((x - avg_capital) ** 2 for x in final_capitals) / len(final_capitals))
        
        # Print results
        print(f"Average Final Capital: ${avg_capital:.2f}")
        print(f"Capital Standard Deviation: ${std_capital:.2f}")
        print(f"Highest Capital: ${max(final_capitals):.2f}")
        print(f"Lowest Capital: ${min(final_capitals):.2f}")
        print(f"Average Max Drawdown: {sum(max_drawdowns)/len(max_drawdowns):.2%}")
        print(f"Average Risk of Ruin: {sum(risk_of_ruins)/len(risk_of_ruins):.2%}")
        print(f"Average Win Rate: {sum(win_rates)/len(win_rates):.2%}")
        
        # Calculate confidence interval
        confidence_interval = 1.96 * (std_capital / sqrt(len(final_capitals)))
        print(f"95% Confidence Interval: [${avg_capital - confidence_interval:.2f}, ${avg_capital + confidence_interval:.2f}]")
        
        return params, results
        
    except Exception as e:
        print(f"Monte Carlo simulation error: {e}")
        return params, []
    
if __name__ == '__main__':
    # days 80 311 580 1050 1600
    Delay, Dayz = 0, 1800
    data = initData(Dayz, Delay, Client.KLINE_INTERVAL_15MINUTE, "AVAX", False)
    #trainer.train(data,[257,992,147,24,569,751,1409,16,566,337,125,144,199,1261,532,290,130,72,77,36,69])
    #trainer.train_test(data,[257,992,147,24,569,751,1409,16,566,337,125,144,199,1261,532,290,130,72,77,36,69])
    #trainer.test(data,[257,992,147,24,569,751,1409,16,566,337,125,144,199,1261,532,290,130,72,77,36,69])
    #rundata(AIStratDis, [257,992,147,24,569,751,1409,16,566,337,125,144,199,1261,532,290,130,72,77,36,69], data, True, True, OptimizationType.RETURN)  
    #trainer.train_multi_agent([257,992,147,24,569,751,1409,16,566,337,125,144,199,1261,532,290,130,72,77,36,69])

    #rundata(MyStratV4, [255,992,147,25,279,751,1398,16,566,337,125,144,200,1261,532,276,130,72,77,36,69], data, False, True, OptimizationType.ADO)
    #rundata(MyStratV4, [257,992,147,24,569,751,1409,16,566,337,125,144,199,1261,532,290,130,72,77,36,69], data, False, True, OptimizationType.ADO)

    #rundata(MyStratV4, optimizeStrat(MyStratV4, [257,992,147,24,569,751,1409,16,566,337,125,144,199,1261,532,290,130,72,77,36,69], 6, data,0, OptimizationType.ADO), data, True, True, OptimizationType.ADO)
    
    #global_agent.eval()
    #rundata(MyStratAI, [257,992,147,24,569,751,1409,16,566,337,125,144,199,1261,532,290,130,72,77,36,69], data, True, True, OptimizationType.RETURN)  

    ### OLD TIMES BRO ###
    # Example of running MyStratV1 with default parameters
    #rundata(MyStratV1, [3,246,3,720,161,76,132,395,1622,25,541,350,116,167,324,1093,609,259,83,-1,-1], data, True, True, OptimizationType.ADO)

    # Example of running MyStratV2 with default parameters
    # rundata(MyStratV2, [3,246,3,720,161,76,132,395,1622,25,541,350,116,167,324,1093,609,259,83,-1,-1], data, True, True, OptimizationType.AI)
    
    # Example of running MyStratV2 with ALL optimization type
    #rundata(MyStratV2, [583,1991,246,720,161,76,132,395,1622,25,541,350,116,167,324,1093,609,259,83,50,200], data, True, True, OptimizationType.ADO)
    #rundata(MyStratV2, optimizeStrat(MyStratV2, [100,200,246,720,161,76,132,395,1622,25,541,350,116,167,324,1093,609,259,83,50,200], 10, data, 0, OptimizationType.ALL), data, True, True, OptimizationType.ADO)

    #rundata(MyStratV2, [20,50,246,720,161,76,132,395,1622,25,541,350,116,167,324,1093,609,259,83,50,200], data, True, True, OptimizationType.ADO)

    #rundata(MyStratV2, [246,720,161,76,132,395,1622,25,541,350,116,167,324,1093,609,259,83,1,5,50,200], data, True, True, OptimizationType.ADO)
    
     
    #rundata(MyStratV2, optimizeStrat(MyStratV2, [243,993,136,59,264,454,1414,18,555,352,120,164,191,1145,626,296,159,101,57,53,58], 10, data,17, OptimizationType.ADO), data, True, True, OptimizationType.ADO)
    #rundata(MyStratV2, optimizeStrat(MyStratV2, [243,993,136,59,264,454,1414,18,555,352,120,164,191,1145,626,296,159,41,57,53,58], 10, data,17, OptimizationType.ADO), data, True, True, OptimizationType.ADO)
    #rundata(MyStratV2, optimizeStrat(MyStratV2, [243,973,149,23,633,735,1428,16,565,354,123,150,201,1066,623,238,132,80,125,36,69], 6, data,0, OptimizationType.ADO), data, True, True, OptimizationType.ADO)
    #rundata(MyStratV2,  [243,973,149,23,633,735,1428,16,565,354,123,150,201,1066,623,238,132,80,125,36,69], data, True, True, OptimizationType.ADO)
   
    #rundata(MyStratV3, optimizeStrat(MyStratV3, [260,971,149,23,633,743,1405,16,568,337,125,138,200,823,532,290,156,72,115,36,69], 3, data,0, OptimizationType.ADO), data, True, True, OptimizationType.ADO)
    #rundata(MyStratV3,  [256, 971, 149, 23, 633, 743, 1405, 16, 568, 337, 125, 138, 201, 811, 532, 290, 159, 72, 121, 36, 69], data, True, True, OptimizationType.ADO)
    #rundata(MyStratV4, optimizeStrat(MyStratV4, [255,993,147,25,569,751,1398,16,568,337,125,138,200,833,532,250,159,72,77,36,69], 6, data,0, OptimizationType.ADO), data, True, True, OptimizationType.ADO)
    #rundata(MyStratV4, optimizeStrat(MyStratV4, [257, 971, 149, 23, 633, 743, 1405, 16, 568, 337, 125, 138, 200, 827, 532, 290, 156, 72, 115, 36, 69], 6, data,0, OptimizationType.ADO), data, True, True, OptimizationType.ADO)
    
    #rundata(MyStratV3,  [260, 971, 149, 23, 633, 743, 1405, 16, 568, 337, 125, 138, 200, 823, 532, 290, 156, 72, 115, 36, 69], data, False, True, OptimizationType.ADO)
    #rundata(MyStratV4,  [256, 971, 149, 23, 633, 743, 1405, 16, 568, 337, 125, 138, 201, 811, 532, 290, 159, 72, 121, 36, 69], data, False, True, OptimizationType.ADO)
    #rundata(MyStratV3,  [257,971,149,23,633,743,1405,16,568,337,125,138,200,827,532,290,156,72,115,36,69], data, False, True, OptimizationType.ADO)
    #rundata(MyStratV4,  [257,971,149,23,633,743,1405,16,568,337,125,138,200,827,532,290,156,72,115,36,69], data, False, True, OptimizationType.ADO)
    #rundata(MyStratV4,  [256,971,149,23,633,743,1405,16,568,337,125,138,201,811,532,290,159,72,121,36,69], data, False, True, OptimizationType.ADO)
    #rundata(MyStratV4,  [257, 971, 149, 23, 633, 743, 1405, 16, 568, 337, 125, 138, 200, 827, 532, 290, 156, 72, 115, 36, 69], data, False, True, OptimizationType.ADO)
    #rundata(MyStratV4,  [255,993,147,25,569,751,1398,16,568,337,125,138,200,833,532,250,159,72,77,36,69], data, False, True, OptimizationType.ADO)
    #rundata(MyStratV4,  [257,992,147,24,569,754,1398,16,568,336,125,138,199,833,529,248,159,72,77,36,69], data, False, True, OptimizationType.ADO)
    
    #rundata(MyStratV4, [257,992,147,24,569,751,1409,16,566,337,125,144,199,1261,532,290,130,72,77,36,69], data, False, True, OptimizationType.ADO)
    #rundata(MyStratV4, optimizeStrat(MyStratV4, [255,992,147,25,569,751,1398,16,566,337,125,144,200,1261,532,276,130,72,77,36,69], 6, data,0, OptimizationType.ADO), data, True, True, OptimizationType.ADO)
  

    #rundata(MyStratV5, [255,992,147,25,279,751,1398,16,566,337,125,144,200,1261,532,276,130,72,77,36,69], data, False, True, OptimizationType.RETURN)    
    #rundata(MyStratV5, [255, 993, 150, 25, 279, 769, 1398, 16, 566, 337, 125, 144, 200, 1245, 532, 269, 14, 72, 125, 36, 69, 137, 59, 31], data, True, True, OptimizationType.ADO)    
    #rundata(MyStratV5, optimizeStrat(MyStratV5, [255, 993, 150, 25, 279, 769, 1398, 16, 566, 337, 125, 144, 200, 1245, 532, 269, 14, 72, 125, 36, 69, 137, 59, 31], 2, data,0, OptimizationType.ADO), data, True, True, OptimizationType.ADO)

   
    #rundata(MyStratV4, [255,992,147,25,279,751,1398,16,566,337,125,144,200,1261,532,276,130,72,77,36,69], data, False, True, OptimizationType.ADO)
    #rundata(MyStratV4, [257,992,147,24,569,751,1409,16,566,337,125,144,199,1261,532,290,130,72,77,36,69], data, False, True, OptimizationType.ADO)


    #rundata(MyStratV4, [255,992,147,25,34,751,1398,16,566,337,125,144,200,1261,532,276,130,72,77,36,69], data, False, False, OptimizationType.ADO)
    #rundata(MyStratV4, [255,992,147,25,35,751,1398,16,566,337,125,144,200,1261,532,276,130,72,77,36,69], data, False, False, OptimizationType.ADO)
    rundata(MyStratV4, optimizeStrat(MyStratV4, [255,992,147,25,39,751,1398,16,566,337,125,144,200,1261,532,276,130,72,77,36,69], 6, data,0, OptimizationType.ADO), data, True, True, OptimizationType.ADO)






    ## PPO
    #rundata(AIDeployStrat, optimizeStrat(AIDeployStrat, [255,993,147,25,569,751,1398,16,568,337,125,138,200,833,532,250,159,72,77,36,69], 2, data,0, OptimizationType.ADO), data, True, True, OptimizationType.ADO)
    #rundata(AIDeployStrat, optimizeStrat(AIDeployStrat, [255,992,147,25,279,751,1398,16,566,337,125,144,200,1261,532,276,130,72,77,36,69], 6, data,0, OptimizationType.ADO), data, True, True, OptimizationType.ADO)
    #rundata(AIDeployStrat, [255,992,147,25,279,751,1398,16,566,337,125,144,200,1261,532,276,15,72,77,36,69], data, False, True, OptimizationType.RETURN) 
    #rundata(AIDeployStrat, optimizeStrat(AIDeployStrat, [255,992,147,25,279,751,1398,16,566,337,125,144,200,1261,532,276,25,72,77,36,69], 12, data,16, OptimizationType.ADO), data, True, True, OptimizationType.ADO)
    #rundata(AIDeployStrat, optimizeStrat(AIDeployStrat, [255,992,147,25,279,751,1398,16,566,337,125,144,200,1261,532,276,15,72,77,36,69], 12, data,16, OptimizationType.ADO), data, True, True, OptimizationType.ADO)
    

    #trainer.test_labels(data, [255,992,147,25,279,751,1398,16,566,337,125,144,200,1261,532,276,130,72,77,36,69])
    #trainer.export_models() 
    #rundata(AIStratDis, [255,992,147,25,279,751,1398,16,566,337,125,144,200,1261,532,276,130,72,77,36,69], data, True, True, OptimizationType.RETURN)  
    #rundata(AIStratDis, [257,992,147,24,569,751,1409,16,566,337,125,144,199,1261,532,290,130,72,77,36,69], data, True, True, OptimizationType.RETURN)  

