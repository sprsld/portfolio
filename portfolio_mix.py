from datetime import date
from dateutil.relativedelta import relativedelta
from tiingo import TiingoClient
import argparse
import math
import matplotlib.pyplot as plt
import statistics
import sys

TODAY = None
START_DATE = None

def calc_expected_return(prices):
    current_price = prices[-1]
    initial_price = prices[0]
    return (current_price - initial_price) / initial_price

def calc_percent_deviation(prices):
    return statistics.stdev(prices) / statistics.mean(prices)

def calc_covariance(prices_a, prices_b):
    mean_a = statistics.mean(prices_a)
    mean_b = statistics.mean(prices_b)

    sum = 0.0
    for a, b in zip(prices_a, prices_b):
        sum = sum + ((a - mean_a) * (b - mean_b))

    return sum / (len(prices_a) - 1)

def calc_correlation(prices_a, prices_b):
    stdev_a = statistics.stdev(prices_a)
    stdev_b = statistics.stdev(prices_b)

    return calc_covariance(prices_a, prices_b) / (stdev_a * stdev_b)

def calc_minimum_variance_allocation(prices_a, prices_b):
    percent_dev_a = calc_percent_deviation(prices_a)
    percent_dev_b = calc_percent_deviation(prices_b)
    var_a = math.pow(percent_dev_a, 2)
    var_b = math.pow(percent_dev_b, 2)
    correlation_ab = calc_correlation(prices_a, prices_b)

    numerator = var_b - (correlation_ab * percent_dev_a * percent_dev_b)
    denominator = var_a + var_b - (2 * correlation_ab * percent_dev_a * percent_dev_b)

    percent_a = numerator / denominator
    if percent_a > 1.0:
        percent_a = 1.0
    elif percent_a < 0.0:
        percent_a = 0.0

    percent_b = 1 - percent_a

    return (percent_a, percent_b)

def calc_portfolio_variance(percent_a, prices_a, percent_b, prices_b, correlation_ab):
    stdev_a = calc_percent_deviation(prices_a)
    stdev_b = calc_percent_deviation(prices_b)
    var_a = math.pow(stdev_a, 2)
    var_b = math.pow(stdev_b, 2)

    return (math.pow(percent_a, 2) * var_a) + (math.pow(percent_b, 2) * var_b) + (2 * percent_a * percent_b * correlation_ab * stdev_a * stdev_b)

def calc_portfolio_expected_return(percent_a, prices_a, percent_b, prices_b):
    er_a = calc_expected_return(prices_a)
    er_b = calc_expected_return(prices_b)

    return percent_a * er_a + percent_b * er_b

def get_args():
    parser = argparse.ArgumentParser(description='Fund Tickers')
    parser.add_argument('-tickers', metavar='VTSAX VDADX', type=str, nargs=2, required=True)
    parser.add_argument('-price_history', type=int, default=6)

    return parser.parse_args()

def get_close_prices(client, ticker):
    historical_prices = client.get_ticker_price(ticker,
                                                fmt='json',
                                                startDate=START_DATE,
                                                endDate=TODAY,
                                                frequency='daily')
    return [price['close'] for price in historical_prices]


def main():
    global TODAY
    global START_DATE

    args = get_args()
    client = TiingoClient()

    TODAY = date.today()
    START_DATE = TODAY + relativedelta(months=-args.price_history)

    ticker_a = args.tickers[0]
    ticker_b = args.tickers[-1]

    prices_a = get_close_prices(client, ticker_a)
    prices_b = get_close_prices(client, ticker_b)

    if len(prices_a) != len(prices_b):
        print("WARNING! You have gone past the total lifetime of at least one of your assets."
              " This may affect model accuracy.")

    correlation_ab = calc_correlation(prices_a, prices_b)

    expected_returns = []
    standard_deviations = []
    for percent in range (0,101):
        variance = calc_portfolio_variance(percent, prices_a, (100-percent), prices_b, correlation_ab)
        stdev = math.sqrt(variance)

        expected_ret = calc_portfolio_expected_return(percent, prices_a, (100-percent), prices_b)

        standard_deviations.append(stdev)
        expected_returns.append(expected_ret)

    plt.title(f"Return vs. Risk\n{int(args.price_history/12)} year model")
    plt.plot(standard_deviations, expected_returns, 'b')
    plt.ylabel('Expected Return (%)')
    plt.xlabel('Standard Deviation (%)')

    # Plot Minimum Variance
    percent_a, percent_b = calc_minimum_variance_allocation(prices_a, prices_b)
    min_var_er = calc_portfolio_expected_return(percent_a * 100, prices_a, percent_b * 100, prices_b)
    min_var_stdev = math.sqrt(calc_portfolio_variance(percent_a * 100, prices_a, percent_b * 100, prices_b, correlation_ab))

    percent_a_label = int(math.ceil(percent_a * 100))
    percent_b_label = int(math.floor(percent_b * 100))
    min_var_label = "{} {}%, {} {}%".format(ticker_a, percent_a_label, ticker_b, percent_b_label)
    plt.plot(min_var_stdev, min_var_er, 'ro-')
    plt.annotate(min_var_label, (min_var_stdev, min_var_er))

    plt.show()

if __name__ == "__main__":
    main()
