from binance.client import Client
from config import BINANCE, ENV, PRODUCTION, COIN_TARGET, COIN_REFER, DEBUG
import csv,datetime,os



def get_Date_Data(fromdate,todate,timeframe,target,reGet):
    client = Client(BINANCE.get("key"),BINANCE.get("secret"))
    path = "data/"+target+"-"+COIN_REFER+"_"+timeframe+"_"+str(fromdate)+"="+str(todate)+".csv"
    if(os.path.exists(path) and not reGet):
        return path

    csvfile = open(path, 'w', newline='') 
    candlestick_writer = csv.writer(csvfile, delimiter=',')
    
    print("Getting Data of: "+ path)
    
    candlesticks = client.get_historical_klines(target + COIN_REFER, timeframe, str(fromdate), str(todate))
    
    
    for candlestick in  candlesticks:
        candlestick[0] = candlestick[0] / 1000
        timestamp = candlestick[0]
        dt_object = datetime.datetime.fromtimestamp(timestamp)
        candlestick[0] = str(dt_object)
        candlestick_writer.writerow(candlestick)
    
    csvfile.close()
    return path
