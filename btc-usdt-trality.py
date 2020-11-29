# weekly and daily for trend
# 4 h for entry or exit confirmation
def initialize(state):
    state.trend = None
    state.number_offset_trades = 0
    state.position_amount = 0
    state.peak = 0

    state.max_all_time = 19660

    state.levels = [
    	{
    		type : 'r',
    		level : 19300,
    		margin: 0.02,
    		strength : 9, # 1-10
    		tested: 2,
    		timescale: '1w',
    		signal_reached: 'wait',
    		signal_crossed: 'buy'
    	},
    	{
    		type : 's',
    		level : 17870,
    		margin: 0.02,
    		strength : 2, # 1-10
    		tested: 1,
    		timescale: '4h',
    		signal_reached: 'wait',
    		signal_crossed: 'buy'
    	},
    	{
    		type : 's',
    		level : 16440,
    		margin: 0.02,
    		strength : 8, # 1-10
    		tested: 1,
    		timescale: '4h',
    		signal_reached: 'wait',
    		signal_crossed: 'sell'
    	},
     	{
    		type : 's',
    		level : 10830,
    		margin: 0.02,
    		strength : 3, # 1-10
    		tested: 2,
    		timescale: '1d',
    		signal_reached: 'buy',
    		signal_crossed: 'sell',

    	}
    ]

@schedule(interval= "1d", symbol="BTCUSDT")
def handler_long(state, data):
    ema_long = data.ema(40).last
    ema_short = data.ema(15).last
    adx = data.adx(14).last

    if adx < 25:
        state.trend == "sideways"
    else:
        if ema_short > ema_long:
            state.trend = "upward"
        else:
            state.trend = "downward"

    print("State: ", state.trend)

@schedule(interval="1h", symbol="BTCUSDT")
def handler(state, data):
    '''
    1) Compute indicators from data
    '''

    ema_long = data.ema(40).last
    ema_short = data.ema(20).last
    rsi = data.rsi(14).last

    # on erronous data return early (indicators are of NoneType)
    if rsi is None or ema_long is None:
        return

    current_price = data.close_last
    state.peak = current_price if current_price > state.peak else state.peak

    '''
    2) Fetch portfolio
        > check liquidity (in quoted currency)
        > resolve buy value
    '''

    portfolio = query_portfolio()
    balance_quoted = portfolio.excess_liquidity_quoted
    # we invest only 80% of available liquidity
    num_open_positions = len(portfolio.open_positions)
    if num_open_positions > 0:
    	buy_value = float(balance_quoted) * 0.40
    else:
    	buy_value = float(balance_quoted) * 0.70


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
    if state.trend is "sideways":
        return
    
    if state.trend is "downward":
        if (ema_short - ema_long)/ema_short > 0.004  and not has_position:
            print("-------")
            print("Buy Signal: creating market order for {}".format(data.symbol))
            print("Buy value: ", buy_value, " at current market price: ", data.close_last)

            order_market_value(symbol=data.symbol, value=buy_value)
            # order_stop_loss(symbol=data.symbol, stop_percent=0.05)
            order_trailing_iftouched_value(symbol="BTCUSDT", value=-buy_value, trailing_percent = 0.1, stop_price=current_price*0.95)


        elif (ema_long - ema_short)/ema_long > 0.002 and has_position:
            print("-------")
            logmsg = "Sell Signal: closing {} position with exposure {} at current market price {}"
            print(logmsg.format(data.symbol,float(position.exposure),data.close_last))

            close_position(data.symbol)
    
    print(state.peak / current_price)
    if state.trend is "upward":
        if not has_position:
            if (ema_short - ema_long)/ema_short > 0.002 and rsi > 60:
                print("-------")
                print("Buy Signal: creating market order for {}".format(data.symbol))
                print("Buy value: ", buy_value, " at current market price: ", data.close_last)

                state.position_amount = buy_value/current_price
                order_market_amount(symbol="BTCUSDT", amount = state.position_amount)
                #order_market_value(symbol=data.symbol, value=buy_value)
                #order_stop_loss(symbol=data.symbol, stop_percent=0.05)
                #order_trailing_iftouched_value(symbol="BTCUSDT", value=-buy_value, trailing_percent = 0.1, stop_price=current_price*1.1)
        else:
            if (ema_long - ema_short)/ema_long > 0.002:
                print("-------")
                logmsg = "Sell Signal: closing {} position with exposure {} at current market price {}"
                print(logmsg.format(data.symbol,float(position.exposure),data.close_last))

                close_position(data.symbol)

            elif state.peak / current_price > 1.09:
                close_position(data.symbol)
                state.peak = current_price
   