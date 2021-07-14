from binance.client import Client
from config import BINANCE, ENV, PRODUCTION, COIN_TARGET, COIN_REFER, DEBUG
import csv,datetime,os



def get_Date_Data(fromdate,todate,reGet):
    client = Client(BINANCE.get("key"),BINANCE.get("secret"))
    path = str(fromdate)+"="+str(todate)+".csv"
    if(os.path.exists(path) and not reGet):
        return

    csvfile = open(path, 'w', newline='') 
    candlestick_writer = csv.writer(csvfile, delimiter=',')
    
    print("Getting Data of: "+ str(fromdate)+" ---->> "+str(todate))
    
    ### for known time periods###
    #candlesticks = client.get_historical_klines(COIN_TARGET + COIN_REFER, Client.KLINE_INTERVAL_1MINUTE, "01 March, 2021", "30 May, 2021")
    
    candlesticks = client.get_historical_klines(COIN_TARGET + COIN_REFER, Client.KLINE_INTERVAL_1MINUTE, str(fromdate), str(todate))
    
    
    for candlestick in  candlesticks:
        candlestick[0] = candlestick[0] / 1000
        timestamp = candlestick[0]
        dt_object = datetime.datetime.fromtimestamp(timestamp)
        candlestick[0] = str(dt_object)
        candlestick_writer.writerow(candlestick)
    
    csvfile.close()
    return path


def get_Data(fromdate,todate):
    client = Client(BINANCE.get("key"),BINANCE.get("secret"))
    csvpath = "data.csv"

    csvfile = open(csvpath, 'w', newline='') 
    candlestick_writer = csv.writer(csvfile, delimiter=',')
    
    print("Getting Data of: "+ str(fromdate)+" ---->> "+str(todate))
    
    ### for known time periods###
    #candlesticks = client.get_historical_klines(COIN_TARGET + COIN_REFER, Client.KLINE_INTERVAL_1MINUTE, "01 March, 2021", "30 May, 2021")
    
    candlesticks = client.get_historical_klines(COIN_TARGET + COIN_REFER, Client.KLINE_INTERVAL_1MINUTE, str(fromdate), str(todate))
    
    for candlestick in  candlesticks:
        candlestick[0] = candlestick[0] / 1000
        timestamp = candlestick[0]
        dt_object = datetime.datetime.fromtimestamp(timestamp)
        candlestick[0] = str(dt_object)
        candlestick_writer.writerow(candlestick)
    
    csvfile.close()
    return csvpath