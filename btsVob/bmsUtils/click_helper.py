#coding: utf-8

import pandas as pd

class Date():
    def __init__(self, value):
        self.date = value

    def convert(self):
        return pd.Timestamp(self.date)

