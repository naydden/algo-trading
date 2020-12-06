# weekly and daily for trend
# 4 h for entry or exit confirmation

# TODO:
# - entry
# - risk management: going full per position as only one graph
# - strategy
# - implement a strategy in case it goes sideways

import numpy as np

def initialize(state):
	state.trend = None
	state.number_offset_trades = 0
	state.position_amount = 0
	state.peak = 0
	state.first = False
	state.ema_started = False

	state.max_all_time = 19660

	state.position_active = False
	state.position_buy_price = 0
	state.position_top_price = 0
	state.position_stop_loss = 0
	state.position_crossover = True


def buy(amount, last_price):
	order_market_amount(symbol="BTCUSDT", amount = amount)

	print("-------")
	print("Buy Signal: creating market order for {}".format("BTCUSDT"))
	print("Buy amount: ", amount, " at current market price: ", last_price)
	print("-------")

def close_and_log(position, data, trend):
	print("-------")
	logmsg = "Sell Signal: closing {} position with exposure {} at current market price {}"
	print(logmsg.format(data.symbol,float(position.exposure),data.close_last))
	print("Trend: ", trend)
	print("-------")

	close_position(data.symbol)


@schedule(interval= "1d", symbol="BTCUSDT")
def handler_long(state, data):
	ema_long = data.ema(32).last
	ema_short = data.ema(16).last
	adx = data.adx(14).last
	dm = data.dm(period=14)

	if ema_long is None or ema_short is None or adx is None or dm is None:
		return

	if dm.plus_dm.last > dm.minus_dm.last and ema_short > ema_long:
		state.trend = "upward"
	else:
		state.trend = "downward"

	if adx < 25:
		state.trend == "sideways"

	print("State: ", state.trend)


@schedule(interval="1h", symbol="BTCUSDT")
def handler(state, data):
	'''
	1) Indicators
	'''

	ema_long = data.ema(35).last
	ema_short = data.ema(14).last
	rsi = data.rsi(14).last
	bbands = data.bbands(20, 2)

	# on erronous data return early (indicators are of NoneType)
	if rsi is None or ema_long is None or ema_short is None or bbands is None:
		return

	# has_high_volume = ema_short_volume[-1] > ema_long_volume[-1]


	close_prices = data.close
	current_price = data.close_last
	state.peak = current_price if current_price > state.peak else state.peak
	bbands_lower = bbands["bbands_lower"].last
	bbands_upper = bbands["bbands_upper"].last
	bbands_middle = bbands["bbands_middle"].last

	is_ema_short_up = (data.ema(3)[-1] - data.ema(3)[-2]) > 0

	'''
	2) Resolve buy value
	'''

	portfolio = query_portfolio()
	balance_quoted = portfolio.excess_liquidity_quoted

	buy_value = float(balance_quoted)*0.85


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

	elif state.trend is "downward":
		if has_position:
			close_and_log(position, data, state.trend)

	elif state.trend is "upward":
		# if not state.first:
		# 	if not has_position and (ema_short / ema_long) > 1:
		# 		state.position_amount = buy_value/current_price
		# 		stop_loss = 0.05
		# 		buy(state.position_amount, current_price)
		# 		state.first = True

		# 		state.position_active = True
		# 		state.position_buy_price = current_price
		# 		state.position_top_price = current_price
		# 		state.position_stop_loss = stop_loss
		# else:

		# rsi_pullback = rsi_under_50 and rsi > 50
		is_buy = ema_short > ema_long and rsi < 40 or \
			  current_price < bbands_lower and rsi < 40 and is_ema_short_up

		is_sell = current_price/state.position_top_price < 0.96 and current_price > bbands_lower or \
			  ema_long > ema_short and rsi > 70 or \
			  (ema_long / ema_short) - 1 > 0.02 and not rsi < 40




		if not has_position:
			if is_buy:

				state.position_amount = buy_value/current_price
				stop_loss = 0.06
				buy(state.position_amount, current_price)

				state.first = True
				state.position_active = True
				state.position_buy_price = current_price
				state.position_top_price = current_price
				state.position_stop_loss = stop_loss
		else:
			if is_sell:
				close_and_log(position, data, state.trend)
			else:
				if current_price > state.position_top_price and current_price < bbands_upper:
					state.position_top_price = current_price
					state.position_stop_loss = state.position_stop_loss

			# else:
			# 	if current_price/state.position_top_price  < 1-0.03 and \
			# 		ema_long / ema_short - 1 > 0.008  or \
			# 		current_price/state.position_top_price  < 1-0.06:
			# 		close_and_log(position, data, state.trend)
			# 	elif (ema_long / ema_short) - 1 > 0.004 and rsi > 60 or \
			# 	(ema_long / ema_short) - 1 > 0.02:
			# 		close_and_log(position, data, state.trend)



