from toolkit.logger import Logger
from toolkit.fileutils import Fileutils
from login_get_kite import get_kite, remove_token

from constants import dir_path, MAX_ALLOWED_QUANTITY, MIN_SELL_QUANTITY
import sys
from time import sleep
import traceback
import pandas as pd
import pendulum

logging = Logger(10)

TRADES_DF = pd.read_csv("tradebook.csv")
FM = pendulum.now().subtract(days=125).to_datetime_string()

# Convert the "trade_date" column to datetime if it's not already
TRADES_DF['trade_date'] = pd.to_datetime(TRADES_DF['trade_date'])

# Sort the DataFrame by trade_date in descending order
TRADES_DF.sort_values(by='trade_date', ascending=False, inplace=True)

# Drop duplicates based on the "symbol" column, keeping the last occurrence
TRADES_DF = TRADES_DF.drop_duplicates(
    subset='symbol', keep='last').reset_index(drop=True)


fibonacci_series = [1, 1]
while True:
    next_fibonacci = fibonacci_series[-1] + fibonacci_series[-2]
    if next_fibonacci > MAX_ALLOWED_QUANTITY:
        break
    fibonacci_series.append(next_fibonacci)


def find_fibo_quantity(**last_trade):
    if last_trade['trade_type'] == 'sell':
        if last_trade['quantity'] in fibonacci_series:
            logging.debug("fibo quantity == previous sell quantity")
            return last_trade['quantity']
        else:
            for fib_num in reversed(fibonacci_series):
                if fib_num < last_trade['quantity']:
                    logging.debug(
                        "fibo quantity < previous sell quantity")
                    return fib_num
    else:
        for fib_num in fibonacci_series:
            if fib_num > last_trade['quantity']:
                logging.debug(
                    "{fibo_num =} > previous buy {last_trade['quantity']}")
                return fib_num


def update_df_with_ltp(df_sym, lst_exchsym):
    sleep(1)
    resp = broker.ltp(lst_exchsym)
    dct = {k: {'ltp': v['last_price'],
               'token': v['instrument_token'],
               }
           for k, v in resp.items()}
    df_sym['ltp'] = df_sym.index.map(lambda x: dct[x]['ltp'])
    df_sym['token'] = df_sym.index.map(lambda x: dct[x]['token'])
    return df_sym


def order_place(index, row):
    try:
        if row['quantity'] == 0:
            logging.debug(f"quantity for {row['symbol']} is 0")
            return

        transaction_type = 'BUY' if row['signal'] == 1 else 'SELL'
        exchsym = index.split(":")
        logging.info(f"placing order for {index}, {str(row)}")
        order_id = broker.order_place(
            tradingsymbol=exchsym[1],
            exchange=exchsym[0],
            transaction_type=transaction_type,
            quantity=row['quantity'],
            order_type='LIMIT',
            product='CNC',
            variety='regular',
            price=row['ltp']
        )
        if order_id:
            logging.info(
                f"{row['signal']} {row['quantity']} order "
                f"{order_id} placed for {exchsym[1]} successfully"
            )
            lst_row = [
                exchsym[1],
                pendulum.now().format('YYYY-MM-DD'),
                exchsym[0],
                transaction_type.lower(),
                row['quantity'],
                row['ltp'],
            ]
            Fileutils().append_to_csv("tradebook.csv", lst_row)

    except Exception as e:
        print(traceback.format_exc())
        logging.warning(f"{str(e)} while placing order for {exchsym[1]}")
    finally:
        return


def generate_signals(row):
    print(f"generating signals for {row['symbol']}")
    to = pendulum.now().to_datetime_string()
    data = broker.kite.historical_data(row['token'], FM, to, '60minute')
    df = pd.DataFrame(data)
    df['12_ma'] = df['close'].rolling(12).mean()
    df['200_ma'] = df['close'].rolling(200).mean()

    # Initialize the 'buy' column to 0
    df['signal'] = 0

    # Set 'buy' to 1 for buy signals based on your rules
    df.loc[(df['open'] < df['12_ma']) & (
        df['close'] > df['12_ma']), 'signal'] = 1
    df.loc[
        (df['close'] > df['200_ma']) &
        (df['open'] > df['12_ma']) &
        (df['close'] < df['12_ma']),
        'signal'
    ] = -1
    print(df.tail())
    sleep(5)
    return df.iloc[-2]['signal']


def calculate_unrealized_profit(row):
    if row['sell_date'] is None:
        return (row['ltp'] - row['buy_price']) * row['buy_quantity']
    else:
        return 0


def read_trades(df_sym):
    tradebook_df = TRADES_DF.merge(df_sym, on='symbol', how='left')
    trades = []
    for _, row in tradebook_df.iterrows():
        if row['trade_type'] == 'buy':
            current_trade = {
                'symbol': row['symbol'],
                'token': row['token'],
                'disabled': row['disabled'],
                'buy_date': row['trade_date'],
                'buy_price': row['price'],
                'buy_quantity': row['quantity'],
                'sell_date': None,
                'sell_price': None,
                'sell_quantity': None,
                'profit': None,
                'ltp': row['ltp'],
                'unrealized': None
            }
            trades.append(current_trade)
        elif row['trade_type'] == 'sell':
            sell_quantity = row['quantity']
            remaining_quantity = sell_quantity

            # Process sell orders FIFO for the current symbol
            for trade in reversed(trades):
                if trade['symbol'] == row['symbol'] and trade['sell_date'] is None:
                    sell_quantity = min(remaining_quantity,
                                        trade['buy_quantity'])
                    remaining_quantity -= sell_quantity

                    trade['sell_date'] = row['trade_date']
                    trade['sell_price'] = row['price']
                    trade['sell_quantity'] = sell_quantity
                    trade['profit'] = (
                        row['price'] - trade['buy_price']) * sell_quantity

                    if remaining_quantity == 0:
                        break
    result_df = pd.DataFrame(trades)
    result_df['unrealized'] = result_df.apply(
        lambda row: calculate_unrealized_profit(row), axis=1)
    result_df = result_df.fillna(0)
    print(f"OVERVIEW {result_df} \n")


def calculate_max_allowed_quantity(symbol):
    """
        Used by sell quantity
    """
    # Filter the DataFrame for the specified symbol
    symbol_df = TRADES_DF[TRADES_DF['symbol'] == symbol]

    if symbol_df.empty:
        return 0  # Symbol not found in the tradebook

    # Calculate the total buy quantity and total sell quantity for the symbol
    total_buy_quantity = symbol_df[symbol_df['trade_type']
                                   == 'buy']['quantity'].sum()
    total_sell_quantity = symbol_df[symbol_df['trade_type']
                                    == 'sell']['quantity'].sum()

    # Calculate the maximum allowed quantity as holdings quantity
    max_allowed_quantity = total_buy_quantity - total_sell_quantity
    logging.info(f"{symbol} holdings on hand {max_allowed_quantity}")

    return max_allowed_quantity


def calculate_sell_quantity(symbol, ltp):

    sell_quantity = 0
    # Filter the DataFrame for the specified symbol
    symbol_df = TRADES_DF[TRADES_DF['symbol'] == symbol]

    if symbol_df.empty:
        return 0  # Symbol not found in the tradebook

    # Sort the DataFrame by Date
    symbol_df = symbol_df.sort_values('trade_date')

    # Calculate the percentage change in LTP (market movement) from the last trade
    symbol_df['ltp_change'] = (
        ltp - symbol_df['price'].shift(1)) / symbol_df['price'].shift(1) * 100

    # Get the last trade for the symbol
    last_trade = symbol_df.iloc[-1]

    # Calculate the maximum allowed quantity (holdings quantity)
    max_allowed_quantity = calculate_max_allowed_quantity(symbol)

    # Calculate the previous number in the Fibonacci series
    fibonacci_series = [1, 1]
    while True:
        next_fibonacci = fibonacci_series[-1] + fibonacci_series[-2]
        if next_fibonacci > max_allowed_quantity:
            break
        fibonacci_series.append(next_fibonacci)

    # Determine the sell quantity based on market movement and Fibonacci series
    if last_trade['ltp_change'] > 5:
        # Market has moved > 5% from the last trade
        if last_trade['trade_type'] == 'buy' and last_trade['quantity'] >= MIN_SELL_QUANTITY:
            logging.debug("previous trade is buy")
            return last_trade['quantity']
        else:  # 'sell':
            # Find the previous number in the Fibonacci series below the current trade quantity
            for fib_num in reversed(fibonacci_series):
                if fib_num < last_trade['quantity'] and fib_num >= MIN_SELL_QUANTITY:
                    logging.debug(
                        f"SELL: {symbol} previous fibo conditions met")
                    return fib_num
    logging.debug("SELL: conditions not met for {symbol}")
    return sell_quantity


def calculate_buy_quantity(symbol, ltp):
    buy_quantity = 0

    # Filter the DataFrame for the specified symbol
    symbol_df = TRADES_DF[TRADES_DF['symbol'] == symbol]

    if symbol_df.empty:
        logging.debug(f"BUY: no trade history for this stock {'symbol'}")
        return 1

    # Sort the DataFrame by Date
    symbol_df = symbol_df.sort_values('trade_date')

    # Calculate the percentage change in LTP (market movement) from the last trade
    symbol_df['ltp_change'] = (
        ltp - symbol_df['price'].shift(1)) / symbol_df['price'].shift(1) * 100

    # Get the last trade for the symbol
    last_trade = symbol_df.iloc[-1].to_dict()
    logging.debug(f"{last_trade=}")

    # Determine the buy quantity based on market movement and Fibonacci series
    if (last_trade['ltp_change'] < -5):
        logging.debug(f"BUY: {symbol} conditions met ... finding quantity")
        # Market has moved < 5% from the last trade
        buy_quantity = find_fibo_quantity(**last_trade)
    else:
        logging.debug(f"BUY: {symbol} failed by PERCENTAGE below condition")
    return buy_quantity


try:
    broker = get_kite(api="bypass", sec_dir=dir_path)
    df_sym = pd.read_csv("symbols.csv")
    df_sym['key'] = "NSE:" + df_sym['symbol']
    df_sym.set_index('key', inplace=True)
    lst_exchsym = df_sym.index.to_list()
    df_sym = update_df_with_ltp(df_sym, lst_exchsym)
except Exception as e:
    remove_token(dir_path)
    print(traceback.format_exc())
    logging.error(f"{str(e)} while getting ltp and token")
    sys.exit(1)


try:
    df_sym = df_sym[df_sym['disabled'] != 'x']
    df_sym['signal'] = df_sym.apply(generate_signals, axis=1)
    df_sym = update_df_with_ltp(df_sym, lst_exchsym)

    df_sym['quantity'] = 0
    for index, row in df_sym.iterrows():
        if row['signal'] == -1:
            row['quantity'] = calculate_sell_quantity(
                row['symbol'], row['ltp'])
        elif row['signal'] == 1:
            row['quantity'] = calculate_buy_quantity(
                row['symbol'], row['ltp'])

        if row['signal'] != 0 and row['quantity'] > 0:
            order_place(index, row)
    sys.exit(0)
except Exception as e:
    remove_token(dir_path)
    print(traceback.format_exc())
    logging.error(f"{str(e)} in the main loop")
