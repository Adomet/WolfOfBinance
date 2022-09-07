from gtts import gTTS
from ccxtbt import CCXTStore
from config import BINANCE, COIN_TARGET, COIN_REFER, DEBUG
import os, playsound, time, backtrader as bt, datetime

### Text To Speach Stuff ###
Buytext    = "Buy " + COIN_TARGET
Selltext   = "Sell "+ COIN_TARGET

def log(msg):
    print(msg)
    with open('logs.txt','a') as f:
        f.write(msg +'\n')


def speak(text):
    return
    language = 'en'
    filename ="output.mp3"
    output = gTTS(text=text, lang = language,slow=True)
    output.save(filename)
    playsound.playsound(filename)
    os.remove(filename)


class TD9(bt.Indicator):
    lines = ('tdnine',)
    plotinfo = dict(
        plot=True,
        plotname='tdnine',
        subplot=True,
        plotlinelabels=True)


    def __init__(self):
        self.addminperiod(5)
        self.prvcandleclose =-1
        self.tdnine = 0

    def next(self):
        if(self.data.high[-4] < self.data.close):
            self.prvcandleclose  = self.data.close
            self.tdnine          = self.tdnine +1
        
        elif(self.tdnine > 0):
            self.tdnine =0
        
        if(self.data.low[-4] > self.data.close):
            self.prvcandleclose  = self.data.close
            self.tdnine          = self.tdnine -1
        
        elif(self.tdnine < 0):
            self.tdnine =0


        self.prvcandleclose = self.data.close
        self.lines.tdnine[0]     = self.tdnine

class SuperTrendBand(bt.Indicator):
    """
    Helper inidcator for Supertrend indicator
    """
    params = (('period',7),('multiplier',3))
    lines = ('basic_ub','basic_lb','final_ub','final_lb')


    def __init__(self):
        self.atr = bt.indicators.AverageTrueRange(period=self.p.period)
        self.l.basic_ub = ((self.data.high + self.data.low) / 2) + (self.atr * self.p.multiplier)
        self.l.basic_lb = ((self.data.high + self.data.low) / 2) - (self.atr * self.p.multiplier)

    def next(self):
        if len(self)-1 == self.p.period:
            self.l.final_ub[0] = self.l.basic_ub[0]
            self.l.final_lb[0] = self.l.basic_lb[0]
        else:
            #=IF(OR(basic_ub<final_ub*,close*>final_ub*),basic_ub,final_ub*)
            if self.l.basic_ub[0] < self.l.final_ub[-1] or self.data.close[-1] > self.l.final_ub[-1]:
                self.l.final_ub[0] = self.l.basic_ub[0]
            else:
                self.l.final_ub[0] = self.l.final_ub[-1]

            #=IF(OR(baisc_lb > final_lb *, close * < final_lb *), basic_lb *, final_lb *)
            if self.l.basic_lb[0] > self.l.final_lb[-1] or self.data.close[-1] < self.l.final_lb[-1]:
                self.l.final_lb[0] = self.l.basic_lb[0]
            else:
                self.l.final_lb[0] = self.l.final_lb[-1]

class SuperTrend(bt.Indicator):
    """
    Super Trend indicator
    """
    params = (('period', 3), ('multiplier', 6))
    lines = ('super_trend',)
    plotinfo = dict(subplot=False)

    def __init__(self):
        self.stb = SuperTrendBand(period = self.p.period, multiplier = self.p.multiplier)

    def next(self):
        if len(self) - 1 == self.p.period:
            self.l.super_trend[0] = self.stb.final_ub[0]
            return

        if self.l.super_trend[-1] == self.stb.final_ub[-1]:
            if self.data.close[0] <= self.stb.final_ub[0]:
                self.l.super_trend[0] = self.stb.final_ub[0]
            else:
                self.l.super_trend[0] = self.stb.final_lb[0]

        if self.l.super_trend[-1] == self.stb.final_lb[-1]:
            if self.data.close[0] >= self.stb.final_lb[0]:
                self.l.super_trend[0] = self.stb.final_lb[0]
            else:
                self.l.super_trend[0] = self.stb.final_ub[0]


### Trade Strategy ###
class MyStratLive(bt.Strategy):
    params=(('p0',0),('p1',0),('p2',0),('p3',0),('p4',0),('p5',0),('p6',0),('p7',0),('p8',0),('p9',0),('p10',0),('p11',0),('p12',0),('p13',0),('p14',0),('p15',0),('p16',0),('p17',0),('p18',0))
    def __init__(self):
        self.plot                      =  True
        self.params.p0                 =  max(self.params.p0,1)
        self.supertrend                =  SuperTrend(self.data,period=self.params.p0,multiplier=max(self.params.p1/100,1),plot=self.plot)
        self.superisBull               =  bt.ind.CrossOver(self.data.close,self.supertrend,plot=False)
        self.tdnine                    =  TD9(plot=self.plot)
        self.roc                       =  bt.ind.RateOfChange100(self.data,period=13,plot=self.plot)
        self.adx                       =  bt.ind.AverageDirectionalMovementIndex(self.data,period = 13,plot=self.plot)
        self.atr                       =  bt.ind.AverageTrueRange(self.data,period = 13,plot=self.plot)

        self.isbull                    =  False
        #BULL
        self.params.p2                 =  max(self.params.p2,1)
        self.bull_rsi                  =  bt.ind.RelativeStrengthIndex(self.data, period=self.params.p2,safediv=True,plot=self.plot)
        self.bull_rsi_high             =  self.params.p3
        self.bull_rsi_low              =  self.params.p4
        self.params.p5                 =  max(self.params.p5,1)
        self.bull_diff_ema             =  bt.ind.TripleExponentialMovingAverage(period=self.params.p5,plot=self.plot)
        self.bull_avgselldiffactor     =  self.params.p6
        self.bull_avgbuydiffactor      =  self.params.p7
        self.bull_diff_ema_heigh       =  self.bull_diff_ema + (self.bull_diff_ema / self.bull_avgselldiffactor * 10) 
        self.bull_diff_ema_low         =  self.bull_diff_ema - (self.bull_diff_ema / self.bull_avgbuydiffactor  * 10)          
        self.bull_stop_loss            =  self.params.p8 / 10
        self.bull_takeprofit           =  self.params.p9 / 10

        #BEAR
        self.params.p10                =  max(self.params.p10,1)
        self.bear_rsi                  =  bt.ind.RelativeStrengthIndex(self.data, period=self.params.p10,safediv=True,plot=self.plot)
        self.bear_rsi_high             =  self.params.p11
        self.bear_rsi_low              =  self.params.p12
        self.params.p13                =  max(self.params.p13,1)
        self.bear_diff_ema             =  bt.ind.TripleExponentialMovingAverage(period=self.params.p13,plot=self.plot)
        self.bear_avgselldiffactor     =  self.params.p14
        self.bear_avgbuydiffactor      =  self.params.p15
        self.bear_diff_ema_heigh       =  self.bear_diff_ema + (self.bear_diff_ema / self.bear_avgselldiffactor * 10) 
        self.bear_diff_ema_low         =  self.bear_diff_ema - (self.bear_diff_ema / self.bear_avgbuydiffactor  * 10)    
        self.bear_stop_loss            =  self.params.p16 / 10
        self.bear_takeprofit           =  self.params.p17 / 10

        self.buyprice                  =  -1
        self.ordered                   =  False
        self.hardSTPDefault            =  137
        self.timeProfitRetioDropRate   =  self.params.p18/1000000

        self.posCandleCountMax         =  896
        self.posCandleCount            =  0
        self.buysize                   =  0

    def notify_data(self, data, status, *args, **kwargs):
        dn = data._name
        dt = datetime.datetime.utcnow() + datetime.timedelta(minutes=180)
        msg= 'Data Status: {}'.format(data._getstatusname(status))
        log(str(dt)+" "+str(dn)+" "+str(msg))
        if data._getstatusname(status) == 'LIVE':
            self.live_data = True
        else:
            self.live_data = False

    def orderer(self, isbuy):
        if(self.ordered):
            return

        self.ordered =True    
        if(isbuy):
            cash,value = self.broker.get_wallet_balance(COIN_REFER)
            size = int(cash-1) / self.data.close[0]
            log("Buy state")
            if(self.live_data and cash > 11.0):
                self.order=self.buy(size=size)
                self.buyprice = self.data.close[0]
                speak(Buytext)
                log("Buyed price at:"+str(self.data.close[0])+" || Stoploss price at:"+ str(self.buyprice - (self.buyprice * self.bear_stop_loss/1000)) + " || TP_Sell price at:"+ str(self.buyprice + (self.buyprice * self.bull_takeprofit/1000)))
        else:
            coin,val = self.broker.get_wallet_balance(COIN_TARGET)
            self.buyprice = -1
            log("Sell state")
            if(self.live_data and (coin * self.data.close[0]) > 11.0):
                self.order=self.sell(size = coin)
                speak(Selltext)
                log("Closed price at:"+str(self.data.close[0]))


    def next(self):
        
        
        if self.live_data:
            cash,value = self.broker.get_wallet_balance(COIN_REFER)
            coin,val = self.broker.get_wallet_balance(COIN_TARGET)

        else:
            cash = 'NA'
            coin = 'NA'

        for data in self.datas:
            log('{} - {} | Coin {} | Cash {} | O: {} H: {} L: {} C: {} V:{} TEMA:{}'.format(data.datetime.datetime()+datetime.timedelta(minutes=180+15),
                data._name, coin, cash, data.open[0], data.high[0], data.low[0], data.close[0], data.volume[0], self.bull_diff_ema[0]))
            

        self.ordered                = False
        adxtrigger                  = self.adx            >=  26
        td9selltrigger              = self.tdnine         >=  10

        if(not self.superisBull[0] == 0):
            self.isbull = (self.superisBull[0] == 1)
            log("Switched: "+(" Bull" if self.isbull else " Bear")+" at: "+str(self.data.close[0]))


        #print("pos:"+str(self.position.size))
        
        #if(not self.live_data):
        #    return


        if(self.isbull):
            bull_rsibuytrigger      = self.bull_rsi       <=  self.bull_rsi_low
            bull_rsiselltrigger     = self.bull_rsi       >=  self.bull_rsi_high 
            bull_avgdiffselltrigger = self.data.close[0]  >=  self.bull_diff_ema_heigh
            bull_avgdiffbuytrigger  = self.data.close[0]  <=  self.bull_diff_ema_low 
            bull_isStop             = self.data.close[0]  <   self.buyprice - (self.buyprice * self.bull_stop_loss/1000 ) - self.atr / 13
            bull_isTakeProfit       = self.data.close[0]  >   self.buyprice + (self.buyprice * self.bull_takeprofit/1000) and not self.buyprice ==-1

            if(bull_rsibuytrigger  and bull_avgdiffbuytrigger ):
                log("Bull_IND BUY")
                self.orderer(True)
            elif(bull_rsiselltrigger and bull_avgdiffselltrigger and td9selltrigger):
                log("Bull_IND SELL")
                self.orderer(False)
            elif(bull_isStop and adxtrigger):
                log("Bull_STOPPED")
                self.orderer(False)
            elif(bull_isTakeProfit):
                log("Bull_TAKE PROFIT")
                self.orderer(False)

        else:
            bear_rsiselltrigger     = self.bear_rsi       >=  self.bear_rsi_high 
            bear_rsibuytrigger      = self.bear_rsi       <=  self.bear_rsi_low
            bear_avgdiffselltrigger = self.data.close[0]  >=  self.bear_diff_ema_heigh
            bear_avgdiffbuytrigger  = self.data.close[0]  <=  self.bear_diff_ema_low
            bear_isStop             = self.data.close[0]  <   self.buyprice - (self.buyprice * self.bear_stop_loss/1000) - self.atr / 13
            bear_isTakeProfit       = self.data.close[0]  >   self.buyprice + (self.buyprice * self.bear_takeprofit/1000) and not self.buyprice ==-1

            if(bear_rsibuytrigger    and bear_avgdiffbuytrigger ):
                log("Bear_IND BUY")
                self.orderer(True)
            elif(bear_rsiselltrigger and bear_avgdiffselltrigger):
                log("Bear_IND SELL")
                self.orderer(False)
            elif(bear_isStop and adxtrigger):
                log("Bear_STOPPED")
                self.orderer(False)
            elif(bear_isTakeProfit):
                log("Bear_TAKE PROFIT")
                self.orderer(False)
        

        ### NEW STUFF ###
        rocbuytrigger       = self.roc              >= self.data.close[0] * 502 /1000                               and self.isbull
        hardSTP             = self.data.close[0]    <= self.buyprice - (self.buyprice * self.hardSTPDefault/1000)   and not self.isbull
        TimeOutSTP          = self.posCandleCount   >= self.posCandleCountMax and not self.isbull                   and self.data.close[0] > self.buyprice
        TimeProfitRatioSTP  = (self.data.close[0] - self.buyprice)/self.buyprice >= ((self.bull_takeprofit/1000) - (self.timeProfitRetioDropRate * (self.posCandleCount))) and not self.isbull
        
        if(not self.buyprice == -1):
            self.posCandleCount+=1
        else:
            self.posCandleCount = 0
        
        if(TimeOutSTP):
            log("TimeOutSTP  SELL")
            self.orderer(False)
        
        if(rocbuytrigger):
            log("ROC_IND BUY")
            self.orderer(True)

        if(hardSTP):
            log("HARD_STP SELL")
            self.orderer(False)
        
        if(TimeProfitRatioSTP):
            log("Time/Profit SELL")
            self.orderer(False)



def main():
    cerebro = bt.Cerebro(quicknotify=True)

    broker_config = {
        'apiKey': BINANCE.get("key"),
        'secret': BINANCE.get("secret"),
        'nonce': lambda: str(int(time.time() * 1000)),
        'enableRateLimit': True,
    }

    store = CCXTStore(exchange='binance', currency=COIN_REFER, config=broker_config, retries=99, debug=DEBUG)
    broker_mapping = {
        'order_types': {
            bt.Order.Market: 'market',
            bt.Order.Limit: 'limit',
            bt.Order.Stop: 'stop-loss',
            bt.Order.StopLimit: 'stop limit'
        },
        'mappings': {
            'closed_order': {
                'key': 'status',
                'value': 'closed'
            },
            'canceled_order': {
                'key': 'status',
                'value': 'canceled'
            }
        }
    }

    broker = store.getbroker(broker_mapping=broker_mapping)
    cerebro.setbroker(broker)
    hist_start_date = (datetime.datetime.utcnow() + datetime.timedelta(minutes=180)) - datetime.timedelta(minutes=15*1000)
    data = store.getdata( dataname='%s/%s' % (COIN_TARGET, COIN_REFER),
        name='%s%s' % (COIN_TARGET, COIN_REFER),
        timeframe=bt.TimeFrame.Minutes,
        fromdate=hist_start_date,
        compression=15,
        ohlcv_limit=15*100000,
        drop_newest=True
    )

    #cerebro.resampledata(data, timeframe=bt.TimeFrame.Minutes, compression=5)

    # Add the feed
    cerebro.adddata(data)
    
    # Include Strategy
    
    args = [2,271,2,91,16,56,213,254,436,1616,19,53,34,101,175,345,565,1166,281]

    cerebro.addstrategy(MyStratLive,p0=args[0],p1=args[1],p2=args[2],p3=args[3],p4=args[4],p5=args[5],p6=args[6],p7=args[7],p8=args[8],p9=args[9]
                                ,p10=args[10],p11=args[11],p12=args[12],p13=args[13],p14=args[14],p15=args[15],p16=args[16],p17=args[17],p18=args[18])
    # Starting backtrader bot 
    initial_value = cerebro.broker.getvalue()
    log('Starting Portfolio Value: %.2f' % initial_value)
    result = cerebro.run()

    # Print analyzers - results
    final_value = cerebro.broker.getvalue()
    log('Final Portfolio Value: %.2f' % final_value)
    log('Profit %.3f%%' % ((final_value - initial_value) / initial_value * 100))

    if DEBUG:
        cerebro.plot()

def wob():
    try:
        main()
    except KeyboardInterrupt:
        timer = (datetime.datetime.utcnow() + datetime.timedelta(minutes=180)).strftime("%d-%m-%y %H:%M")
        log("finished : "+ str(timer))
    except Exception as err:
        log("Finished with error: "+str(err))
        raise

if __name__ == "__main__":
    wob()





