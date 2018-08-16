
# Arbitrage & Trades
Records arbitrage opportunities and trades executed.

## RDBMS Schema
One `Arbitrage` object is created for every arbitrage executed (we may also want to store non-executed arbitrage that we found).
```
Arbitrage(
	id, foundAt(Date), executedAt(Date), startingCurrency(String), propogateFee(Boolean), restrictByBalance(Boolean), minConversionRatio(BigDecimal), minTheoreticalConversionRatio(BigDecimal),
	bottleneckEdge(ArbitrageExchangeEdge.id), bottleneckVolume(BigDecimal), bottleneckCurrency(BigDecimal)
)
ArbitrageExchangeEdge(id, Arbitrage.id, depth(Int), exchange(String) fromVolume(BigDecimal), fromWithdrawalFee(BigDecimal), toWithdrawalFee(BigDecimal), toVolume(BigDecimal), fromCurrency(String), toCurrency(String))
ConversionOrder(id, updatedAt(Date), ArbitrageExchangeEdge.id, conversionRate(BigDecimal), fromVolume(BigDecimal), toVolume(BigDecimal), fee(BigDecimal))
LimitOrder(See LimitOrder under Market Data > RDBMS Schema, plus a foreign key ConversionOrder.id)
ExecutedOrder(id, Arbitrage.id, exchangeOrderId(String), executedAt(Date) volume(BigDecimal), price(BigDecimal), marketType(BID,ASK), orderType(LIMIT,MARKET), currencyPair(String))
```
Still Needed:
- balances of every exchange immediately before and after arb execution
- result of order (via getTradeHistory)

## Relations
```
Arbitrage has_many ArbitrageExchangeEdge (one for each conversion, e.g. BTC->LTC, LTC->ETH, ETH->BTC would be three ArbitrageExchangeEdges for one Arbitrage)
ArbitrageExchangeEdge has_many ConversionOrder (ArbitrageExchangeEdge.depth many, representing the outstanding LimitOrders that we want to "take")
```

## NoSQL/JSON Schema
Assume each Arbitrage, ArbitrageExchangeEdge, etc. has all the fields listed in the RDBMS Schema section
```
Arbitrage = {
	<Arbitrage fields>
	arbitragePath => [
		{
			<ArbitrageExchangeEdge fields>
			existingOrders => [
				{ 
					<ConversionOrder fields> 
					limitOrder => { <LimitOrder fields> }
				},
				{ <ConversionOrder fields> },
				...
			],
			placedOrder = { <ExecutedOrder fields> }
			orderResult = { (results of order via getTradeHistory) }
		},
		{ <ArbitrageExchangeEdge fields> },
		{ <ArbitrageExchangeEdge fields> },
		...
	],
	balances => [
		{exchange => Binance, currency => Ether, amount => 10.3905},
		...
	],
}
```

# Market Data
Used primarily for machine learning and general testing of new trading algorithms. Records all orders placed and executed. That way, we can simulate the market over any time by getting all the active `LimitOrder`s, then adding, partially filling, and removing `LimitOrder`s over time.

## RDBMS Schema
```
LimitOrder(id, createdAt(Date), filledAt(Date), exchange(String), currencyPair(String), type(BID,ASK), orderId(String), limitPrice(BigDecimal), averagePrice(BigDecimal), originalAmount(BigDecimal), cumulativeAmount(BigDecimal), fee(BigDecimal), status(String))
```

## Relations
None yet

## NoSQL/JSON Schema
Pretty much the same as RDBMS

# Thoughts
- the ArbitrageExchangeEdges should really be stored as a list since they are ordered, which means we will need to re-construct this array after making the DB call or store pointers to the next and previous ArbitrageExchangeEdge
- the trader is the only writer, all others (developers debugging, future ML pipelines, etc.) only read from the DB
- each ConversionOrder belongs to only one ArbitrageExchangeEdge, and each ArbitrageExchangeEdge to only one Arbitrage. It's not a ton of data so they could probably just be embedded in Arbitrage which is easier with NoSQL?
