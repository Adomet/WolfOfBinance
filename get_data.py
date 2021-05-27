import config, csv
from binance.client import Client
from config import BINANCE, ENV, PRODUCTION, COIN_TARGET, COIN_REFER, DEBUG


client = Client(BINANCE.get("key"),BINANCE.get("secret"))

# prices = client.get_all_tickers()

# for price in prices:
#     print(price)

csvfile = open('data.csv', 'w', newline='') 
candlestick_writer = csv.writer(csvfile, delimiter=',')

candlesticks = client.get_historical_klines(COIN_TARGET + COIN_REFER, Client.KLINE_INTERVAL_1MINUTE, "01 January, 2021", "30 May, 2021")

for candlestick in  candlesticks:
    candlestick[0] = candlestick[0] / 1000
    candlestick_writer.writerow(candlestick)

csvfile.close()