import datetime
import backtrader as bt
from PPO.AgentDis import AgentDis
from indicators import AverageRage, AverageDiff, ATD, TD9, NormalizedRange, SuperTrendBand, SuperTrend, EWO
from Debug import log
import numpy as np
import datetime
import random
import torch as T
import collections

lookback = 8
input_dims = 14 + (lookback * 3)  # Corrected input_dims

### Trade Strategy ###
class AIStratDis(bt.Strategy):
    params=(('p0',1),('p1',1),('p2',1),('p3',1),('p4',1),('p5',1),('p6',1),('p7',1),('p8',1),('p9',1),('p10',1),('p11',1),('p12',1),('p13',1),('p14',1),('p15',1),('p16',1),('p17',1),('p18',1),('p19',1),('p20',1),('p21',1),('train_mode',False))

    def __init__(self):
        # This agent instance acts as a global fallback if no specific agent is passed to the strategy
        self.agent                 = AgentDis(n_actions=3, input_dims=input_dims)

        self.agent.train()
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
        self.ordered                   =  False
        self.buyPercent                =  0.99

        self.posCandleCount            =  0
        self.buysize                   =  0
        self.isbuyready                =  False

        ### PPO ###
        self.current_reward            =  0
        self.reward                    =  0
        self.isHalt                    =  False
        self.value                     =  0
        self.prev_value                =  0
        self.tradeCount                =  0
        self.start_cash                =  1000
        
        self.trade_penalty = 0.001

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
            self.buyprice = self.data.close[0]
            self.buysize = int(self.broker.get_cash() * self.buyPercent) / self.data.close[0]
            self.reward -= self.value * self.trade_penalty # Apply penalty for buying
            self.reward -= 1 # Apply penalty for buying

            self.buy(size=self.buysize)
            if reason:
                log(reason)

        elif(not isbuy and not self.buyprice == -1):
            profit =  self.normalizeProfit(self.data.close[0], self.buyprice)
            self.reward += profit
            self.reward -=  self.value * self.trade_penalty # Apply penalty for selling
            self.reward -= 1 # Apply penalty for buying

            self.tradeCount += 1
            #print(f"Reward: {self.reward}")

            self.buysize = 0
            self.buyprice = -1
            
            self.close()
            if reason:
                log(reason)

    def getState(self,strat_Input):
        """Get the current state for the agent using efficient calculations"""
        close_price = self.data.close[0]
        state = np.zeros(input_dims, dtype=np.float32)
        state[0] = self.normalizeIndicator(self.bull_rsi, 100)
        state[1] = self.normalizeIndicator(self.bear_rsi, 100)
        state[2] = self.normalizeMA(self.bull_diff_ema[0])*10
        state[3] = self.normalizeMA(self.bear_diff_ema[0])*10

        state[4] = self.normalizeIndicator(self.ewo, 1)/2.0
        state[5] = self.normalizeIndicator(self.ar, 1)
        state[6] = self.normalizeMA(self.supertrend[0])*10
        
        # Price and profit information
        state[7] = self.normalizeProfit(close_price, self.buyprice)*10
        state[8] = self.normalizeProfit(self.data.high[0], self.data.low[0])*10
        
        # Binary indicator for position (1 if in position, 0 if not)
        state[9] = 1.0 if self.buysize > 0 else 0.0
        
        # Position duration normalized by dividing by 100
        state[10] = self.posCandleCount / 200.0

        state[11] = self.tdnine[0]/20.0
        
        isbull = (self.supertrend < close_price)
        # Market trend indicator (1.0 for bullish, 0.0 for bearish)
        state[12] = 1.0 if isbull else 0.0

        state[13] = strat_Input

        first_open = self.data.open[-lookback]
        # Add the current price as the last element
        state[13] = self.normalizeProfit(close_price, first_open)*10

        for i in range(lookback):
            state[14 + (3*i)] = self.normalizeProfit(self.data.close[-lookback + i], first_open)*10
            state[14 + (3*i) + 1] = self.normalizeProfit(self.data.close[-lookback + i], self.data.open[-lookback + i])*10
            state[14 + (3*i) + 2] = self.normalizeProfit(self.data.high[-lookback + i], self.data.low[-lookback + i])*10

        #print(state)
        return state

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
    

    def next(self):
        if(self.isHalt):
            return
        
        self.prev_value = self.value
        self.value = self.getEquity()
        self.ordered = False

        if(not self.buyprice == -1):
            self.posCandleCount += 1
        else:
            self.posCandleCount = 0   

        if(self.value < 300):
            print("value: ", self.value)
            print(f"Drawdown: {(self.start_cash - self.value) / self.start_cash}")
            self.orderer(False, f"HALTED {self.data.close[0]}")
            self.isHalt = True

        # Get state sequence for transformer
        state_sequence = self.getState()
        
        # Get action from transformer agent
        action, prob, val = self.agent.choose_action(state_sequence)

        # Execute trading action
        if(action == 2):  # Buy
            self.orderer(True, f"TRANS_BUY {self.data.close[0]}")
        elif(action == 1):  # Sell
            self.orderer(False, f"TRANS_SELL {self.data.close[0]}")

        self.reward += self.value - self.prev_value
        #self.reward += self.normalizeProfit(self.value, self.start_cash)
        #self.reward += self.normalizeProfit(self.data.close[0], self.buyprice)/100
        
        # Store experience in agent's memory
        #print(f"Reward: {self.reward}")
        self.agent.remember(state_sequence, action, prob, val, self.reward, False)
        self.reward = 0

    def stop(self):
        state_sequence = self.getState()
        action, prob, val = self.agent.choose_action(state_sequence)
        print(f"Trade Count: {self.tradeCount}, Equity: {self.value}")
        final_reward_val = self.normalizeProfit(self.value, self.start_cash) 
        print(f"Final: {final_reward_val}")
        self.agent.remember(state_sequence, action, prob, val, final_reward_val, True) 

        
        