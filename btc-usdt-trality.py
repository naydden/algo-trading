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

	state.levels = [
		{
			'type' : 'r',
			'level' : 19300,
			'margin': 0.02,
			'strength' : 9, # 1-10
			'tested': 2,
			'timescale': '1w',
			'signal_reached': 'wait',
			'signal_crossed': 'buy'
		},
		{
			'type' : 's',
			'level' : 17870,
			'margin': 0.02,
			'strength' : 2, # 1-10
			'tested' : 1,
			'timescale' : '4h',
			'signal_reached' : 'wait',
			'signal_crossed' : 'buy'
		},
		{
			'type' : 's',
			'level' : 16440,
			'margin' : 0.02,
			'strength' : 8, # 1-10
			'tested' : 1,
			'timescale' : '4h',
			'signal_reached' : 'wait',
			'signal_crossed' : 'sell'
		},
		{
			'type' : 's',
			'level' : 10830,
			'margin': 0.02,
			'strength' : 3, # 1-10
			'tested': 2,
			'timescale': '1d',
			'signal_reached': 'buy',
			'signal_crossed': 'sell',
		}
	]

def last_five_up(data):
	prices = data.select("close")
	signs = np.sign(np.diff(prices))[-5:]
	return sum(signs) == 5

def order_with_sl(amount,percent, last_price, trend):
	with OrderScope.sequential(fail_on_error=True, wait_for_entire_fill=False):
		order_1 = order_market_amount(symbol="BTCUSDT", amount = amount)
		order_2 = order_stop_loss(symbol="BTCUSDT", amount = amount, stop_percent=percent)
		# order_2 = order_trailing_iftouched_amount(symbol="BTCUSDT", amount = -amount,\
		#		 trailing_percent = float(percent), stop_price=float(last_price*(1-percent)))

	print("-------")
	print("Buy Signal: creating market order for {}".format("BTCUSDT"))
	print("Buy amount: ", amount, " at current market price: ", last_price)
	print("Trend: ", trend)
	print("-------")

def check_levels_buy(close_prices, current_price, state):

	current_price = close_prices[-1]
	if state.trend == "upward":
		case0 = [price < state.levels[0]['level'] * 0.98 for price in close_prices[-20:]]
		case2 = [price < state.levels[2]['level'] * 0.98 for price in close_prices[-20:]]
		case3 = [price < state.levels[3]['level'] * 0.98 for price in close_prices[-20:]]


		if current_price / state.levels[0]['level'] > 1.02 and np.any(case0):

			stop_loss = current_price/state.levels[0]['level']*0.98 - 1
			order_with_sl(state.position_amount, stop_loss, current_price, state.trend )

		elif current_price / state.levels[2]['level'] > 1.02 and np.any(case2):

			stop_loss = current_price/state.levels[2]['level']*0.98 - 1
			order_with_sl(state.position_amount, stop_loss, current_price, state.trend )

		elif current_price / state.levels[3]['level'] > 1.02 and np.any(case3):

			stop_loss = current_price/state.levels[3]['level']*0.98 - 1
			order_with_sl(state.position_amount, stop_loss, current_price, state.trend )

def check_levels_close(close_prices, position, data, state):

	current_price = close_prices[-1]
	if state.trend  == "downward":
		case0 = [price > state.levels[0]['level'] * 1.02 for price in close_prices[-20:]]
		case2 = [price > state.levels[2]['level'] * 1.02 for price in close_prices[-20:]]
		case3 = [price > state.levels[3]['level'] * 1.02 for price in close_prices[-20:]]

		if current_price / state.levels[0]['level'] < 0.98 and np.any(case0):

			close_and_log(position, data, state.trend )

		elif current_price / state.levels[2]['level'] < 0.98 and np.any(case2):

			close_and_log(position, data, state.trend )

		elif current_price / state.levels[3]['level'] < 0.98 and np.any(case3):

			close_and_log(position, data, state.trend )


def close_and_log(position, data, trend):
	print("-------")
	logmsg = "Sell Signal: closing {} position with exposure {} at current market price {}"
	print(logmsg.format(data.symbol,float(position.exposure),data.close_last))
	print("Trend: ", trend)
	print("-------")

	close_position(data.symbol)


@schedule(interval= "1d", symbol="BTCUSDT")
def handler_long(state, data):
	ema_long = data.ema(40).last
	ema_short = data.ema(15).last
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
	bbands = data.bbands(period=20,stddev=2)
	# volume = data.volume
	# ema_short_volume, ema_long_volume = volume.ema(20).last, volume.ema(40).last
	rsi = data.rsi(14).last

	# on erronous data return early (indicators are of NoneType)
	if rsi is None or ema_long is None or ema_short is None or bbands is None :
		return

	# has_high_volume = ema_short_volume[-1] > ema_long_volume[-1]


	close_prices = data.close
	current_price = data.close_last
	state.peak = current_price if current_price > state.peak else state.peak

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
		if not has_position:
			# strategy: detect pullback from bollinger band lower until the moving average
			if (ema_short / ema_long) - 1 > 0.004 and rsi > 60 :
				state.position_amount = buy_value/current_price
				stop_loss = 0.03
				order_with_sl(state.position_amount, stop_loss, current_price, state.trend)
				state.first = True
				portfolio = query_portfolio()
				print(portfolio.open_positions, portfolio.closed_positions, portfolio.open_order_ids)
		# else:
		# 	if ((ema_long / ema_short) - 1 > 0.004 and rsi < 30) or current_price/bbands.bbands_lower.last < 0.965:
		# 		close_and_log(position, data, state.trend)
			# else:
			# 	check_levels_close(close_prices, position, data, state)

	elif state.trend is "upward":
		if not state.first:
			if not has_position and (ema_short / ema_long) > 1:
				state.position_amount = buy_value/current_price
				stop_loss = 0.03
				order_with_sl(state.position_amount, stop_loss, current_price, state.trend)
				state.first = True
		else:
			if not has_position:
				if (ema_short / ema_long) - 1 > 0.008  and rsi > 60:
					state.position_amount = buy_value/current_price
					# stop_loss = current_price/bbands.bbands_lower.last*0.98 - 1
					# if stop_loss < 0:
					stop_loss = 0.03
					order_with_sl(state.position_amount, stop_loss, current_price, state.trend)
				# else:
				# 	check_levels_buy(close_prices, current_price, state)

			# else:
			# 	if (ema_long / ema_short) - 1 > 0.02:
			# 		close_and_log(position, data, state.trend)

			# 	elif state.peak / current_price - 1 > 0.06:
			# 		close_and_log(position, data, state.trend)
			# 		state.peak = current_price
				# else:
				# 	check_levels_close(close_prices, position, data, state)



