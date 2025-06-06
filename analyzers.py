import backtrader as bt
from backtrader.utils import AutoOrderedDict

class GLP(bt.Analyzer):
    """
    Average gain/loss per trade analyzer
    """
    def start(self):
        super(GLP, self).start()
        
    def create_analysis(self):
        self.trade = AutoOrderedDict()
        self._value = 0

        self.rets = AutoOrderedDict()  # dict with . notation
        self.rets.gper = 0
        self.rets.lper = 0
        self.rets.len = 0
        self.rets.glp = 0

    def stop(self):
        if self.rets.len > 0:  # Only calculate if we have trades
            self.rets.gper = self.rets.gper / self.rets.len
            self.rets.lper = self.rets.lper / self.rets.len
            if self.rets.lper != 0:  # Prevent division by zero
                self.rets.glp = self.rets.gper / abs(self.rets.lper)
            else:
                self.rets.glp = float('inf') if self.rets.gper > 0 else 0
        self.rets._close()  # . notation cannot create more keys

    def notify_trade(self, trade):
        if trade.justopened:
            self.rets.len += 1
            self._value = trade.value  
        
        elif trade.status == trade.Closed:
            sval, pnl = trade.price, trade.pnlcomm
            if sval != 0:  # Prevent division by zero
                per = pnl / sval
                if pnl > 0:
                    self.rets.gper += per
                else:
                    self.rets.lper += per 

class AVGDD(bt.Analyzer):
    """
    Average Drawdown analyzer
    
    This analyzer tracks all drawdowns that occur during strategy execution
    and calculates their average value.
    """
    params = (
        ('fund', False),  # If True, analyze fund value, else analyze value
    )
    
    def create_analysis(self):
        self.rets = AutoOrderedDict()
        self.rets.drawdowns = []  # List to store all drawdowns
        self.rets.count = 0  # Number of drawdowns
        self.rets.avgdd = 0.0  # Average drawdown
        self.rets.maxdd = 0.0  # Maximum drawdown (for reference)
        
        # Peak tracking
        self.peak = None
        self.trough = None
        self.in_drawdown = False
        
    def next(self):
        # Get current portfolio value
        value = self.strategy.broker.fundvalue if self.p.fund else self.strategy.broker.getvalue()
        
        # First run or new peak
        if self.peak is None or value > self.peak:
            # If we were in a drawdown, record it
            if self.in_drawdown and self.trough is not None:
                dd_pct = (self.peak - self.trough) / self.peak
                self.rets.drawdowns.append(dd_pct)
                self.rets.count += 1
                self.rets.maxdd = max(self.rets.maxdd, dd_pct)
                self.in_drawdown = False
                self.trough = None
            self.peak = value
        else:
            # In drawdown
            self.in_drawdown = True
            if self.trough is None or value < self.trough:
                self.trough = value
                # Update max drawdown for this peak
                current_dd = (self.peak - value) / self.peak
                self.rets.maxdd = max(self.rets.maxdd, current_dd)
    
    def stop(self):
        # Ensure we record the final drawdown if still in one
        if self.in_drawdown and self.trough is not None:
            dd_pct = (self.peak - self.trough) / self.peak
            self.rets.drawdowns.append(dd_pct)
            self.rets.count += 1
            self.rets.maxdd = max(self.rets.maxdd, dd_pct)
        
        # Calculate average drawdown
        if self.rets.count > 0:
            self.rets.avgdd = sum(self.rets.drawdowns) / self.rets.count
        
        self.rets._close()  # Close the AutoOrderedDict 