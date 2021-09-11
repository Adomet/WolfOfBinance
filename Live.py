from multiprocessing import log_to_stderr
from backtrader.dataseries import TimeFrame
from gtts import gTTS
from ccxtbt import CCXTStore
from config import BINANCE, ENV, PRODUCTION, COIN_TARGET, COIN_REFER, DEBUG
import os, playsound, time, backtrader as bt, datetime

### Text To Speach Stuff ###
Buytest    = "Buy " + COIN_TARGET
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



### Trade Strategy ###
class MyStratLive(bt.Strategy):
    params=(('p0',0),('p1',0),('p2',0),('p3',0),('p4',0),('p5',0),('p6',0),('p7',0),('p8',0),('p9',0))
    def __init__(self):

        self.rsi                  =  bt.ind.RelativeStrengthIndex(self.data, period=int(self.params.p0/10))
        self.rsi_high             =  self.params.p1
        self.rsi_low              =  self.params.p2
        
        self.tdnine               =  TD9()
        self.td9_high             =  self.params.p3
        self.td9_low              =  self.params.p4

        self.diff_ema             =  bt.ind.TripleExponentialMovingAverage(period=self.params.p5)
        self.avgselldiffactor     =  self.params.p6
        self.avgbuydiffactor      =  self.params.p7
        self.diff_ema_heigh       =  self.diff_ema + (self.diff_ema / self.avgselldiffactor * 10) 
        self.diff_ema_low         =  self.diff_ema - (self.diff_ema / self.avgbuydiffactor  * 10)           

        self.stop_loss            =  self.params.p8
        self.RiskReward           =  self.params.p9
        self.takeprofit           =  self.stop_loss * self.RiskReward / 100

        self.buyprice             =  -1
        self.isBull               =  False
        self.ordered              =  False


    def notify_data(self, data, status, *args, **kwargs):
        dn = data._name
        dt = datetime.datetime.now()
        msg= 'Data Status: {}'.format(data._getstatusname(status))
        log(str(dt)+" "+str(dn)+" "+str(msg))
        if data._getstatusname(status) == 'LIVE':
            self.live_data = True
        else:
            self.live_data = False

    def orderer(self, isbuy):
        if(self.ordered):
            return
            
        if(isbuy):
            cash,value = self.broker.get_wallet_balance(COIN_REFER)
            size = int(cash-1) / self.data.close[0]
            log("Buy state")
            if(self.live_data and cash > 11.0):
                self.order=self.buy(size=size)
                self.buyprice = self.data.close[0]
                speak(Buytest)
                log("Buyed pos at:"+str(self.data.close[0]))
        else:
            coin,val = self.broker.get_wallet_balance(COIN_TARGET)
            log("Sell state")
            if(self.live_data and (coin * self.data.close[0]) > 11.0):
                self.order=self.sell(size = coin)
                self.buyprice = -1
                speak(Selltext)
                log("Closed pos at:"+str(self.data.close[0]))

    def next(self):
        self.ordered = False
        isStop       = (self.data.close[0] < self.buyprice - (self.buyprice * self.stop_loss/1000))
        isTakeProfit = (self.data.close[0] > self.buyprice + (self.buyprice * self.takeprofit/1000))

        td9selltrigger     = self.tdnine        >=  self.td9_high
        td9buytrigger      = self.tdnine        <= -self.td9_low
        rsiselltrigger     = self.rsi           >=  self.rsi_high 
        rsibuytrigger      = self.rsi           <=  self.rsi_low
        avgdiffselltrigger = self.data.close[0] >= self.diff_ema_heigh
        avgdiffbuytrigger  = self.data.close[0] <= self.diff_ema_low


        if self.live_data:
            cash,value = self.broker.get_wallet_balance(COIN_REFER)
        else:
            cash = 'NA'

        for data in self.datas:
            log('{} - {} | Cash {} | O: {} H: {} L: {} C: {} V:{} EMA:{}'.format(data.datetime.datetime()+datetime.timedelta(minutes=195),
                data._name, cash, data.open[0], data.high[0], data.low[0], data.close[0], data.volume[0],
                self.diff_ema[0]))
            

        #print("pos:"+str(self.position.size))

        if((td9buytrigger and rsibuytrigger and avgdiffbuytrigger)):
            log("IND BUY")
            self.orderer(True)
        elif((td9selltrigger  and rsiselltrigger and avgdiffselltrigger)):
            log("IND SELL")
            self.orderer(False)
        elif(isStop):
            log("STOPPED")
            self.orderer(False)
        elif(isTakeProfit and self.buyprice != -1):
            log("TAKE PROFIT")
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
    hist_start_date = datetime.datetime.utcnow() - datetime.timedelta(minutes=15*1000)
    data = store.getdata( dataname='%s/%s' % (COIN_TARGET, COIN_REFER),
        name='%s%s' % (COIN_TARGET, COIN_REFER),
        timeframe=bt.TimeFrame.Minutes,
        fromdate=hist_start_date,
        compression=15,
        ohlcv_limit=100000000,
        drop_newest=True
    )

    #cerebro.resampledata(data, timeframe=bt.TimeFrame.Minutes, compression=15)

    # Add the feed
    cerebro.adddata(data)
    
    # Include Strategy
    #cerebro.addstrategy(MyStratLive, 356, 454, 190, 79, 187, 178, 192, 13, -37)
    args = [180,65,35,9,2,304,185,226,95,256]
    cerebro.addstrategy(MyStratLive,p0=args[0],p1=args[1],p2=args[2],p3=args[3],p4=args[4],p5=args[5],p6=args[6],p7=args[7],p8=args[8],p9=args[9])
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
        timer = datetime.datetime.now().strftime("%d-%m-%y %H:%M")
        log("finished : "+ str(timer))
    except Exception as err:
        log("Finished with error: "+str(err))
        raise

if __name__ == "__main__":
    wob()





