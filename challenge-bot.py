def initialize(state):
    state.number_offset_trades = 0;


@schedule(interval="1h", symbol="BTCUSDT")
def handler(state, data):

    '''
    1) Compute indicators from data
    '''

    macd_ind = data.macd(12,26,9)
    rsi = data.rsi(14).last
    bbands = data.bbands(20, 2)

    # on erronous data return early (indicators are of NoneType)
    if macd_ind is None:
        return

    signal = macd_ind['macd_signal'].last
    macd = macd_ind['macd'].last
    bbands_lower = bbands["bbands_lower"].last
    bbands_upper = bbands["bbands_upper"].last
    bbands_middle = bbands["bbands_middle"].last
    bbands_m = bbands["bbands_middle"]
    is_ema_short_up = (bbands_m[-1] - bbands_m[-3]) > 0

    current_price = data.close_last

    '''
    2) Fetch portfolio
        > check liquidity (in quoted currency)
        > resolve buy value
    '''

    portfolio = query_portfolio()
    balance_quoted = portfolio.excess_liquidity_quoted
    # we invest only 80% of available liquidity
    buy_value = float(balance_quoted) * 0.80

    '''
    3) Fetch position for symbol
        > has open position
        > check exposure (in base currency)
    '''

    position = query_open_position_by_symbol(data.symbol,include_dust=False)
    has_position = position is not None

    '''
    4) Resolve buy or sell signals
        > create orders using the order api
        > print position information

    '''
    is_in_range = current_price < (bbands_upper+bbands_middle) / 2
    is_small = abs(macd) < 5
    if macd > signal and not has_position and current_price < bbands_upper and not is_small:
        print("-------")
        print("Buy Signal: creating market order for {}".format(data.symbol))
        print("Buy value: ", buy_value, " at current market price: ", data.close_last)
        order_market_value(symbol=data.symbol, value=buy_value)

    elif macd < signal and has_position and not is_ema_short_up and not current_price < bbands_lower and rsi > 50 and not is_small:
        print("-------")
        logmsg = "Sell Signal: closing {} position with exposure {} at current market price {}"
        print(logmsg.format(data.symbol,float(position.exposure),data.close_last))
        close_position(data.symbol)


    '''
    5) Check strategy profitability
        > print information profitability on every offsetting trade
    '''

    if state.number_offset_trades < portfolio.number_of_offsetting_trades:

        pnl = query_portfolio_pnl()
        print("-------")
        print("Accumulated Pnl of Strategy: {}".format(pnl))

        offset_trades = portfolio.number_of_offsetting_trades
        number_winners = portfolio.number_of_winning_trades
        print("Number of winning trades {}/{}.".format(number_winners,offset_trades))
        print("Best trade Return : {:.2%}".format(portfolio.best_trade_return))
        print("Worst trade Return : {:.2%}".format(portfolio.worst_trade_return))
        print("Average Profit per Winning Trade : {:.2f}".format(portfolio.average_profit_per_winning_trade))
        print("Average Loss per Losing Trade : {:.2f}".format(portfolio.average_loss_per_losing_trade))
        # reset number offset trades
        state.number_offset_trades = portfolio.number_of_offsetting_trades
