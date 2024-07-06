import yfinance as yf
import pandas as pd
import asyncio
from telegram import Bot
import os

bot_token = os.environ["BotToken"]
bot = Bot(token=bot_token)

# type = high or open or close, ticker = stock ticker(Yahoo.com), interval = (Candle timeframe interval and function update interval) supported intervals: 1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo
# update = update interval of the function in seconds

async def crossover_calculation(chat_id, type: str, ticker: str, interval: str, update_interval: int):

    async def send_telegram_message(chat_id, message):
        await bot.send_message(chat_id=chat_id, text=f"{ticker}: {message}")

    def get_intraday_data(ticker_symbol: str) -> pd.DataFrame:
        ticker = yf.Ticker(ticker_symbol)
        end_date = pd.Timestamp.now().normalize() + pd.DateOffset(days=1)
        start_date = end_date - pd.DateOffset(days=14)
        intraday_data = ticker.history(interval=interval, start=start_date, end=end_date)
        if intraday_data.index.tzinfo is None:
            intraday_data.index = intraday_data.index.tz_localize('America/New_York')  # Ensure timezone is New York
        else:
            intraday_data.index = intraday_data.index.tz_convert('America/New_York')
        return intraday_data[[type]]

    # Define a function to calculate SMA
    def calculate_sma(data: pd.DataFrame, window: int) -> pd.Series:
        return data[type].rolling(window=window).mean()

    # Define a function to print new data and check for SMA crossover signals
    async def print_new_data_and_signals(data: pd.DataFrame, last_timestamp: pd.Timestamp, chat_id) -> pd.Timestamp:
        if last_timestamp.tzinfo is None:
            last_timestamp = last_timestamp.tz_localize('America/New_York')
        else:
            last_timestamp = last_timestamp.tz_convert('America/New_York')

        new_data = data[data.index > last_timestamp]

        if not new_data.empty:
            # Calculate SMAs
            data['SMA20'] = calculate_sma(data, 20)
            data['SMA50'] = calculate_sma(data, 50)

            # Convert index to German timezone for display
            display_data = data[[type, 'SMA20', 'SMA50']].copy()
            display_data.index = display_data.index.tz_convert('Europe/Berlin')

            # Print new data with SMAs
            display_message = f"New Data with SMAs:\n{display_data.loc[new_data.index.tz_convert('Europe/Berlin')].to_string()}"

            # Check for crossover signals
            if len(data) >= 50:
                if data['SMA20'].iloc[-2] < data['SMA50'].iloc[-2] and data['SMA20'].iloc[-1] > data['SMA50'].iloc[-1]:
                    crossover_message = "Bullish Crossover Signal: SMA 20 crossed above SMA 50."
                    await send_telegram_message(chat_id, crossover_message)
                elif data['SMA20'].iloc[-2] > data['SMA50'].iloc[-2] and data['SMA20'].iloc[-1] < data['SMA50'].iloc[-1]:
                    crossover_message = "Bearish Crossover Signal: SMA 20 crossed below SMA 50."
                    await send_telegram_message(chat_id, crossover_message)

            # Update the last timestamp
            return new_data.index[-1]
        else:
            return last_timestamp

    ticker_symbol = ticker
    last_timestamp = pd.Timestamp.min.tz_localize('America/New_York')  # Initialize to the earliest possible timestamp with timezone

    while True:
        data = get_intraday_data(ticker_symbol)
        last_timestamp = await print_new_data_and_signals(data, last_timestamp, chat_id)
        await asyncio.sleep(update_interval)
