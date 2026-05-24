We want to mimic StreamQuotes provide the same public methods/properties
this way we can easily plug this wherever StreamQuotes feaure is used.
the default timeframe for getting historical data is 1Min and the default
period is one month from current date.
These should be parameters so one can easily change the timeframe and
period (start date and end date)
the result is each call should advance to the next close price of the candlestick
in the chosen timeframe..
Use broker-ai broker's (in this case Finvasia) historical api for this purpose
