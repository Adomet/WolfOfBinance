from gtts import gTTS
from ccxtbt import CCXTStore
from config import BINANCE, ENV, PRODUCTION, COIN_TARGET, COIN_REFER, DEBUG
import os, playsound, time, backtrader as bt, datetime

### Text To Speach Stuff ###
Buytest    = "Buy " + COIN_TARGET
Selltext   = "Sell "+ COIN_TARGET

def speak(text):
    language = 'en'
    filename ="output.mp3"
    output = gTTS(text=text, lang = language,slow=True)
    output.save(filename)
    playsound.playsound(filename)
    os.remove(filename)


### Trade Strategy ###
class MyStratV10(bt.Strategy):
    def __init__(self, dir_ema_period, ema_period, bullavgselldiffactor, bullavgbuydiffactor, bearavgselldiffactor, bearavgbuydiffactor, stop_loss, loss_treshold):
        ## SMA ##
        self.ema_period = ema_period
        self.dir_ema_period = dir_ema_period
        self.ema = bt.ind.EMA(period=self.ema_period)
        self.dir_ema =  bt.ind.EMA(period=self.dir_ema_period)
        self.loss_treshold = loss_treshold
        self.buyprice = -1
        self.stop_loss = stop_loss
        self.bullavgbuydiffactor = bullavgbuydiffactor
        self.bullavgselldiffactor = bullavgselldiffactor
        self.bearavgbuydiffactor = bearavgbuydiffactor
        self.bearavgselldiffactor = bearavgselldiffactor
        self.isBull = True
        self.order = None



    def notify_data(self, data, status, *args, **kwargs):
        dn = data._name
        dt = datetime.datetime.now()
        msg= 'Data Status: {}'.format(data._getstatusname(status))
        print(dt,dn,msg)
        if data._getstatusname(status) == 'LIVE':
            self.live_data = True
        else:
            self.live_data = False

    def orderer(self, isbuy):
        if(isbuy):
            self.buyprice = self.data.close[0]
            cash,value = self.broker.get_wallet_balance(COIN_REFER)
            size = int(cash-1) / self.data.close[0]
            print("Buy state")
            if(self.live_data and cash > 11.0):
                speak(Buytest)
                print("Buyed pos at:"+str(self.data.close[0]))
                self.order=self.buy(size=size)
        else:
            self.buyprice = -1
            coin,val = self.broker.get_wallet_balance(COIN_TARGET)
            print("Sell state")
            if(self.live_data and (coin * self.data.close[0]) > 10.0):
                speak(Selltext)
                print("Closed pos at:"+str(self.data.close[0]))
                self.order=self.sell(size = coin)

    def next(self):
        if self.live_data:
            cash,value = self.broker.get_wallet_balance(COIN_REFER)
        else:
            cash = 'NA'

        for data in self.datas:
            print('{} - {} | Cash {} | O: {} H: {} L: {} C: {} V:{} EMA:{}'.format(data.datetime.datetime()+datetime.timedelta(minutes=180),
                data._name, cash, data.open[0], data.high[0], data.low[0], data.close[0], data.volume[0],
                self.ema[0]))

        #print("pos:"+str(self.position.size))

        avgdiff = self.data - self.ema
        tmp = (self.ema > self.dir_ema)

        if self.isBull != tmp:
            msg = "Switched: "+(" Bull" if tmp else " Bear")+" at: "+str(self.data.close[0])
            speak(msg)
            print(msg)

        if(self.isBull and not (tmp==self.isBull) and self.data.close[0] > self.buyprice - (self.buyprice * self.loss_treshold/1000)):
            self.orderer(False)


        self.isBull = tmp

        if(self.isBull):
            if avgdiff < -self.ema*10/self.bullavgbuydiffactor:
                self.orderer(True)

            if avgdiff > self.ema*10/self.bullavgselldiffactor and self.data.close[0] > self.buyprice - (self.buyprice * self.loss_treshold/1000):
                self.orderer(False)
        else:
            if avgdiff < -self.ema*10/self.bearavgbuydiffactor:
                self.orderer(True)

            if avgdiff > self.ema*10/self.bearavgselldiffactor and self.data.close[0] > self.buyprice - (self.buyprice * self.loss_treshold/1000):
                self.orderer(False)

        if self.data.close[0] < self.buyprice - (self.buyprice * self.stop_loss/1000):
            self.orderer(False)


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
    cerebro.addstrategy(MyStratV10,433, 160, 149, 561, 1506, 185, 68, -15) 
    # Starting backtrader bot 
    initial_value = cerebro.broker.getvalue()
    print('Starting Portfolio Value: %.2f' % initial_value)
    result = cerebro.run()

    # Print analyzers - results
    final_value = cerebro.broker.getvalue()
    print('Final Portfolio Value: %.2f' % final_value)
    print('Profit %.3f%%' % ((final_value - initial_value) / initial_value * 100))

    if DEBUG:
        cerebro.plot()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        timer = datetime.datetime.now().strftime("%d-%m-%y %H:%M")
        print("finished : "+ str(timer))
    except Exception as err:
        print("Finished with error: ", err)
        raise





