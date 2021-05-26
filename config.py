import os

PRODUCTION = "production"
DEVELOPMENT = "development"

COIN_TARGET = "BNB"
COIN_REFER = "USDT"

ENV = PRODUCTION #os.getenv("ENVIRONMENT", DEVELOPMENT)
DEBUG = False

BINANCE = {
  "key": "Your API Key",
  "secret": "Your API Secret"
}

print("ENV = ", ENV)