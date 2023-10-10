from pandas.core.api import DataFrame
from toolkit.logger import Logger
from omspy_brokers.bypass import Bypass
from constants import dir_path, secs
from time import sleep
import traceback
import pandas as pd
import pendulum

logging = Logger(10)

FM = pendulum.now().subtract(days=300).to_datetime_string()
df_sym = pd.read_csv("./ind_niftysmallcap250list.csv")


def get_kite():
    try:
        enctoken = None
        fpath = dir_path + 'bypass.yaml'
        dct = fils.get_lst_fm_yml(fpath)
        tokpath = dir_path + dct['userid'] + '.txt'
        if not fils.is_file_not_2day(tokpath):
            with open(tokpath, 'r') as tf:
                enctoken = tf.read()
        print(f'{tokpath=} has {enctoken=}')
        bypass = Bypass(dct['userid'],
                        dct['password'],
                        dct['totp'],
                        tokpath,
                        enctoken)
        bypass.authenticate()
    except Exception as e:
        logging.error(f"unable to create bypass object  {e}")
    else:
        return bypass


broker = get_kite()


def update_df_with_ltp(df_sym: DataFrame, lst_exchsym: list) -> DataFrame:
    df_sym['ltp'] = 0
    df_sym['token'] = 0
    resp = broker.kite.ltp(lst_exchsym)
    dct = {k: {'ltp': v['last_price'],
               'token': v['instrument_token'],
               }
           for k, v in resp.items()}
    df_sym['token'] = df_sym.index.map(lambda x: dct[x]['token'])
    df_sym['ltp'] = df_sym.index.map(lambda x: dct[x]['ltp'])
    return df_sym


def generate_signals(row):
    to = pendulum.now().to_datetime_string()
    data = broker.kite.historical_data(row['token'], FM, to, 'day')
    df = pd.DataFrame(data)
    df['200_ma'] = df['close'].rolling(200).mean()
    sleep(secs)
    return df


# Filter out rows where 'disabled' column has a length greater than 0
df_sym['Disabled'] = df_sym['Disabled'].astype('str')
df_sym = df_sym[~(df_sym.Disabled.str.upper() == 'X')]
df_sym.drop('Disabled', axis=1, inplace=True)

df_sym['key'] = "NSE:" + df_sym['Symbol']
df_sym.set_index('key', inplace=True)
lst_exchsym = df_sym.index.to_list()
df_sym = update_df_with_ltp(df_sym, lst_exchsym)

stock_data = df_sym[(df_sym.ltp > 20) & (df_sym.ltp < 300)]
stock_data.sort_values(by=['Industry'], inplace=True)
df_sym.to_csv("tokens.csv")
"""
for index, row in df_sym.iterrows():
    df = generate_signals(row)
    df.to_csv(data/row['Symbol'] + ".csv")
import pandas as pd
import matplotlib.pyplot as plt
"""

# Step 1: Read the CSV data
stock_data = pd.read_csv("stock_data.csv")  # Replace with your CSV filename
# Replace with your CSV filename
historical_data = pd.read_csv("historical_data.csv")

# Step 2: Specify the industry of interest
# Replace with your desired industry
industry_of_interest = "Automobile and Auto Components"

# Filter stocks based on the specified industry
industry_stocks = stock_data[stock_data["industry"]
    == industry_of_interest.lower()]

# Step 3: Calculate daily price change percentage
historical_data['date'] = pd.to_datetime(
    historical_data['date'])  # Ensure Date column is datetime
historical_data = historical_data.sort_values(by='date')

# Merge historical data with industry stocks
merged_data = historical_data.merge(
    industry_stocks[['symbol', 'ltp']], left_on='symbol', right_on='symbol', how='inner')
merged_data['changepercentage'] = (
    merged_data['close'] - merged_data['ltp']) / merged_data['ltp'] * 100

# Step 4: Plot the daily price change percentage as a line chart
plt.figure(figsize=(12, 6))
for symbol, data in merged_data.groupby('symbol'):
    plt.plot(data['date'], data['changepercentage'], label=symbol)

plt.xlabel('Date')
plt.ylabel('Change Percentage')
plt.title(f'Daily Price Change Percentage ({industry_of_interest})')
plt.legend()
plt.grid(True)

# Step 5: Calculate and plot the 12-day moving average
merged_data['12dayma'] = merged_data.groupby('symbol')['changepercentage'].rolling(
    window=12).mean().reset_index(level=0, drop=True)
for symbol, data in merged_data.groupby('symbol'):
    plt.plot(data['date'], data['12dayma'],
             linestyle='--', label=f'{symbol} 12-Day MA')

plt.legend()

# Step 6: Plot OHLC bars based on the change percentage
plt.figure(figsize=(12, 6))
for symbol, data in merged_data.groupby('symbol'):
    ax = plt.subplot(111)
    ax.set_title(f'OHLC Bars for {symbol}')
    ax.plot(data['date'], data['open'],
            label='Open', linestyle='-', marker='o')
    ax.plot(data['date'], data['high'],
            label='High', linestyle='-', marker='o')
    ax.plot(data['date'], data['low'], label='Low', linestyle='-', marker='o')
    ax.plot(data['date'], data['close'],
            label='Close', linestyle='-', marker='o')

plt.xlabel('Date')
plt.ylabel('Price')
plt.legend()
plt.grid(True)

# Show the plots
plt.tight_layout()
plt.show()
"""


