import backtrader
from backtester import *


### value list to compare different strats ###
val_list = list()

def writeUpdatedParams(params):
    strg = ""
    for i in range(0,len(params)):
        strg+= str(params[i]) + ("" if i == (len(params)-1) else ",")
    with open('params.txt', 'w') as f:
        f.write(strg)


def Update(args,data):
    strat = MyStratV2
    lst = optimizeStrat(strat,args,20,data)
    if(lst != args):
        print("New Optimium!")
        print(lst)
        writeUpdatedParams(lst)

def loop():
    args = [356, 454, 190, 79, 187, 178, 192, 13, -37]
    data = initData(15,0,True)
    Update(args,data)


if __name__ == "__main__":
    while(True):
        loop()


    

