# 可以自己import我们平台支持的第三方python模块，比如pandas、numpy等。
import talib
import numpy as np
import math
import pandas
def init(context):
    context.OBSERVATION = 20 

def handle_bar(context, bar_dict):
    prices = history(context.OBSERVATION, '1m', 'close')['rb1610'].values    
    print(sum(prices) / 20.0)
    print(prices[-1])
    if prices[-1] > (sum(prices) / 20.0):
        order_shares('rb1610', 1, 'long', 'open')
    else:
        order_shares('rb1610', 1, 'short', 'close')
        
