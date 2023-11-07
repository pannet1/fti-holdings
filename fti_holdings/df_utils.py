import pandas as pd 

def get_holdings_on_hand(df):
    # Create a dictionary to keep track of holdings
    holdings = {}

    # Calculate holdings
    for index, row in df.iterrows():
        symbol = row['symbol']
        quantity = row['quantity']
        if row['trade_type'] == 'buy':
            holdings[symbol] = holdings.get(symbol, 0) + quantity
        elif row['trade_type'] == 'sell':
            holdings[symbol] = holdings.get(symbol, 0) - quantity

    # Create a DataFrame from the holdings dictionary
    final_holdings_df = pd.DataFrame(list(holdings.items()), columns=['symbol', 'holding'])
    return final_holdings_df


if __name__ == "__main__":

    df = pd.read_csv("tradebook.csv")
    print(get_holdings_on_hand(df))
    

