"""
Crypto & Finance Module — Cryptocurrency prices, stock quotes, currency conversion.
Uses free APIs for real-time financial data.
"""

import asyncio
import aiohttp
from datetime import datetime
from core.logger import get_logger

log = get_logger("finance")


async def get_crypto_price(symbol: str = "bitcoin") -> str:
    """Get cryptocurrency price from CoinGecko API."""
    try:
        symbol_lower = symbol.lower().strip()
        # Map common abbreviations
        symbol_map = {
            "btc": "bitcoin", "eth": "ethereum", "bnb": "binancecoin",
            "sol": "solana", "xrp": "ripple", "ada": "cardano",
            "doge": "dogecoin", "dot": "polkadot", "avax": "avalanche-2",
            "matic": "matic-network", "link": "chainlink",
            "ltc": "litecoin", "uni": "uniswap", "atom": "cosmos",
        }
        coin_id = symbol_map.get(symbol_lower, symbol_lower)

        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}"
        params = {
            "localization": "false",
            "tickers": "false",
            "community_data": "false",
            "developer_data": "false",
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    market = data.get("market_data", {})
                    price = market.get("current_price", {}).get("usd", 0)
                    change_24h = market.get("price_change_percentage_24h", 0)
                    change_7d = market.get("price_change_percentage_7d", 0)
                    market_cap = market.get("market_cap", {}).get("usd", 0)
                    volume = market.get("total_volume", {}).get("usd", 0)
                    high_24h = market.get("high_24h", {}).get("usd", 0)
                    low_24h = market.get("low_24h", {}).get("usd", 0)
                    ath = market.get("ath", {}).get("usd", 0)
                    name = data.get("name", symbol)
                    ticker = data.get("symbol", "").upper()

                    direction = "📈" if change_24h > 0 else "📉"

                    return (
                        f"{name} ({ticker}) {direction}\n"
                        f"  Price: ${price:,.2f}\n"
                        f"  24h Change: {change_24h:+.2f}%\n"
                        f"  7d Change: {change_7d:+.2f}%\n"
                        f"  24h High: ${high_24h:,.2f}\n"
                        f"  24h Low: ${low_24h:,.2f}\n"
                        f"  Market Cap: ${market_cap:,.0f}\n"
                        f"  24h Volume: ${volume:,.0f}\n"
                        f"  All-Time High: ${ath:,.2f}"
                    )
                elif resp.status == 404:
                    return f"Cryptocurrency '{symbol}' not found. Try full name like 'bitcoin' or 'ethereum'."
                return f"API error: status {resp.status}"
    except Exception as e:
        return f"Crypto price error: {e}"


async def get_crypto_list(limit: int = 20) -> str:
    """Get top cryptocurrencies by market cap."""
    try:
        url = "https://api.coingecko.com/api/v3/coins/markets"
        params = {
            "vs_currency": "usd",
            "order": "market_cap_desc",
            "per_page": min(limit, 50),
            "page": 1,
            "sparkline": "false",
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    coins = await resp.json()
                    lines = []
                    for i, coin in enumerate(coins, 1):
                        price = coin.get("current_price", 0)
                        change = coin.get("price_change_percentage_24h", 0) or 0
                        direction = "↑" if change > 0 else "↓"
                        lines.append(
                            f"  {i:>2}. {coin['symbol'].upper():<6} ${price:>12,.2f} "
                            f"{direction}{abs(change):>5.1f}% | {coin['name']}"
                        )
                    return f"Top {len(coins)} Cryptocurrencies:\n" + "\n".join(lines)
                return f"API error: {resp.status}"
    except Exception as e:
        return f"Crypto list error: {e}"


async def convert_currency(amount: float, from_currency: str, to_currency: str) -> str:
    """Convert between fiat currencies using free API."""
    try:
        from_c = from_currency.upper()
        to_c = to_currency.upper()

        url = f"https://api.exchangerate-api.com/v4/latest/{from_c}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    rates = data.get("rates", {})
                    if to_c not in rates:
                        available = ", ".join(list(rates.keys())[:20])
                        return f"Currency '{to_c}' not found. Available: {available}..."
                    rate = rates[to_c]
                    result = amount * rate
                    return (
                        f"Currency Conversion:\n"
                        f"  {amount:,.2f} {from_c} = {result:,.2f} {to_c}\n"
                        f"  Rate: 1 {from_c} = {rate:.6f} {to_c}\n"
                        f"  Source: exchangerate-api.com"
                    )
                return f"Exchange rate API error: {resp.status}"
    except Exception as e:
        return f"Currency conversion error: {e}"


async def get_exchange_rates(base: str = "USD") -> str:
    """Get current exchange rates for a base currency."""
    try:
        url = f"https://api.exchangerate-api.com/v4/latest/{base.upper()}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    rates = data.get("rates", {})
                    # Show major currencies
                    major = ["EUR", "GBP", "JPY", "CAD", "AUD", "CHF", "CNY", "INR", "BRL", "MXN", "KRW", "SGD", "HKD", "NOK", "SEK"]
                    lines = []
                    for c in major:
                        if c in rates and c != base.upper():
                            lines.append(f"  {c}: {rates[c]:.4f}")
                    return f"Exchange rates (base: {base.upper()}):\n" + "\n".join(lines)
                return f"API error: {resp.status}"
    except Exception as e:
        return f"Exchange rates error: {e}"


async def get_stock_quote(symbol: str) -> str:
    """Get stock quote information. Note: using free tier API."""
    try:
        # Using Yahoo Finance chart API (no key needed for basic data)
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol.upper()}"
        headers = {"User-Agent": "Mozilla/5.0"}

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    result = data.get("chart", {}).get("result", [{}])[0]
                    meta = result.get("meta", {})

                    price = meta.get("regularMarketPrice", 0)
                    prev_close = meta.get("previousClose", 0)
                    change = price - prev_close if prev_close else 0
                    change_pct = (change / prev_close * 100) if prev_close else 0
                    currency = meta.get("currency", "USD")
                    exchange = meta.get("exchangeName", "")
                    market_state = meta.get("marketState", "CLOSED")

                    direction = "📈" if change >= 0 else "📉"

                    return (
                        f"{symbol.upper()} {direction} ({exchange})\n"
                        f"  Price: {currency} {price:,.2f}\n"
                        f"  Change: {change:+,.2f} ({change_pct:+.2f}%)\n"
                        f"  Previous Close: {currency} {prev_close:,.2f}\n"
                        f"  Market: {market_state}"
                    )
                elif resp.status == 404:
                    return f"Stock symbol '{symbol}' not found."
                return f"Stock API error: {resp.status}"
    except Exception as e:
        return f"Stock quote error: {e}"


# ─── Unified interface ───────────────────────────────────────
async def finance_operation(operation: str, **kwargs) -> str:
    """Unified finance operations."""
    ops = {
        "crypto_price": lambda: get_crypto_price(kwargs.get("symbol", "bitcoin")),
        "crypto_list": lambda: get_crypto_list(int(kwargs.get("limit", 20))),
        "convert_currency": lambda: convert_currency(
            float(kwargs.get("amount", 1)),
            kwargs.get("from_currency", "USD"),
            kwargs.get("to_currency", "EUR"),
        ),
        "exchange_rates": lambda: get_exchange_rates(kwargs.get("base", "USD")),
        "stock": lambda: get_stock_quote(kwargs.get("symbol", "")),
    }

    handler = ops.get(operation)
    if handler:
        return await handler()
    return f"Unknown finance operation: {operation}. Available: {', '.join(ops.keys())}"
