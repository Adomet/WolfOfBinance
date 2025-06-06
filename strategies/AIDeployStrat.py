import datetime
import backtrader as bt
from indicators import AverageRage, AverageDiff, ATD, TD9, SuperTrendBand, SuperTrend, EWO
from Debug import log
import numpy as np
import datetime
from PPO.AgentTrans import AgentTrans
import random
import torch as T

from PPO.AgentDis import AgentDis
from PPO.AgentCon import AgentCon

# Set random seeds for reproducibility
def set_seeds(seed=42):
    random.seed(seed)
    np.random.seed(seed)
    T.manual_seed(seed)
    if T.cuda.is_available():
        T.cuda.manual_seed(seed)
        T.cuda.manual_seed_all(seed)
        T.backends.cudnn.deterministic = True
        T.backends.cudnn.benchmark = False

# Set global seeds
set_seeds(42)

### Trade Strategy ###
class AIDeployStrat(bt.Strategy):
    params=(('p0',0),('p1',0),('p2',0),('p3',0),('p4',0),('p5',0),('p6',0),('p7',0),('p8',0),('p9',0),('p10',0),('p11',0),('p12',0),('p13',0),('p14',0),('p15',0),('p16',0),('p17',0),('p18',0),('p19',0),('p20',0),('p21',0))
    AI_Mode                   =  True

    def __init__(self):
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
        # Use the static agent instead of creating a new one
        self.input_dims                =  23
        self.current_reward            =  0  # For accumulating rewards during the episode
        
        # Continuous action threshold values
        self.threshold_buy             =  0.5   # 0.5'den büyük değerler al sinyali
        self.threshold_sell            =  -0.5  # -0.5'den küçük değerler sat sinyali

        self.agent                =  AgentTrans(n_actions=3, input_dims=self.input_dims)

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
            self.buy(size=self.buysize)
            if reason:
                log(reason)

        elif(not isbuy and not self.buyprice == -1):
            self.buysize = 0
            self.buyprice = -1
            self.close()
            if reason:
                log(reason)

    def getState(self):
        """Get the current state for the agent using efficient calculations"""
        # Pre-calculate common values
        close_price = self.data.close[0]
        
        # Create state array directly instead of appending
        state = np.zeros(self.input_dims, dtype=np.float32)
        
        # Fill state array with normalized values
        state[0] = self.normalizeIndicator(self.bull_rsi, 100)
        state[1] = self.normalizeIndicator(self.bear_rsi, 100)
        state[2] = self.normalizeMA(self.bull_diff_ema)/10
        state[3] = self.normalizeMA(self.bear_diff_ema)/10
        state[4] = self.normalizeIndicator(self.ewo, 1)
        state[5] = self.normalizeIndicator(self.ar, 1)
        state[6] = self.normalizeMA(self.supertrend)/10
        
        # Price and profit information
        state[7] = self.normalizeProfit(close_price, self.buyprice)
        state[8] = self.normalizeProfit(close_price, self.data.close[-1])*10
        state[9] = self.normalizeProfit(self.data.high[0], self.data.low[0])*10
        
        # Binary indicator for position (1 if in position, 0 if not)
        state[10] = 1.0 if self.buysize > 0 else 0.0
        
        # Position duration normalized by dividing by 100
        state[11] = self.posCandleCount / 100.0
        
        isbull = (self.supertrend < self.data.close[0])
        # Market trend indicator (1.0 for bullish, 0.0 for bearish)
        state[12] = 1.0 if isbull else 0.0

        # Last 20 candles' relative prices to first candle's open (increased from 5 to 20)
        first_candle_open = self.data.open[-10]  # Get the open price of the first candle
        for i in range(10):  # Changed from 5 to 20
            candle_price = self.data.close[-(10-i)]  # Get each candle's close price
            state[12+i] = self.normalizeProfit(candle_price, first_candle_open) * 10

        
        return state

    def normalize(self, value, min, max):
        return (value - min) / (max - min)
    
    def normalizeIndicator(self, value, divisor):
        return 2.0 * (value / divisor) - 1.0
    
    def normalizeMA(self,value):
        return value / self.data.close[0]
    
    def normalizePrice(self, min , max):
        return (self.data.close[0] - min) / (max - min)
    
    def getEquity(self):
        return (self.data.close[0] * self.buysize) + self.broker.get_cash()

    def normalizeProfit(self, price, buyprice):
        if (buyprice == -1):
            return 0

        return (price - buyprice) / buyprice
    

    def getReward(self):
        return self.getEquity()/1000

    def next(self):
        if(self.AI_Mode):
            self.orderer(True, "AI_BUY")
            self.orderer(False, "AI_SELL")
            return


        self.ordered = False
        isStop = self.data.close[0] <= self.buyprice - (self.buyprice * self.stop_loss * self.ar[0])

        self.isbull = (self.supertrend < self.data.close[0])

        if(self.isbull):
            bull_rsibuytrigger      = self.bull_rsi        <=  self.bull_rsi_low
            bull_rsiselltrigger     = self.bull_rsi        >=  self.bull_rsi_high 
            bull_avgdiffselltrigger = self.data.close[0]   >=  self.bull_diff_ema_heigh
            bull_avgdiffbuytrigger  = self.data.close[0]   <=  self.bull_diff_ema_low 
            bull_isTakeProfit       = self.data.close[0]   >=  self.buyprice + (self.buyprice * self.bull_takeprofit) and not self.buyprice == -1
            bull_ewo_trigger        = self.ewo             <=  self.bull_ewo_offset

            if(bull_avgdiffbuytrigger and (bull_rsibuytrigger or bull_ewo_trigger)):
                self.isbuyready = True
            elif(bull_rsiselltrigger and bull_avgdiffselltrigger):
                self.orderer(False, "Bull_IND SELL")
            elif(bull_isTakeProfit):
                self.orderer(False, "Bull_TAKE PROFIT")
            elif(isStop):
                self.orderer(False, "Bull_STOPPED")

        else:
            bear_rsibuytrigger      = self.bear_rsi        <=  self.bear_rsi_low
            bear_rsiselltrigger     = self.bear_rsi        >=  self.bear_rsi_high 
            bear_avgdiffselltrigger = self.data.close[0]   >=  self.bear_diff_ema_heigh
            bear_avgdiffbuytrigger  = self.data.close[0]   <=  self.bear_diff_ema_low
            bear_isTakeProfit       = self.data.close[0]   >=  self.buyprice + (self.buyprice * self.bear_takeprofit * self.ar) and not self.buyprice == -1
            bear_ewo_trigger        = self.ewo             <=  -self.bear_ewo_offset

            if(bear_avgdiffbuytrigger and bear_rsibuytrigger and bear_ewo_trigger):
                self.isbuyready = True
            elif(bear_rsiselltrigger and bear_avgdiffselltrigger):
                self.orderer(False, "Bear_IND SELL")
            elif(bear_isTakeProfit):
                self.orderer(False, "Bear_TAKE PROFIT")
            elif(isStop):
                self.orderer(False, "Bear_STOPPED")

        if(self.isbuyready):
            self.isbuyready = False
            self.orderer(True, "AI_BUY")

        if(not self.buyprice == -1):
            self.posCandleCount += 1
        else:
            self.posCandleCount = 0   

        ### NEW STUFF ###
        TimeProfitRatioSTP = (self.data.close[0] - self.buyprice)/self.buyprice >= ((self.bull_takeprofit) - (self.timeProfitRetioDropRate * (self.posCandleCount))) and not self.isbull 
        hardSTP = self.data.close[0] <= self.buyprice - (self.buyprice * self.hardSTPDefault)
        
        if(TimeProfitRatioSTP):
            self.orderer(False, "Time_Profit SELL")
        
        if(hardSTP):
            self.orderer(False, "HARD_STP SELL") 

        state = self.getState()
        action, prob, val = self.agent.choose_action(state)
        print(f"Action: {action}, Prob: {prob}, Value: {val}")
        reward = self.getReward()
        self.agent.remember(state, action, prob, val, reward, False)
        