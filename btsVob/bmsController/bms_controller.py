#coding: utf-8
import codecs
import os
import sys
import getopt
import json

import numpy as np
import pandas as pd
from pandas import Series, DataFrame
from six import exec_, print_, StringIO, iteritems

from ..bmsUtils import dummy_func
from ..bmsUtils import Date
from ..bmsUtils import TradingParams
from ..bmsData import LocalDataProxy
from ..bmsStrategy import StrategyExecutor
from ..bmsScheduler import scheduler
from . import api

class BtsController(object):
    """
    Bts控制类
    外层入口函数调用控制类解析参数
    """
    def __init__(self):
        """Bts控制类，主函数需要通过控制类作为回测入口"""
        self.databundlepath = 'btsVob/bmsData/.data/'
        self.strategyfile = None
        self.outputfile = None
        self.start_time = None
        self.end_time = None
        self.plot = False
        self.progress = True
        self.frequency = '1m'

    def useage(self):
        print('python btsMain [option][value]...')
        print('-h or --help for detail')
        print('-v or --verbose set option to hide info')
        print('-d or --data-bundle-path for update data need assign a data path')
        print('-f or --strategy-file')
        print('-s or --start-date')
        print('-e or --end-date')
        print('-o or --output-file')
        print('-r or --frequency')
        print('--plot/--no-plot whether need draw graphic')
        print('--progress/--no-progress whether need display progress bar')
    
    def process_command(self, args):
        """处理参数 
        :rags: 主程序的参数列表
        """
        #参数的短格式
        par_str = 'hvd:f:s:e:o:r:'
        #参数的长格式
        par_list = ['help',
                    'verbose',
                    'data-bundle-path=',
                    'strategy-file=',
                    'start-date=',
                    'end-date=',
                    'output-file',
                    'frequency',
                    'plot',
                    'no-plot',
                    'progress',
                    'no-progress']
        try:
            options,args = getopt.getopt(args, par_str, par_list)
            print('euxyacg')
            print(options)
            for name,value in options:
                if name in ('-h', '--help'):
                    self.useage()
                elif name in ('-d', '--data-bundle-path'):
                    self.databundlepath = value
                elif name in ('-f', '--strategy-file'):
                    self.strategyfile = value
                elif name in ('-o', '--output-file'):
                    self.outputfile = value
                elif name in ('-s', '--start-date'):
                    self.start_time = value
                elif name in ('-e', '--end-date'):
                    self.end_time = value
                elif name in ('-r','--frequency'):
                    self.frequency = value
                elif name in ('--plot'):
                    self.plot = True 
                elif name in ('--no-plot'):
                    self.plot = False
                elif name in ('--progress'):
                    self.progress = True
                elif name in ('--no-progress'):
                    self.progress = False
            self.work(self.strategyfile, self.start_time, self.end_time, self.outputfile, self.plot, self.databundlepath, 1000000, self.progress, self.frequency)

        except getopt.GetoptError:
            self.useage()

    def work(self, strategy_file, start_date, end_date, output_file, plot, data_bundle_path, init_cash, progress, frequency): 
        """控制类的工作函数调用策略运行函数
        :strategy_file:策略文件
        :start_date:回测开始时间
        :end_date:回测结束时间
        :output_file:输出文件
        :plot:是否画图标记
        :data_bundle_path:数据文件路径
        :init_cash:初始资金
        :progress:是否显示进度条
        :frequency:回测数据频率
        """
        with codecs.open(strategy_file, encoding="utf-8") as f:
            source_code = f.read()

        results_df = self.run_strategy(source_code, strategy_file, start_date, end_date,
                                  init_cash, data_bundle_path, progress, frequency)

        if output_file is not None:
            results_df.to_pickle(output_file)

        if plot:
            self.show_draw_result(strategy_file, results_df)
    
    def show_draw_result(self, title, results_df):
        """绘图函数"""
        import matplotlib
        from matplotlib import gridspec
        import matplotlib.image as mpimg
        import matplotlib.pyplot as plt
        plt.style.use('ggplot')

        red = "#aa4643"
        blue = "#4572a7"
        black = "#000000"

        figsize = (18, 6)
        f = plt.figure(title, figsize=figsize)
        gs = gridspec.GridSpec(10, 8)

        # draw logo
        ax = plt.subplot(gs[:3, -1:])
        ax.axis("off")
        filename = os.path.join(os.path.dirname(os.path.realpath(__file__)), "resource")
        filename = os.path.join(filename, "ricequant-logo.png")
        img = mpimg.imread(filename)
        imgplot = ax.imshow(img, interpolation="nearest")
        ax.autoscale_view()

        # draw risk and portfolio
        series = results_df.iloc[-1]

        font_size = 12
        value_font_size = 11
        label_height, value_height = 0.8, 0.6
        label_height2, value_height2 = 0.35, 0.15

        fig_data = [
            (0.00, label_height, value_height, "Total Returns", "{0:.3%}".format(series.total_returns), red, black),
            (0.15, label_height, value_height, "Annual Returns", "{0:.3%}".format(series.annualized_returns), red, black),

            (0.30, label_height, value_height, "Sharpe", "{0:.4}".format(series.sharpe), black, black),
            (0.45, label_height, value_height, "Sortino", "{0:.4}".format(series.sortino), black, black),

            (0.00, label_height2, value_height2, "Volatility", "{0:.4}".format(series.volatility), black, black),
            (0.15, label_height2, value_height2, "MaxDrawdown", "{0:.3%}".format(series.max_drawdown), black, black),
            (0.30, label_height2, value_height2, "Downside Risk", "{0:.4}".format(series.downside_risk), black, black),
        ]

        ax = plt.subplot(gs[:3, :-1])
        ax.axis("off")
        for x, y1, y2, label, value, label_color, value_color in fig_data:
            ax.text(x, y1, label, color=label_color, fontsize=font_size)
            ax.text(x, y2, value, color=value_color, fontsize=value_font_size)

        # strategy
        ax = plt.subplot(gs[4:, :])

        ax.get_xaxis().set_minor_locator(matplotlib.ticker.AutoMinorLocator())
        ax.get_yaxis().set_minor_locator(matplotlib.ticker.AutoMinorLocator())
        ax.grid(b=True, which='minor', linewidth=.2)
        ax.grid(b=True, which='major', linewidth=1)

        ax.plot(results_df["total_returns"], label="strategy", alpha=1, linewidth=2, color=red)

        # manipulate
        vals = ax.get_yticks()
        ax.set_yticklabels(['{:3.2f}%'.format(x*100) for x in vals])

        leg = plt.legend(loc="upper left")
        leg.get_frame().set_alpha(0.5)

        plt.show()

    def run_strategy(self, source_code, strategy_filename, start_date, end_date,
                     init_cash, data_bundle_path, show_progress, frequency):
        """运行策略类
        """
        start_date = Date(start_date).convert().to_datetime()
        end_date = Date(end_date).convert().to_datetime()
        scope = {}
        scope.update({export_name: getattr(api, export_name) for export_name in api.__all__})
        code = compile(source_code, strategy_filename, 'exec')
        exec_(code, scope)

        try:
            data_proxy = LocalDataProxy(data_bundle_path)
        except OSError as e:
            if e.errno == errno.EEXIST:
                print_("data bundle might crash. Run `%s update_bundle` to redownload data bundle." % sys.argv[0])
                sys.exit()

        trading_cal = data_proxy.get_trading_dates(start_date, end_date)
        scheduler.set_trading_dates(data_proxy.get_trading_dates(start_date, end_date))
        trading_params = TradingParams(trading_cal, start_date=start_date, end_date=end_date,
                                       frequency=frequency, init_cash=init_cash,
                                       show_progress=show_progress)

        executor = StrategyExecutor(
            init=scope.get("init", dummy_func),
            before_trading=scope.get("before_trading", dummy_func),
            handle_bar=scope.get("handle_bar", dummy_func),

            trading_params=trading_params,
            data_proxy=data_proxy,
        )

        results_df = executor.execute()

        return results_df

"""Test Code"""
def main():
    bc = BtsController()
    bc.process_command(sys.argv[1:])

if __name__ == '__main__':
    main()

