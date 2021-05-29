from binance.client import Client
from config import BINANCE, ENV, PRODUCTION, COIN_TARGET, COIN_REFER, DEBUG
import csv,datetime,os

client = Client(BINANCE.get("key"),BINANCE.get("secret"))

def get_Date_Data(fromdate,todate):
    path = str(fromdate)+"="+str(todate)+".csv"
    if(os.path.exists(path)):
        return

    csvfile = open(path, 'w', newline='') 
    candlestick_writer = csv.writer(csvfile, delimiter=',')
    
    print("Getting Data of: "+ str(fromdate)+" ---->> "+str(todate))
    
    ### for known time periods###
    #candlesticks = client.get_historical_klines(COIN_TARGET + COIN_REFER, Client.KLINE_INTERVAL_1MINUTE, "01 March, 2021", "30 May, 2021")
    
    candlesticks = client.get_historical_klines(COIN_TARGET + COIN_REFER, Client.KLINE_INTERVAL_1MINUTE, str(fromdate), str(todate))
    
    
    for candlestick in  candlesticks:
        candlestick[0] = candlestick[0] / 1000
        candlestick_writer.writerow(candlestick)
    
    csvfile.close()


def get_Data():
    ### month ago ###
    today = datetime.date.today()
    first = today.replace(day=1)
    fromdate = first - datetime.timedelta(days=1)
    fromdate = fromdate.today()
    todate = today

    path = str(fromdate)+"="+str(todate)+".csv"
    if(os.path.exists(path)):
        return

    csvfile = open(path, 'w', newline='') 
    candlestick_writer = csv.writer(csvfile, delimiter=',')
    
    print("Getting Data of: "+ str(fromdate)+" ---->> "+str(todate))

    ### for known time periods###
    #candlesticks = client.get_historical_klines(COIN_TARGET + COIN_REFER, Client.KLINE_INTERVAL_1MINUTE, "01 March, 2021", "30 May, 2021")

    candlesticks = client.get_historical_klines(COIN_TARGET + COIN_REFER, Client.KLINE_INTERVAL_1MINUTE, str(fromdate), str(todate))

    for candlestick in  candlesticks:
        candlestick[0] = candlestick[0] / 1000
        candlestick_writer.writerow(candlestick)

    csvfile.close()