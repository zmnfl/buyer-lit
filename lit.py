import asyncio
import re
from datetime import datetime

from cors.lighter import Lighter
from tg.tgBot import TelegramClient

from envLit import *

# core init
lighter = Lighter(LighterConfig)
tg = TelegramClient(TG_TOKEN)

MAIN_TICKER = ['DOGE', 'SKY', 'AI16Z', 'FARTCOIN', 'NEAR', 'WIF', 'KAITO', 'MORPHO', 'NVDA', 'MSFT', 'NZDUSD', 'ICP', 'CRV', 'ADA', 'ENA', 'HOOD', 'SYRUP', 'JUP', 'PENGU', 'LINK', 'ARB', 'OP', '1000BONK', 'BCH', 'PAXG', 'STRK', 'USDKRW', 'MKR', 'COIN', 'BNB', 'TON', 'AUDUSD', 'AAPL', 'VIRTUAL', '0G', 'FIL', 'APEX', '1000FLOKI', '1000PEPE', 'TIA', 'NMR', '1000TOSHI', 'RESOLV', 'VVV', 'META', 'EURUSD', 'LTC', 'BERA', 'MON', 'PYTH', 'GRASS', 'FF', 'ETHFI', 'WLFI', 'USDJPY', 'SOL', 'SPX', 'BTC', 'HYPE', 'S', 'AVAX', 'GBPUSD', 'IP', 'UNI', 'EIGEN', 'POL', 'EDEN', 'PENDLE', 'DYDX', 'XPL', 'SUI', 'AERO', 'XAG', 'ETH', 'DOT', 'GOOGL', 'AVNT', 'USELESS', 'MEGA', 'WLD', 'AMZN', 'ASTER', 'USDCAD', 'CC', 'XMR', 'HBAR', 'ZEC', 'TRUMP', 'DOLO', 'LAUNCHCOIN', 'STBL', 'MYX', 'LDO', '2Z', 'PROVE', 'SEI', 'XAU', 'GMX', 'CRO', 'YZY', 'MET', '1000SHIB', 'LINEA', 'ZORA', 'USDCHF', 'TSLA', 'PUMP', 'TRX', 'TAO', 'ZRO', 'ZK', 'POPCAT', 'XRP', 'ONDO', 'MNT', 'PLTR', 'AAVE', 'APT', 'ETH/USDC']

candle_count = 0

orders = []

async def send_tx(market_id, size_decimals, price_decimals, size, price):
    try:
        name, status, elapsed, api_response = await lighter.create_limit_order(
            market_id,
            size,
            price,
            True,
            size_decimals,
            price_decimals
        )

        if status == 200:
            print(f"\n{name.upper()}: {status} - ms: {elapsed * 1000:.2f} - return: {api_response}")
        else:
            name, status, elapsed, api_response = await lighter.create_limit_order(
                market_id,
                size,
                price,
                True,
                size_decimals,
                price_decimals
            )
            print(f"\n{name.upper()}: {status} - ms: {elapsed * 1000:.2f} - return: {api_response}")

        return name, status, elapsed, api_response
    except Exception as e:
        return "send_tx", 404, 0, e
    
async def plase_orders(market_id, size_decimals, price_decimals):
    tasks = [send_tx(market_id, size_decimals, price_decimals, round(float(order[1])/float(order[0]),1), float(order[0])) for order in orders]
    await asyncio.gather(*tasks)

def ticker_check(ticker):
    global MAIN_TICKER

    ticker_up = ticker.upper()

    if ticker_up not in MAIN_TICKER:
        MAIN_TICKER.append(ticker_up)
        ticker_part = ticker_up.split('/', 1)[0]

        pattern = r"^L?(I?(G?(H?(T?(E?R?)?)?)?)?)?$|^LIT.*$"

        if re.match(pattern, ticker_part):
            return 0
        return 1
    return 2

async def check_markets():
    global candle_count
    while True:
        try:
            _, spots_markets = await lighter.get_orderBook()

            for item in spots_markets:
                res_check = ticker_check(item["symbol"])
                if res_check == 0:
                    print( f"MAYBE MEM - TOKEN NAME: {item['symbol']}")
                    asyncio.create_task(tg.send_message(CHAT_ID, f"MAYBE MEM\nTOKEN NAME: {item['symbol']}"))
                    await plase_orders(item["market_id"], item["size_decimals"], item["price_decimals"])
                    return
                
                elif res_check == 1:
                    print( f"NEW TICKER - TOKEN NAME: {item['symbol'].upper()}")
                    asyncio.create_task(tg.send_message(CHAT_ID, f"NEW TICKER\nTOKEN NAME: {item['symbol']}"))

            candle_count += 1
        
        except Exception as e:
            print( f"check_markets: {e}")
        finally:
            await asyncio.sleep(1)

async def monitor_candles(interval: int = 1200):
    global candle_count
    while True:
        await asyncio.sleep(interval)
        if candle_count == 0:
            print( f"{datetime.now()} - WARNING - ❌")
        else:
            print( f"{datetime.now()} - WARNING - ✅ Candle: {candle_count}")

        candle_count = 0

def get_orders():
    res = []

    with open("orders.txt", "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                elements = line.split()[:2]
                res.append(elements)
    return res

async def main():
    print("🔹 Start...\n")

    orders = get_orders()
    print(orders[0])

    await asyncio.gather(
        lighter.init_session()
    )

    asyncio.create_task(monitor_candles())

    await check_markets()
    await lighter.close()



if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⛔ Its all")
