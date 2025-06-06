from enum import Enum
from math import sqrt, log
import numpy as np
from backtrader.utils import AutoOrderedDict

class OptimizationType(Enum):
    ALL = 'All'
    RETURN = 'Return'
    ADO = 'Ado'
    AI = 'AI'

def safe_division(numerator, denominator, default=0.0):
    return default if denominator == 0 or denominator is None else numerator / denominator

def extract_returns(strat):
    try:
        if hasattr(strat.analyzers, 'returns'):
            return strat.analyzers.returns.get_analysis().get('returns', [])
        
        equity_curve = [strat.broker.get_value() for _ in range(len(strat))]
        returns = [(equity_curve[i] / equity_curve[i-1]) - 1 for i in range(1, len(equity_curve))]
        return returns
    except Exception as e:
        print(f"Getiri hesaplama hatası: {e}")
        return []

def calculate_return(strat): 
    return 100

def calculate_ado(strat):
        analyzer = strat.analyzers.ta.get_analysis()
        total_closed = analyzer.total.closed
        if total_closed < 10 :
            return -1
        
        total_won = analyzer.won.total
        winrate = (total_won / total_closed)
        lossrate = 1 - winrate
        avg_win = analyzer.won.pnl.average
        avg_loss = abs(analyzer.lost.pnl.average)
        expectancy = (winrate * avg_win) - (lossrate * avg_loss)
        
        sqn = strat.analyzers.sqn.get_analysis()['sqn']
        sharperatio = strat.analyzers.sharperatio.get_analysis()['sharperatio']
        ret = log(1 + strat.broker.getvalue())
        ddown        = strat.analyzers.drawdown.get_analysis().max.drawdown
        won_pnl_avg  = round(analyzer.won.pnl.total,2)
        lost_pnl_avg = round(analyzer.lost.pnl.total,2)
        glp          = strat.analyzers.glp.get_analysis().glp
        pnlRet       = won_pnl_avg/-(lost_pnl_avg+0.0001)
        calmar       = strat.analyzers.returns.get_analysis()['rnorm']
        avgdd        = strat.analyzers.avgdd.get_analysis().avgdd

        val = ret * sqn  * sharperatio * pnlRet * glp * (1 + expectancy) / (ddown*ddown*avgdd)
        return val
    

def calculate_all(strat):
    try:
        # Get analyzer results
        analyzer = strat.analyzers.ta.get_analysis()
        total_closed = analyzer.total.closed

        # Return early if no trades
        if total_closed < 10 :
            return -1
        
        total_won = analyzer.won.total
        winrate = (total_won / total_closed)
        sqn = strat.analyzers.sqn.get_analysis()['sqn']
        sharperatio = strat.analyzers.sharperatio.get_analysis()['sharperatio']
        ret = log(1 + strat.broker.getvalue())
        ddown        = strat.analyzers.drawdown.get_analysis().max.drawdown
        avgdd        = strat.analyzers.drawdown.get_analysis().avg.drawdown
        val          = ret * sqn * winrate * sharperatio * total_won / (ddown*avgdd)
        return val
        
    except Exception as e:
        print(f"ALL hesaplama hatası: {e}")
        return 0.0

def calculate_ai(strat):
    try:
        analyzer = strat.analyzers.ta.get_analysis()
        total_closed = getattr(analyzer, 'total', AutoOrderedDict()).closed if hasattr(analyzer, 'total') else 0
        
        if total_closed < 10:
            return 0.0
            
        total_won = getattr(analyzer.won, 'total', 0) if hasattr(analyzer, 'won') else 0
        winrate = safe_division(total_won, total_closed, 0)
        
        returns = strat.analyzers.returns.get_analysis()
        ret = log(1 + abs(getattr(returns, 'rtot', 0) or 0) + 0.0001)
        
        drawdown_analysis = strat.analyzers.drawdown.get_analysis()
        ddown = max(0.0001, getattr(drawdown_analysis.max, 'drawdown', 0) or 0.0001)
        
        won_pnl = getattr(analyzer.won.pnl, 'total', 0) if hasattr(analyzer, 'won') and hasattr(analyzer.won, 'pnl') else 0
        lost_pnl = getattr(analyzer.lost.pnl, 'total', 0) if hasattr(analyzer, 'lost') and hasattr(analyzer.lost, 'pnl') else 0
        profit_factor = safe_division(abs(won_pnl), abs(lost_pnl) + 0.0001, 0)
        
        risk_adjusted_return = safe_division(ret, ddown, 0)
        
        returns_list = extract_returns(strat)
        consistency = 1.0 / (1.0 + np.std(returns_list)) if returns_list and len(returns_list) > 1 else 0.5
            
        score = (
            0.30 * ret +
            0.20 * risk_adjusted_return +
            0.15 * winrate +
            0.15 * (1.0 / (1.0 + ddown)) +
            0.10 * consistency +
            0.10 * min(profit_factor, 5.0) / 5.0
        )
        
        trade_bonus = min(total_closed / 100, 1.0)
        
        return score * (1.0 + 0.2 * trade_bonus)
        
    except Exception as e:
        print(f"AI optimization calculation error: {e}")
        return 0.0

def calculate_optimization_value(strat, opt_type):
    if(opt_type == OptimizationType.RETURN):
        return calculate_return(strat)
    elif(opt_type == OptimizationType.ADO):
        return calculate_ado(strat)
    elif(opt_type == OptimizationType.AI):
        return calculate_ai(strat)  
    elif(opt_type == OptimizationType.ALL):
        return calculate_all(strat)
    else:
        return 0

def calculate_sortino(strat):
    try:
        analyzer = strat.analyzers.ta.get_analysis()
        total_closed = analyzer.total.closed
        
        if total_closed < 10:
            return 0.0
            
        returns = strat.analyzers.returns.get_analysis()
        annual_return = returns.get('rnorm', 0)
        
        # Get daily returns for downside deviation calculation
        daily_returns = []
        for i in range(1, len(strat)):
            daily_return = (strat.broker.get_value(i) / strat.broker.get_value(i-1)) - 1
            daily_returns.append(daily_return)
        
        # Calculate downside deviation (standard deviation of negative returns)
        negative_returns = [r for r in daily_returns if r < 0]
        if not negative_returns:
            return 0.0
            
        downside_deviation = np.std(negative_returns)
        if downside_deviation == 0:
            return 0.0
            
        # Annualize the downside deviation
        annual_downside_deviation = downside_deviation * np.sqrt(252)  # Assuming daily data
        
        return annual_return / annual_downside_deviation if annual_downside_deviation != 0 else 0.0
    except Exception as e:
        print(f"Sortino calculation error: {e}")
        return 0.0

def calculate_calmar(strat):
    try:
        analyzer = strat.analyzers.ta.get_analysis()
        total_closed = analyzer.total.closed
        
        if total_closed < 10:
            return 0.0
            
        returns = strat.analyzers.returns.get_analysis()
        drawdown = strat.analyzers.drawdown.get_analysis()
        
        annual_return = returns.get('rnorm', 0)
        max_drawdown = drawdown.max.drawdown / 100.0  # Convert from percentage to decimal
        
        if max_drawdown == 0:
            return 0.0
            
        return annual_return / max_drawdown
    except Exception as e:
        print(f"Calmar calculation error: {e}")
        return 0.0

def calculate_kelly(strat):
    try:
        analyzer = strat.analyzers.ta.get_analysis()
        total_closed = analyzer.total.closed
        
        if total_closed < 10:
            return 0.0
            
        total_won = analyzer.won.total
        win_rate = total_won / total_closed
        
        avg_win = analyzer.won.pnl.average
        avg_loss = abs(analyzer.lost.pnl.average)
        
        if avg_loss == 0:
            return 0.0
            
        win_loss_ratio = avg_win / avg_loss
        
        return win_rate - ((1 - win_rate) / win_loss_ratio)
    except Exception as e:
        print(f"Kelly calculation error: {e}")
        return 0.0

def calculate_consistency(strat):
    try:
        analyzer = strat.analyzers.ta.get_analysis()
        total_closed = analyzer.total.closed
        
        if total_closed < 10:
            return 0.5
            
        # Get daily returns
        daily_returns = []
        for i in range(1, len(strat)):
            daily_return = (strat.broker.get_value(i) / strat.broker.get_value(i-1)) - 1
            daily_returns.append(daily_return)
        
        if not daily_returns or len(daily_returns) < 2:
            return 0.5
            
        # Calculate standard deviation of returns
        returns_std = np.std(daily_returns)
        
        # Consistency is inversely proportional to standard deviation
        # Higher consistency = lower standard deviation
        consistency = 1.0 / (1.0 + returns_std)
        
        return consistency
    except Exception as e:
        print(f"Consistency calculation error: {e}")
        return 0.5

def calculate_recovery(strat):
    try:
        analyzer = strat.analyzers.ta.get_analysis()
        drawdown = strat.analyzers.drawdown.get_analysis()
        
        net_profit = analyzer.pnl.net.total
        max_drawdown = drawdown.max.drawdown
        
        if max_drawdown == 0:
            return 0.0
            
        return net_profit / max_drawdown
    except Exception as e:
        print(f"Recovery calculation error: {e}")
        return 0.0

def calculate_expectancy(strat):
    try:
        analyzer = strat.analyzers.ta.get_analysis()
        total_closed = analyzer.total.closed
        
        if total_closed < 10:
            return 0.0
            
        total_won = analyzer.won.total
        win_rate = total_won / total_closed
        
        avg_win = analyzer.won.pnl.average
        avg_loss = analyzer.lost.pnl.average
        
        return (win_rate * avg_win) + ((1 - win_rate) * avg_loss)
    except Exception as e:
        print(f"Expectancy calculation error: {e}")
        return 0.0

def calculate_omega(strat):
    try:
        analyzer = strat.analyzers.ta.get_analysis()
        total_closed = analyzer.total.closed
        
        if total_closed < 10:
            return 0.0
            
        # Get daily returns
        daily_returns = []
        for i in range(1, len(strat)):
            daily_return = (strat.broker.get_value(i) / strat.broker.get_value(i-1)) - 1
            daily_returns.append(daily_return)
        
        if not daily_returns:
            return 0.0
            
        # Set threshold to 0 (risk-free rate)
        threshold = 0.0
        
        # Calculate sum of returns above threshold
        sum_positive = sum([r for r in daily_returns if r > threshold])
        
        # Calculate sum of returns below threshold (absolute value)
        sum_negative = abs(sum([r for r in daily_returns if r <= threshold]))
        
        if sum_negative == 0:
            return 0.0
            
        return sum_positive / sum_negative
    except Exception as e:
        print(f"Omega calculation error: {e}")
        return 0.0

def calculate_risk_adjusted_return(strat):
    try:
        analyzer = strat.analyzers.ta.get_analysis()
        total_closed = analyzer.total.closed
        
        if total_closed < 10:
            return 0.0
            
        returns = strat.analyzers.returns.get_analysis()
        drawdown = strat.analyzers.drawdown.get_analysis()
        
        annual_return = returns.get('rnorm', 0)
        max_drawdown = drawdown.max.drawdown / 100.0  # Convert from percentage to decimal
        
        if max_drawdown == 0:
            return 0.0
            
        # Calculate risk-adjusted return as annual return divided by max drawdown
        return annual_return / max_drawdown
    except Exception as e:
        print(f"Risk-adjusted return calculation error: {e}")
        return 0.0

def calculate_profit_factor(strat):
    try:
        analyzer = strat.analyzers.ta.get_analysis()
        total_closed = analyzer.total.closed
        
        if total_closed < 10:
            return 0.0
            
        total_profit = analyzer.won.pnl.total
        total_loss = abs(analyzer.lost.pnl.total)
        
        if total_loss == 0:
            return 0.0
            
        return total_profit / total_loss
    except Exception as e:
        print(f"Profit Factor calculation error: {e}")
        return 0.0 