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


### Trade Strategy ###
class MyStratV2(bt.Strategy):
    def __init__(self,p0,p1,p2,p3,p4,p5,p6,p7,p8):
        self.trend_slow_ema       =  bt.ind.SMA(period=p0)
        self.trend_fast_ema       =  bt.ind.EMA(period=p1)
        self.diff_ema             =  bt.ind.EMA(period=p2)
        self.bullavgselldiffactor =  p3
        self.bullavgbuydiffactor  =  p4
        self.bearavgselldiffactor =  p5
        self.bearavgbuydiffactor  =  p6
        self.stop_loss            =  p7
        self.loss_treshold        =  p8

        self.buyprice             =  -1
        self.isBull               =  False
        self.ordered              =  False

    def updateParams(self,newparams):
        self.trend_slow_ema.p.period = newparams[0]
        self.trend_fast_ema.p.period = newparams[1]
        self.diff_ema.p.period       = newparams[2]
        self.bullavgselldiffactor    = newparams[3]
        self.bullavgbuydiffactor     = newparams[4]
        self.bearavgselldiffactor    = newparams[5]
        self.bearavgbuydiffactor     = newparams[6]
        self.stop_loss               = newparams[7]
        self.loss_treshold           = newparams[8]
    
    def getOldParams(self):
        return[self.trend_slow_ema.p.period ,
               self.trend_fast_ema.p.period ,
               self.diff_ema.p.period       ,
               self.bullavgselldiffactor    ,
               self.bullavgbuydiffactor     ,
               self.bearavgselldiffactor    ,
               self.bearavgbuydiffactor     ,
               self.stop_loss               ,
               self.loss_treshold           ]


    def getParams(self):
        with open('params.txt') as f:
            line = f.readline()
        newparams = line.split(',')
        newparams = [int(i) for i in newparams]
        oldparams = self.getOldParams()

        if(newparams != oldparams):
            self.updateParams(newparams)
            log("New Params")
            log(self.getOldParams())



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
        avgdiff      = (self.data - self.diff_ema)
        tmp          = (self.trend_fast_ema > self.trend_slow_ema)
        isTrendSame  = (tmp==self.isBull)
        isSellable   = (self.data.close[0] > self.buyprice - (self.buyprice * self.loss_treshold/1000))
        isStop       = (self.data.close[0] < self.buyprice - (self.buyprice * self.stop_loss/1000))
        isProfitStop = (self.data.close[0] > self.buyprice - self.buyprice  * self.stop_loss*1.5/1000 and isSellable)
        self.ordered =False


        if self.live_data:
            cash,value = self.broker.get_wallet_balance(COIN_REFER)
        else:
            cash = 'NA'

        for data in self.datas:
            log('{} - {} | Cash {} | O: {} H: {} L: {} C: {} V:{} EMA:{}'.format(data.datetime.datetime()+datetime.timedelta(minutes=180),
                data._name, cash, data.open[0], data.high[0], data.low[0], data.close[0], data.volume[0],
                self.diff_ema[0]))

        #print("pos:"+str(self.position.size))

        if self.isBull != tmp:
            msg = "Switched: "+(" Bull" if tmp else " Bear")+" at: "+str(self.data.close[0])
            speak(msg)
            log(msg)


        if (self.isBull and not isTrendSame and isSellable):
            self.orderer(False)
        
        if (not self.isBull and not isTrendSame):
            self.orderer(True)


        self.isBull = tmp

        if (self.isBull):
            if avgdiff < -self.diff_ema*10/self.bullavgbuydiffactor:
                self.orderer(True)

            if avgdiff > self.diff_ema*10/self.bullavgselldiffactor and isSellable:
                self.orderer(False)
        else:
            if avgdiff < -self.diff_ema*10/self.bearavgbuydiffactor:
                self.orderer(True)

            if avgdiff > self.diff_ema*10/self.bearavgselldiffactor and isSellable:
                self.orderer(False)

        if (isStop):
            self.orderer(False)
        
        if(self.live_data):
            self.getParams()



def main():
    cerebro = bt.Cerebro(quicknotify=True)

    broker_config = {
        'apiKey': BINANCE.get("key"),
        'secret': BINANCE.get("secret"),
        'nonce': lambda: str(int(time.time() * 1000)),
        'enableRateLimit': True,
    }

    store = CCXTStore(exchange='binance', currency=COIN_REFER, config=broker_config, retries=5, debug=DEBUG)
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
    hist_start_date = datetime.datetime.utcnow() - datetime.timedelta(minutes=1000)
    data = store.getdata( dataname='%s/%s' % (COIN_TARGET, COIN_REFER),
        name='%s%s' % (COIN_TARGET, COIN_REFER),
        timeframe=bt.TimeFrame.Minutes,
        fromdate=hist_start_date,
        compression=1,
        ohlcv_limit=100000000,
        drop_newest=True
    )

    # Add the feed
    cerebro.adddata(data)
    
    # Include Strategy
    cerebro.addstrategy(MyStratV2, 356, 454, 190, 79, 187, 178, 192, 13, -37) 
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





