import datetime
import random
import backtrader as bt
#from strategies.AIStrat import AIStrat, agent as ai_strat_agent
from analysis import StrategyAnalysis
from config import COIN_TARGET
import get_data as gd
import time
from binance.client import Client
from multiprocessing import Pool, cpu_count
import numpy as np
import torch as T
import matplotlib.pyplot as plt
from IPython.display import clear_output, display

from strategies.MyStratAI import MyStratAI , global_agent

def add_strategy_params_to_cerebro(cerebro, strategy, args, is_optimization=False):
    params = {f'p{i}': args[i] for i in range(len(args))}
    cerebro.optstrategy(strategy, **params) if is_optimization else cerebro.addstrategy(strategy, **params)


def setup_cerebro(strategy, args, data, StartCash=1000):
    cerebro = bt.Cerebro(maxcpus=10, optdatas=True, optreturn=False, preload=True, runonce=True)
    add_strategy_params_to_cerebro(cerebro, strategy, args)
    cerebro.broker.setcash(StartCash)
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="ta")
    cerebro.adddata(data)
    cerebro.getbroker().setcommission(commission=0.001, name=COIN_TARGET)
    return cerebro

def getRecentSlice(timeframe, target=COIN_TARGET, slice_day=100):
    print(f"testing slice: {slice_day}")
    available_days = 1666
    today = datetime.date.today()

    path = gd.get_Date_Data(today - datetime.timedelta(days=available_days),  today + datetime.timedelta(days=1), timeframe, target, False)
    slice_day_timedelta = datetime.timedelta(days=slice_day)

    from_date = today - slice_day_timedelta
    to_date = today 

    recent_data_feed = bt.feeds.GenericCSVData(name=target, dataname=path, timeframe=bt.TimeFrame.Minutes,
                                               fromdate=from_date, todate=to_date)
    return recent_data_feed

def getRandomSlice(timeframe, target=COIN_TARGET, slice_day=100):
    available_days = 1436
    today = datetime.date.today()

    path = gd.get_Date_Data(today - datetime.timedelta(days=available_days), today + datetime.timedelta(days=1), timeframe, target, False)

    slice_day_timedelta = datetime.timedelta(days=slice_day)
    random_days = random.randint(0, available_days + (-2*slice_day))
    random_timedelta = datetime.timedelta(days=random_days)
    print(f"random_days: {random_days}")

    slice_startDay = today + (-2 * slice_day_timedelta) - random_timedelta
    slice_endDay = slice_startDay + slice_day_timedelta

    slice_data = bt.feeds.GenericCSVData(name=target, dataname=path, timeframe=bt.TimeFrame.Minutes,
                                          fromdate=slice_startDay, todate=slice_endDay)
    return slice_data
    
def initData(traindays, testdays, timeframe, target=COIN_TARGET, refresh=False):
    today = datetime.date.today() - datetime.timedelta(days=testdays)
    fromdate = today - datetime.timedelta(days=traindays)
    todate = today + datetime.timedelta(days=1)
    path = gd.get_Date_Data(fromdate, todate, timeframe, target, refresh)
    data = bt.feeds.GenericCSVData(name=target, dataname=path, timeframe=bt.TimeFrame.Minutes, 
                                 fromdate=fromdate, todate=todate)
    print(f"BackTesting Data of: {path}")
    return data


## Main Training Function 
def train(data,params, episodes=100000):
    best_equity = 0.0
    max_slice = 1436
    start_slice = 1436
    slice_multiplier = 1.5
    step = 0
    episode_values = []  # List to store final values for plotting
    plt.ion() # Turn on interactive mode for matplotlib
    fig, ax = plt.subplots() # Create a figure and an axes.

    for episode in range(episodes):
        #data = getRandomSlice(Client.KLINE_INTERVAL_15MINUTE, COIN_TARGET, start_slice)
        #data = getRecentSlice(Client.KLINE_INTERVAL_15MINUTE, COIN_TARGET, start_slice)
        data = initData(start_slice, 0, Client.KLINE_INTERVAL_15MINUTE, COIN_TARGET, False)
        cerebro = setup_cerebro(MyStratAI, params, data)
        start_time = time.time()
        print(f"=============== slice: {start_slice} | episode: {episode + 1}/{episodes} =============== ")
        cerebro.run()
        final_value = cerebro.broker.getvalue()
        global_agent.learn()
        end_time = time.time()
        print(f"Episode {episode + 1}/{episodes} | Final value: {final_value} | Time: {end_time - start_time} seconds.")
        
        episode_values.append(final_value)
        ax.clear() # Clear the previous plot
        ax.plot(episode_values)
        ax.set_xlabel("Episode")
        ax.set_ylabel("Final Value")
        ax.set_title("Training Progress: Final Value per Episode")
        fig.canvas.draw() # Redraw the canvas
        fig.canvas.flush_events() # Flush the GUI events
        step += 1
        if final_value > best_equity * 0.9 and final_value > 1000 and step > 10:
            start_slice = int(min(max_slice, start_slice * slice_multiplier))
            step = 0
            best_equity = final_value
            global_agent.save_models()
            print(f"Best pnl: {final_value} | New Slice: {start_slice}")
    plt.ioff() # Turn off interactive mode
    plt.show() # Show the final plot
    return global_agent


## Main Training Function 
def train_test(data,params, episodes=100000):
    best_test_value = 0.0
    best_equity = 0.0
    max_slice = 333
    start_slice = 20
    slice_multiplier = 1.5
    step = 0
    episode_values = []  # List to store final values for plotting
    test_episode_values = [] # List to store test values for plotting
    test_episode_numbers = [] # List to store episode numbers for test values
    plt.ion() # Turn on interactive mode for matplotlib
    fig, ax = plt.subplots() # Create a figure and an axes.

    for episode in range(episodes):
        data = getRandomSlice(Client.KLINE_INTERVAL_15MINUTE, COIN_TARGET, start_slice)
        #data = getRecentSlice(Client.KLINE_INTERVAL_15MINUTE, COIN_TARGET, start_slice)
        #data = initData(start_slice, 0, Client.KLINE_INTERVAL_15MINUTE, COIN_TARGET, False)
        cerebro = setup_cerebro(MyStratAI, params, data)
        start_time = time.time()
        print(f"=============== slice: {start_slice} | episode: {episode + 1}/{episodes} =============== ")
        cerebro.run()
        final_value = cerebro.broker.getvalue()

        global_agent.learn()
            
        end_time = time.time()
        print(f"Episode {episode + 1}/{episodes} | Final value: {final_value} | Time: {end_time - start_time} seconds.")
        
        episode_values.append(final_value)
        ax.clear() # Clear the previous plot
        ax.plot(episode_values, label="Training Value")
        if test_episode_numbers: # Plot test values if available
            ax.plot(test_episode_numbers, test_episode_values, label="Test Value", marker='o', linestyle='--')
        ax.set_xlabel("Episode")
        ax.set_ylabel("Final Value")
        ax.set_title("Training Progress: Final Value per Episode")
        ax.legend() # Add a legend
        fig.canvas.draw() # Redraw the canvas
        fig.canvas.flush_events() # Flush the GUI events

        step += 1
        if final_value > best_equity * 0.9 and final_value > 1000 and step > 2:
            start_slice = int(min(max_slice, start_slice * slice_multiplier))
            step = 0
            best_equity = final_value
            print(f"Best pnl: {final_value} | New Slice: {start_slice}")
        
        #test
        if episode % 10 == 0:
            global_agent.eval()
            data = initData(400, 1436, Client.KLINE_INTERVAL_15MINUTE, COIN_TARGET, False)
            cerebro = setup_cerebro(MyStratAI, params, data)
            cerebro.run()
            test_value = cerebro.broker.getvalue()
            print(f"Test value: {test_value}")
            test_episode_values.append(test_value)
            test_episode_numbers.append(episode) # Store current episode number
            global_agent.memory.clear_memory()
            if(test_value > best_test_value):
                best_test_value = test_value
                print(f"Best test value: {best_test_value}")
                global_agent.save_models()
            global_agent.train()

            
    plt.ioff() # Turn off interactive mode
    plt.show() # Show the final plot
    return global_agent