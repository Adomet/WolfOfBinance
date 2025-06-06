import datetime
import backtrader as bt
from indicators import AverageRage, AverageDiff, ATD, TD9, SuperTrendBand, SuperTrend, EWO
from Debug import log

### Trade Strategy ###
class MyStratV4(bt.Strategy):
    params=(('p0',0),('p1',0),('p2',0),('p3',0),('p4',0),('p5',0),('p6',0),('p7',0),('p8',0),('p9',0),('p10',0),('p11',0),('p12',0),('p13',0),('p14',0),('p15',0),('p16',0),('p17',0),('p18',0),('p19',0),('p20',0),('p21',0))
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
        self.bull_diff_ema_heigh       =  self.bull_diff_ema + ((self.bull_diff_ema / self.params.p4)) 
        self.bull_diff_ema_low         =  self.bull_diff_ema - ((self.bull_diff_ema / self.params.p5) * 10)
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

    def orderer(self, isbuy, reason="", buyPercent=None):
        if(self.ordered):
            return 
        
        self.ordered = True
        if(isbuy and self.buyprice == -1):
            self.buyprice = self.data.close[0]
            if buyPercent is None:
                buyPercent = self.buyPercent
            self.buysize = int(self.broker.get_cash() * buyPercent) / self.data.close[0]
            self.buy(size=self.buysize)
            if reason:
                log(reason)

        elif(not isbuy and not self.buyprice == -1):
            self.buysize = 0
            self.buyprice = -1
            self.close()
            if reason:
                log(reason)

    def next(self):
        self.ordered                = False
        isStop                      = self.data.close[0]   <=  self.buyprice - (self.buyprice * self.stop_loss * self.ar[0])

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
            if(bull_rsiselltrigger and bull_avgdiffselltrigger):
                self.orderer(False, "Bull_IND SELL")
            if(bull_isTakeProfit):
                self.orderer(False, "Bull_TAKE PROFIT")
            if(isStop):
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
            if(bear_rsiselltrigger and bear_avgdiffselltrigger):
                self.orderer(False, "Bear_IND SELL")
            if(bear_isTakeProfit):
                self.orderer(False, "Bear_TAKE PROFIT")
            if(isStop):
                self.orderer(False, "Bear_STOPPED")

        if(self.isbuyready):
            self.isbuyready = False
            self.orderer(True, "CANDLE_TRIG BUY", self.buyPercent)

        if(not self.buyprice == -1):
            self.posCandleCount += 1
        else:
            self.posCandleCount = 0   

        ### NEW STUFF ###
        TimeProfitRatioSTP          = (self.data.close[0] - self.buyprice)/self.buyprice >= ((self.bull_takeprofit) - (self.timeProfitRetioDropRate * (self.posCandleCount))) and not self.isbull 
        hardSTP                     = self.data.close[0]    <= self.buyprice - (self.buyprice *  self.hardSTPDefault)
        
        if(TimeProfitRatioSTP):
            self.orderer(False, "Time_Profit SELL")
        
        if(hardSTP):
            self.orderer(False, "HARD_STP SELL") 