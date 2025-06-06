from optimization import calculate_sortino, calculate_calmar, calculate_kelly, calculate_consistency
from optimization import calculate_recovery, calculate_expectancy, calculate_omega, calculate_risk_adjusted_return
from optimization import calculate_profit_factor
from datetime import datetime

class StrategyAnalysis:
    def __init__(self, strat, data, start_cash):
        self.strat = strat
        self.data = data
        self.start_cash = start_cash
        
        self.ta = strat.analyzers.ta.get_analysis()
        self.sqn = strat.analyzers.sqn.get_analysis()
        self.drawdown = strat.analyzers.drawdown.get_analysis()
        self.avgdd = strat.analyzers.avgdd.get_analysis().avgdd
        self.sharpe = strat.analyzers.sharperatio.get_analysis()
        self.returns = strat.analyzers.returns.get_analysis()
        self.glp = strat.analyzers.glp.get_analysis()
        
        self.sortino = calculate_sortino(strat)
        self.calmar = calculate_calmar(strat)
        self.kelly = calculate_kelly(strat)
        self.consistency = calculate_consistency(strat)
        self.recovery = calculate_recovery(strat)
        self.expectancy = calculate_expectancy(strat)
        self.omega = calculate_omega(strat)
        self.risk_adjusted_return = calculate_risk_adjusted_return(strat)
        self.profit_factor = calculate_profit_factor(strat)
        
    @property
    def market_ratio(self): 
        return self.data.close[-1] / self.data.close[0]
        
    @property
    def bot_ratio(self): 
        return self.strat.broker.getvalue() / self.start_cash
        
    @property
    def bot_market_ratio(self): 
        return self.bot_ratio / self.market_ratio
        
    @property
    def trade_per_candle(self): 
        return self.ta.total.closed / len(self.data.close)
        
    def print_summary(self):
        print(f"\n=============| {self.strat.__class__.__name__} |==============")
        print(f"Net Profit: ${self.ta.pnl.net.total}")
        print(f"Total Profit: ${self.ta.pnl.gross.total}")
        print(f"Total Loss: ${abs(self.ta.lost.pnl.total)}")
        print(f"Bot Ratio: {self.bot_ratio}")
        print(f"Bot/Market: {self.bot_market_ratio}")
        print(f"CAGR: {self.returns['rnorm']}")
        print(f"Total Trades: {self.ta.total.closed}")
        print(f"Win Rate: {self.ta.won.total / self.ta.total.closed}")
        print(f"Win Streak: {self.ta.streak.won.longest}")
        print(f"Lose Streak: {self.ta.streak.lost.longest}")
        print(f"Avg Profit: ${self.ta.won.pnl.average}")
        print(f"Avg Loss: ${self.ta.lost.pnl.average}")
        print(f"Risk/Reward: {self.ta.won.pnl.average/abs(self.ta.lost.pnl.average)}")
        print(f"Profit Factor: {self.profit_factor}")
        print(f"Avg Trade Duration: {self.ta.len.average} bars")
        print(f"TradePerCandle: {self.trade_per_candle}")
        print(f"Max DrawDown: {self.drawdown.max.drawdown}%")
        print(f"Avg DrawDown: {self.avgdd}%")
        print(f"Recovery Factor: {self.recovery}")
        print(f"Kelly Criterion: {self.kelly}")
        print(f"Sharpe Ratio: {self.sharpe.get('sharperatio', 0)}")
        print(f"Sortino Ratio: {self.sortino}")
        print(f"Calmar Ratio: {self.calmar}")
        print(f"Omega Ratio: {self.omega}")
        print(f"Risk-Adj Return: {self.risk_adjusted_return}")
        print(f"SQN: {self.sqn.sqn}")
        print(f"GLP: {self.glp.glp}")
        print(f"GPER: {self.glp.gper}")
        print(f"LPER: {self.glp.lper}")
        print(f"Consistency: {self.consistency}")
        print(f"Expectancy: {self.expectancy}")