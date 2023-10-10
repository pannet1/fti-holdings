from pandas.core.api import DataFrame
from toolkit.logger import Logger
from toolkit.fileutils import Fileutils
from omspy_brokers.bypass import Bypass
from constants import dir_path, secs
import sys
from time import sleep
import traceback
import pandas as pd
import pendulum

logging = Logger(10)

fils = Fileutils()
FM = pendulum.now().subtract(days=125).to_datetime_string()
TRADES_DF = pd.read_csv("tradebook.csv")


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


def update_df_with_ltp(df_sym: DataFrame, lst_exchsym: list) -> DataFrame:
    sleep(secs)
    resp = broker.ltp(lst_exchsym)
    dct = {k: {'ltp': v['last_price'],
               'token': v['instrument_token'],
               }
           for k, v in resp.items()}
    df_sym['ltp'] = df_sym.index.map(lambda x: dct[x]['ltp'])
    df_sym['token'] = df_sym.index.map(lambda x: dct[x]['token'])
    return df_sym


def order_place(index: str, row: DataFrame):
    try:
        transaction_type = 'BUY' if row['signal'] > 0 else 'SELL'
        exchsym = index.split(":")
        logging.info(f"placing order for {index}, {str(row)}")
        order_id = broker.order_place(
            tradingsymbol=exchsym[1],
            exchange=exchsym[0],
            transaction_type=transaction_type,
            quantity=abs(row['signal']),
            order_type='LIMIT',
            product='CNC',
            variety='regular',
            price=row['ltp']
        )
        if order_id:
            logging.info(
                f"{transaction_type} order for {exchsym[1]} "
                f" for {abs(row['signal'])}q placed successfully"
            )
            lst_row = [
                exchsym[1],
                pendulum.now().format('YYYY-MM-DD'),
                exchsym[0],
                transaction_type.lower(),
                abs(row['signal']),
                row['ltp'],
            ]
            fils.append_to_csv("tradebook.csv", lst_row)

    except Exception as e:
        print(traceback.format_exc())
        logging.warning(f"{str(e)} while placing order for {exchsym[1]}")
    finally:
        return


def generate_signals(row):
    try:
        print(f"generating signals for {row['symbol']} {row['ltp']}")
        to = pendulum.now().to_datetime_string()
        data = broker.kite.historical_data(row['token'], FM, to, '60minute')
        df = pd.DataFrame(data)
        df['12_ma'] = df['close'].rolling(12).mean()
        df['200_ma'] = df['close'].rolling(200).mean()
        df['signal'] = 0

        # Set 'signal' > 0 for buy signals based on your rules
        """ above ma200 wait for next fibo change % """
        df.loc[
            (df['open'] < df['12_ma']) &
            (df['close'] > df['12_ma']) &
            (row['perc_chng'] < 0) &
            (row['perc_chng'] < -1 * row['fibo']) &
            (row['ltp'] > df['200_ma']), 'signal'
        ] = row['quantity']
        """ below ma200 wait for bigger change % """
        df.loc[
            (df['open'] < df['12_ma']) &
            (df['close'] > df['12_ma']) &
            (row['perc_chng'] < 0) &
            (row['perc_chng'] < -1 * row['martingale']) &
            (row['ltp'] < df['200_ma']), 'signal'
        ] = row['martingale']
        """ below ma200 wait for sell fibo % """
        df.loc[
            (row['trade_type'] == 'buy') &
            (df['open'] > df['12_ma']) &
            (df['close'] < df['12_ma']) &
            (row['perc_chng'] > row['fibo']) &
            (row['ltp'] < df['200_ma']), 'signal'
        ] = row['quantity'] * -1
        """ above ma200 for sell at martingale % """
        df.loc[
            (row['trade_type'] == 'buy') &
            (df['open'] > df['12_ma']) &
            (df['close'] < df['12_ma']) &
            (row['perc_chng'] > row['martingale']) &
            (row['ltp'] > df['200_ma']), 'signal'
        ] = row['quantity'] * -1
        print(df.tail())
        sleep(secs)
        return df.iloc[-2]['signal']
    except Exception as e:
        print(e)


def calculate_fibo_martingale(quantity):
    # Define a function to calculate 'fibo' and 'martingale' columns
    list_of_lots = [1, 2, 3, 5, 8, 13, 21, 33, 54]
    # Find the next highest number in the series for 'fibo' column
    for lot in list_of_lots:
        if quantity < lot:
            quantity = lot
            break
    return quantity


try:
    TRADES_DF['trade_date'] = pd.to_datetime(TRADES_DF['trade_date'])
    TRADES_DF.sort_values(by='trade_date', ascending=True, inplace=True)
    TRADES_DF = TRADES_DF.drop_duplicates(
        subset='symbol', keep='last').reset_index(drop=True)
except Exception as e:
    print(e)


try:
    broker = get_kite()
    df_sym = pd.read_csv("symbols.csv")
    df_sym['key'] = "NSE:" + df_sym['symbol']
    df_sym.set_index('key', inplace=True)
    lst_exchsym = df_sym.index.to_list()
except Exception as e:
    print(traceback.format_exc())
    logging.error(f"{str(e)} while getting login")
    sys.exit(1)


try:
    df_sym = update_df_with_ltp(df_sym, lst_exchsym)
    # Filter out rows where 'disabled' column has a length greater than 0
    df_sym['disabled '] = df_sym['disabled'].astype('str')
    df_sym = df_sym[~(df_sym.disabled.str.upper() == 'X')]
    df_sym.drop('disabled', axis=1, inplace=True)

    df_merged = TRADES_DF.merge(df_sym, on='symbol', how='inner')

    df_merged['perc_chng'] = (
        df_merged['ltp'] - df_merged['price']) / df_merged['ltp'] * 100

    # Apply the function to each row of the DataFrame
    df_merged['fibo'] = df_merged['quantity'].apply(
        calculate_fibo_martingale)
    df_merged['martingale'] = df_merged['fibo'].apply(
        calculate_fibo_martingale)

    df_merged['signal'] = df_merged.apply(generate_signals, axis=1)
    # Display the updated DataFrame
    df_merged['key'] = df_merged['exchange'] + ":" + df_merged['symbol']
    df_merged.set_index('key', inplace=True)
    df_merged.drop(columns=['exchange', 'symbol'], inplace=True)
    print(df_merged)
    for index, row in df_merged.iterrows():
        if row['signal'] != 0:
            order_place(index, row)
    sys.exit(0)

except Exception as e:
    print(traceback.format_exc())
    logging.error(f"{str(e)} in the main loop")
