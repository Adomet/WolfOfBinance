import backtrader as bt
from indicators import EWO
from Debug import log

class SMAOffsetV1(bt.Strategy):
    params = (
        # Parameters index mapping:
        # 0: base_nb_candles_buy
        # 1: base_nb_candles_sell
        # 2: low_offset (multiplied by 1000)
        # 3: high_offset (multiplied by 1000)
        # 4: ewo_low (multiplied by 1000) - POSITIVE value, will be negated in logic
        # 5: ewo_high (multiplied by 1000)
        # 6: rsi_buy_threshold
        # 7: fast_ewo
        # 8: slow_ewo
        # 9: stoploss (multiplied by 1000) - POSITIVE value, will be negated in logic
        # 10-12: unused
        
        ('p0', 13),      # base_nb_candles_buy
        ('p1', 18),      # base_nb_candles_sell
        ('p2', 978),     # low_offset (0.978 * 1000)
        ('p3', 1012),    # high_offset (1.012 * 1000)
        ('p4', 19909),   # ewo_low (19.909 * 1000, stored as positive)
        ('p5', 5835),    # ewo_high (5.835 * 1000)
        ('p6', 55),      # rsi_buy_threshold
        ('p7', 50),      # fast_ewo
        ('p8', 200),     # slow_ewo
        ('p9', 150),     # stoploss (0.15 * 1000, stored as positive)
        ('p10', 0),      # unused
        ('p11', 0),      # unused
        ('p12', 0),      # unused
    )

    def __init__(self):
        self.plot = True
        
        # Ensure parameters are valid
        self.params.p0 = max(self.params.p0, 1)
        self.params.p1 = max(self.params.p1, 1)
        self.params.p7 = max(self.params.p7, 1)
        self.params.p8 = max(self.params.p8, 1)
        
        # Convert integer parameters to decimal values
        self.low_offset = self.params.p2 / 1000.0
        self.high_offset = self.params.p3 / 1000.0
        self.ewo_low = -self.params.p4 / 1000.0  # Negate for logic - store as negative
        self.ewo_high = self.params.p5 / 1000.0
        self.stoploss = -self.params.p9 / 1000.0  # Negate for logic - store as negative
        
        # Indicators
        self.ema_buy = bt.ind.EMA(period=self.params.p0)
        self.ema_sell = bt.ind.EMA(period=self.params.p1)
        self.rsi = bt.ind.RSI(period=14)
        
        # EWO: ((EMA(fast) - EMA(slow)) / close) * 100
        self.ema_fast = bt.ind.EMA(period=self.params.p7)
        self.ema_slow = bt.ind.EMA(period=self.params.p8)
        self.ewo = ((self.ema_fast - self.ema_slow) / self.data.close) * 100
        
        # Keep track of entry price for stoploss
        self.order = None
        self.entry_price = None
        
        # Protection settings
        self.cooldown_counter = 0
        self.low_profit_pairs = {}
        
        # State variables
        self.buyprice = -1
        self.ordered = False
        self.isbuyready = False
        self.posCandleCount = 0
        self.buysize = 0

    def orderer(self, isbuy, reason=""):
        if self.ordered: return
        self.ordered = True
        
        # Collect indicator values
        candle_index = len(self)
        close_price = self.data.close[0]
        ema_buy_value = self.ema_buy[0]
        ema_sell_value = self.ema_sell[0]
        ewo_value = self.ewo[0]
        rsi_value = self.rsi[0]
        
        if isbuy and self.buyprice == -1:
            self.buyprice = close_price
            self.buysize = int(self.broker.get_cash()*99/100) / close_price
            self.buy(size=self.buysize)
            log(f"C{candle_index} | C:{close_price:.2f} | EMA_BUY:{ema_buy_value:.2f} | EMA_SELL:{ema_sell_value:.2f} | EWO:{ewo_value:.2f} | RSI:{rsi_value:.2f} | {reason}")
            
        elif not isbuy and not self.buyprice == -1:
            pnl = close_price - self.buyprice
            log(f"C{candle_index} | C:{close_price:.2f} | EMA_BUY:{ema_buy_value:.2f} | EMA_SELL:{ema_sell_value:.2f} | EWO:{ewo_value:.2f} | RSI:{rsi_value:.2f} | PnL:{pnl:.2f} | {reason}")
            self.buysize, self.buyprice = 0, -1
            self.close()

    def next(self):
        self.ordered = False
        
        # Decrement cooldown if active
        if self.cooldown_counter > 0:
            self.cooldown_counter -= 1
        
        # Collect indicator values
        close_price = self.data.close[0]
        ema_buy_value = self.ema_buy[0]
        ema_sell_value = self.ema_sell[0]
        ewo_value = self.ewo[0]
        rsi_value = self.rsi[0]
        
        # Check if we have an open position
        in_position = self.buyprice != -1
        
        # Buy conditions
        ewo_high_condition = ewo_value > self.ewo_high
        ewo_low_condition = ewo_value < self.ewo_low
        price_below_ma = close_price < (ema_buy_value * self.low_offset)
        rsi_condition = rsi_value < self.params.p6
        
        # Sell conditions
        price_above_ma = close_price > (ema_sell_value * self.high_offset)
        stoploss_hit = in_position and close_price <= self.buyprice * (1 + self.stoploss)
        
        # Apply buy logic when not in position and not in cooldown
        if not in_position and self.cooldown_counter == 0:
            # Condition 1: Price below MA with high EWO and low RSI
            if price_below_ma and ewo_high_condition and rsi_condition:
                self.isbuyready = True
                self.orderer(True, "Buy: Price below MA, High EWO, Low RSI")
            
            # Condition 2: Price below MA with low EWO
            elif price_below_ma and ewo_low_condition:
                self.isbuyready = True
                self.orderer(True, "Buy: Price below MA, Low EWO")
        
        # Apply sell logic when in position
        if in_position:
            # Update position count
            self.posCandleCount += 1
            
            # Sell if price is above MA
            if price_above_ma:
                self.orderer(False, "Sell: Price above MA")
                self.cooldown_counter = 2  # Apply cooldown period
            
            # Apply stoploss
            elif stoploss_hit:
                self.orderer(False, "Sell: Stoploss hit")
                # Track pair for low profit protection
                self.low_profit_pairs[self.data._name] = self.posCandleCount
                self.cooldown_counter = 2  # Apply cooldown period 