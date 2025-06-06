import datetime
import backtrader as bt
from indicators import AverageRage, AverageDiff, ATD, TD9, SuperTrendBand, SuperTrend, EWO
from Debug import log

### Trade Strategy ###
class MyStratV1(bt.Strategy):
    params=(('p0',0),('p1',0),('p2',0),('p3',0),('p4',0),('p5',0),('p6',0),('p7',0),('p8',0),('p9',0),('p10',0),('p11',0),('p12',0),('p13',0),('p14',0),('p15',0),('p16',0),('p17',0),('p18',0),('p19',0),('p20',0))
    def __init__(self):
        self.plot                      =  True
        self.params.p0                 =  max(self.params.p0,1)
        self.supertrend                =  SuperTrend(self.data,period=self.params.p0,multiplier=max(self.params.p1/100,1),plot=True)
        self.tdnine                    =  TD9(plot=True)
        self.adx                       =  bt.ind.AverageDirectionalMovementIndex(self.data,period = 13,plot=self.plot)
        self.ar                        =  AverageRage(self.data,period=self.params.p18,plot=self.plot)

        self.isbull                    =  False
        #BULL
        self.params.p2                 =  max(self.params.p2,1)
        self.bull_rsi                  =  bt.ind.RelativeStrengthIndex(self.data, period=self.params.p2,safediv=True,plot=self.plot)
        self.bull_rsi_high             =  self.params.p3 / 10
        self.bull_rsi_low              =  self.params.p4 / 10
        self.params.p5                 =  max(self.params.p5,1)
        self.bull_diff_ema             =  bt.ind.TripleExponentialMovingAverage(period=self.params.p5,plot=self.plot)
        self.bull_diff_ema_heigh       =  self.bull_diff_ema + (self.bull_diff_ema / self.params.p6 * 10) 
        self.bull_diff_ema_low         =  self.bull_diff_ema - (self.bull_diff_ema / self.params.p7 * 10)
        self.bull_takeprofit           =  self.params.p8 / 10000

        #BEAR
        self.params.p9                 =  max(self.params.p9,1)
        self.bear_rsi                  =  bt.ind.RelativeStrengthIndex(self.data, period=self.params.p9,safediv=True,plot=self.plot)
        self.bear_rsi_high             =  self.params.p10 / 10
        self.bear_rsi_low              =  self.params.p11 / 10
        self.params.p12                =  max(self.params.p12,1)
        self.bear_diff_ema             =  bt.ind.TripleExponentialMovingAverage(period=self.params.p12,plot=self.plot)
        self.bear_diff_ema_heigh       =  self.bear_diff_ema + ((self.bear_diff_ema / self.params.p13) * self.ar * 37/10) 
        self.bear_diff_ema_low         =  self.bear_diff_ema - ((self.bear_diff_ema / self.params.p14) * 10)
        self.bear_takeprofit           =  self.params.p15 / 10000 
        self.stop_loss                 =  self.params.p16 / 10000
        self.timeProfitRetioDropRate   =  self.params.p17 / 1000000

        self.hardSTPDefault            =  16 / 100
        self.min_tp_per                =  13 / 1000
        self.buyprice                  =  -1
        self.ordered                   =  False

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

    def orderer(self, isbuy):
        if(self.ordered):
            return 
        
        self.ordered =True
        if(isbuy and self.buyprice == -1 ):
            self.buyprice = self.data.close[0]
            self.buysize = int(self.broker.get_cash()*99/100) / self.data.close[0]
            self.buy(size=self.buysize)
            #print("B " + str(self.data.close[0]))

        elif(not isbuy and not self.buyprice == -1 ):
            self.buysize = 0
            self.buyprice = -1
            self.close()
            #print("S " + str(self.data.close[0]))


    def next(self):

        self.ordered                = False
        adxtrigger                  = self.adx             >=  26
        td9selltrigger              = self.tdnine          >=  10
        isProfit                    = self.data.close[0]   >   self.buyprice
        isSellPer                   = self.data.close[0]   >= (self.buyprice + (self.buyprice * self.min_tp_per))
        isStop                      = self.data.close[0]   <=  self.buyprice - (self.buyprice * self.stop_loss)
        candleDiffbuytrigger        = 358 / 10000          >=  1 - (self.data.close[0]/self.data.open[0])

        #wasBull = self.isbull
        self.isbull = (self.supertrend < self.data.close[0])
        #if(wasBull != self.isbull):
        #    log("Switched: "+(" Bull" if self.isbull else " Bear")+" at: "+str(self.data.close[0]))

        if(self.isbull):
            bull_rsibuytrigger      = self.bull_rsi        <=  self.bull_rsi_low
            bull_rsiselltrigger     = self.bull_rsi        >=  self.bull_rsi_high 
            bull_avgdiffselltrigger = self.data.close[0]   >=  self.bull_diff_ema_heigh
            bull_avgdiffbuytrigger  = self.data.close[0]   <=  self.bull_diff_ema_low 
            bull_isTakeProfit       = self.data.close[0]   >=  self.buyprice + (self.buyprice * self.bull_takeprofit) and not self.buyprice == -1


            if(bull_rsibuytrigger and bull_avgdiffbuytrigger ): #problematic
                log("BUY Bull_IND BUY")
                self.isbuyready = True
            if(bull_rsiselltrigger and bull_avgdiffselltrigger and td9selltrigger and isSellPer):
                log("Bull_IND SELL")
                self.orderer(False)
            if(bull_isTakeProfit):
                log("Bull_TAKE PROFIT")
                self.orderer(False)
            if(isStop and adxtrigger and not self.isbuyready):
                log("Bull_STOPPED")
                self.orderer(False)

        else:
            bear_rsibuytrigger      = self.bear_rsi        <=  self.bear_rsi_low
            bear_rsiselltrigger     = self.bear_rsi        >=  self.bear_rsi_high 
            bear_avgdiffselltrigger = self.data.close[0]   >=  self.bear_diff_ema_heigh
            bear_avgdiffbuytrigger  = self.data.close[0]   <=  self.bear_diff_ema_low
            bear_isTakeProfit       = self.data.close[0]   >=  self.buyprice + (self.buyprice * self.bear_takeprofit) and not self.buyprice == -1


            if(bear_rsibuytrigger and bear_avgdiffbuytrigger ):
                log("BUY Bear_IND BUY")
                self.isbuyready = True
            if(bear_rsiselltrigger and bear_avgdiffselltrigger and isSellPer): #problematic
                self.orderer(False)
                log("Bear_IND SELL")
            if(bear_isTakeProfit):
                self.orderer(False)
                log("Bear_TAKE PROFIT")
            if(isStop and adxtrigger and not self.isbuyready):
                self.orderer(False)
                log("Bear_STOPPED")


        if(candleDiffbuytrigger and self.isbuyready):
            self.isbuyready=False
            self.orderer(True)
            log("BUY")     

        if(not self.buyprice == -1):
            self.posCandleCount+=1
        else:
            self.posCandleCount = 0   

        ### NEW STUFF ###
        TimeProfitRatioSTP          = (self.data.close[0] - self.buyprice)/self.buyprice >= ((self.bull_takeprofit) - (self.timeProfitRetioDropRate * (self.posCandleCount))) and not self.isbull 
        hardSTP                     = self.data.close[0]    <= self.buyprice - (self.buyprice *  self.hardSTPDefault) and not self.isbull
        
        if(TimeProfitRatioSTP and isProfit):
            self.orderer(False)
            log("Time/Profit SELL")
        
        if(hardSTP and adxtrigger):
            self.orderer(False)
            log("HARD_STP SELL")