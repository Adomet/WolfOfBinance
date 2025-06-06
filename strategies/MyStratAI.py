import datetime
import backtrader as bt
import numpy as np
from PPO.AgentACT import AgentACT
from indicators import AverageRage, AverageDiff, ATD, TD9, SuperTrendBand, SuperTrend, EWO
from PPO.AgentTrans import AgentTrans
from Debug import log

input_dims = 13 # Feature dimensions per state
seq_len = 8 # History length
global_agent = AgentACT(n_actions=3, input_dims=input_dims, seq_len=seq_len)

### Trade Strategy ###
class MyStratAI(bt.Strategy):
    params=(('p0',0),('p1',0),('p2',0),('p3',0),('p4',0),('p5',0),('p6',0),('p7',0),('p8',0),('p9',0),('p10',0),('p11',0),('p12',0),('p13',0),('p14',0),('p15',0),('p16',0),('p17',0),('p18',0),('p19',0),('p20',0),('p21',0))

    def __init__(self):
        self.agent                     = global_agent

        self.plot                      =  True
        self.supertrend                =  SuperTrend(self.data,period=3,multiplier=max(self.params.p0/100,1),plot=True)
        self.tdnine                    =  TD9(plot=True)
        self.ar                        =  AverageRage(self.data,period=130,plot=self.plot)
        self.ewo                       =  EWO(self.data,fper = self.params.p19,sper = self.params.p20,plot=self.plot)

        self.isbull                    =  False
        #BULL
        self.bull_ewo_offset           =  self.params.p17 / 1000
        self.bull_rsi                  =  bt.ind.RelativeStrengthIndex(self.data, period=3,safediv=True,plot=self.plot)
        self.bull_rsi_high             =  self.params.p1 / 10
        self.bull_rsi_low              =  self.params.p2 / 10
        self.params.p3                 =  max(self.params.p3,1)
        self.bull_diff_ema             =  bt.ind.TripleExponentialMovingAverage(period=self.params.p3,plot=self.plot)
        self.bull_diff_ema_heigh       =  self.bull_diff_ema + (self.bull_diff_ema / self.params.p4 * 10) 
        self.bull_diff_ema_low         =  self.bull_diff_ema - (self.bull_diff_ema / self.params.p5 * 10)
        self.bull_takeprofit           =  self.params.p6 / 10000

        #BEAR
        self.bear_ewo_offset           =  self.params.p18/1000
        self.params.p7                 =  max(self.params.p7,1)
        self.bear_rsi                  =  bt.ind.RelativeStrengthIndex(self.data, period=self.params.p7,safediv=True,plot=self.plot)
        self.bear_rsi_high             =  self.params.p8 / 10
        self.bear_rsi_low              =  self.params.p9 / 10
        self.params.p10                =  max(self.params.p10,1)
        self.bear_diff_ema             =  bt.ind.TripleExponentialMovingAverage(period=self.params.p10,plot=self.plot)
        self.bear_diff_ema_heigh       =  self.bear_diff_ema + ((self.bear_diff_ema / self.params.p11) * self.ar * 37/10) 
        self.bear_diff_ema_low         =  self.bear_diff_ema - ((self.bear_diff_ema / self.params.p12) * 10)
        self.bear_takeprofit           =  self.params.p13 / 10000 
        self.stop_loss                 =  self.params.p14 / 10000
        self.timeProfitRetioDropRate   =  self.params.p15 / 1000000

        self.hardSTPDefault            =  160 / 1000
        self.min_tp_per                =  13 / 1000
        self.buyprice                  =  -1
        self.last_buy_price            =  -1
        self.ordered                   =  False
        self.buyPercent                =  0.99

        self.posCandleCount            =  0
        self.buysize                   =  0

        ### PPO ###
        self.strat_order               =  0
        self.current_reward            =  0
        self.reward                    =  0
        self.isHalt                    =  False
        self.value                     =  1000.0
        self.prev_value                =  1000.0
        self.tradeCount                =  0
        self.start_cash                =  1000.0
        
        self.trade_penalty = 0.05

        # For log returns calculation
        self.prev_close = None
        
        # For drawdown tracking
        self.peak_equity = 1000.0
        self.max_drawdown_penalty = 10.0  # Maximum penalty for 100% drawdown

        ### Potential Lost Profit Tracking ###
        self.sellprice = -1

        ### State History for Transformer ###
        self.state_history = []
        self.max_history = seq_len

    def notify_data(self, data, status, *args, **kwargs):
        dn = data._name
        dt = datetime.datetime.utcnow() + datetime.timedelta(minutes=180)
        msg= 'Data Status: {}'.format(data._getstatusname(status))
        log(str(dt)+" "+str(dn)+" "+str(msg))
        self.isbuyready = False
        if data._getstatusname(status) == 'LIVE':
            self.live_data = True
        else:
            self.live_data = False

    def orderer(self, isbuy, reason=""):
        if(self.ordered):
            return 
        
        self.ordered = True
        if(isbuy and self.buyprice == -1):
            self.reward -= (self.trade_penalty) # Apply penalty for buying
            self.sellprice = -1
            self.buyprice = self.data.close[0]
            self.buysize = int(self.broker.get_cash() * self.buyPercent) / self.data.close[0]
            self.buy(size=self.buysize)
            if reason:
                log(reason)

        elif(not isbuy and not self.buyprice == -1):
            profit =  self.normalizeProfit(self.data.close[0], self.buyprice)
            self.reward += profit
            self.reward -= (self.trade_penalty) # Apply penalty for selling
            self.buyprice = -1
            self.tradeCount += 1
            self.buysize = 0
            self.sellprice = self.data.close[0]
            self.close()
            if reason:
                log(reason)

    def strategy_order(self, order):
        if(self.strat_order != 0):
            return
        
        self.strat_order = order

    def getEquity(self):
        return self.broker.get_value()

    def next(self):
        if(self.isHalt):
            return
        
        self.reward = 0
        self.prev_value = self.value
        self.value = self.getEquity()
        self.ordered = False

        if(self.value < 300):
            print("value: ", self.value)
            print(f"Drawdown: {(self.start_cash - self.value) / self.start_cash}")
            self.orderer(False, f"HALTED {self.data.close[0]}")
            self.isHalt = True

        #self.reward += (self.value - self.prev_value)

        #if in position reward if price goes up else reward if price goes down
        if(self.buysize > 0):
            self.reward += (self.data.close[0] - self.data.open[0])
        else:
            self.reward += (self.data.open[0] - self.data.close[0])

        # Get current state and update history
        current_state = self.getCurrentState()
        self.updateStateHistory(current_state)
        
        # Get state sequence for transformer
        state_sequence = self.getStateSequence()
        
        # Get action from transformer agent
        action, prob, val = self.agent.choose_action(state_sequence)

        # Execute trading action
        if(action == 2):  # Buy
            self.orderer(True, f"TRANS_BUY {self.data.close[0]}")
        elif(action == 1):  # Sell
            self.orderer(False, f"TRANS_SELL {self.data.close[0]}")
        
        # Store experience in agent's memory
        if(self.agent.model.training):
            self.agent.remember(state_sequence, action, prob, val, self.reward, False)

    def normalize(self, value, min, max):
        return (value - min) / (max - min)
    
    def normalizeIndicator(self, value, divisor):
        return 2.0 * (value / divisor) - 1.0
    
    def normalizeMA(self,value):
        return (value - self.data.close[0]) / self.data.close[0]
    
    def normalizePrice(self, min , max):
        return (self.data.close[0] - min) / (max - min)
    
    def getEquity(self):
        return self.broker.get_value()

    def normalizeProfit(self, price, buyprice):
        if (buyprice <= 0):
            return 0

        return (price - buyprice) / buyprice

    def updateStateHistory(self, state):
        """Update the state history buffer with the current state"""
        self.state_history.append(state.copy())
        
        # Keep only the last max_history states
        if len(self.state_history) > self.max_history:
            self.state_history.pop(0)

    def getStateSequence(self):
        """Get the state sequence for the transformer"""
        # If we don't have enough history, pad with the first available state
        if len(self.state_history) < self.max_history:
            # Pad with the first state if available, otherwise zeros
            if len(self.state_history) > 0:
                padding_state = self.state_history[0]
                padded_history = [padding_state] * (self.max_history - len(self.state_history)) + self.state_history
            else:
                # If no history yet, create zero states
                zero_state = np.zeros(input_dims, dtype=np.float32)
                padded_history = [zero_state] * self.max_history
        else:
            padded_history = self.state_history[-self.max_history:]
        
        return np.array(padded_history, dtype=np.float32)

    def getCurrentState(self):
        """Get the current state for the agent using efficient calculations"""
        state = np.zeros(input_dims, dtype=np.float32)

        state[0] = self.normalizeIndicator(self.bull_rsi, 100)
        state[1] = self.normalizeIndicator(self.bear_rsi, 100)
        state[2] = self.normalizeMA(self.bull_diff_ema[0])*10
        state[3] = self.normalizeMA(self.bear_diff_ema[0])*10
        state[4] = self.normalizeMA(self.supertrend[0])*10
        state[5] = self.ewo[0]/10.0
        state[6] = self.ar[0]/10.0
        state[7] = self.tdnine[0]/20.0
        state[8] = 1.0 if self.buysize > 0 else 0.0
        state[9] = 1.0 if (self.supertrend < self.data.close[0]) else 0.0
        state[10] = self.normalizeProfit(self.data.close[0], self.buyprice)*10
        state[11] = self.normalizeProfit(self.data.close[0],  self.data.open[0])*10
        state[12] = self.normalizeProfit(self.data.high[0],  self.data.low[0])*10

        return state

    def getState(self):
        """Legacy method - now just returns the state sequence"""
        return self.getStateSequence()

    def stop(self):
        state_sequence = self.getStateSequence()
        action, prob, val = self.agent.choose_action(state_sequence)
        final_reward_val = self.normalizeProfit(self.value, self.start_cash) 
        print(f"Trade Count: {self.tradeCount}, Final: {final_reward_val}, Equity: {self.value}")
        if(self.agent.model.training):  
            self.agent.remember(state_sequence, action, prob, val, final_reward_val*10, True) 
        
        