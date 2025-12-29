# Lit Token Bot

A Python bot that TRACKS the appearance of the **LIT token** on the **Lighter exchange**. Once the token appears, the bot automatically BUYS and ***optional SENDS a notification to a Telegram bot***.

---

## Features

- Monitors the Lighter exchange for the LIT token.
- Automatically purchases the token as soon as it is listed.
- Sends real-time notifications to a Telegram chat (**OPTIONAL**).

---

## Requirements

Install the necessary dependencies listed in `req.txt`:

```bash
pip install -r req.txt
```

---

## Configuration

The bot requires two configuration files:

1. envLit.py

This file contains your system and exchange settings. Example:

```python
TG_TOKEN = "your_telegram_bot_token" or ""       # Telegram bot token
CHAT_ID = "your_telegram_chat_id" or ""          # Telegram chat ID for notifications
L1_ADDRESS = "your_lighter_wallet_address" # Wallet address on Lighter
API_KEY_PRIVATE_KEY = "your_lighter_api_private_key"  # Private API key from Lighter
API_KEY_PUBLIC_KEY = "your_lighter_api_public_key"    # Public API key from Lighter
ACCOUNT_INDEX = 0                           # API account index
API_KEY_INDEX = 0                           # API key index
```

| Make sure to replace all placeholders with your actual keys.

3. orders.txt

This file defines the orders the bot should place. Each line should contain:

```code
<price> <amount_in_usd>
```

- <price> - the price at which to place the order.
- <amount_in_usd> - the amount in USD to buy at that price.

Example:

```code
2 100
2.5 200
3 150
```

2. req.txt

This file contains the Python dependencies required for the project. Install them with:

```bash
pip install -r req.txt
```

---

## Usage

Run the bot with:

```bash
python lit.py
```

- The bot will start monitoring the Lighter exchange.
- When the LIT token appears, it will automatically place orders from orders.txt and send Telegram notifications.
- To stop the bot at any time, press Control + C.

---

## Notes

- Ensure your Telegram bot token and chat ID are correct for notifications.
- If you do not want to use Telegram notifications, ***you can leave TG_TOKEN and CHAT_ID empty ("") if you don't need notifications***.
- Make sure orders.txt is correctly formatted with one order per line.
- Use a secure environment for storing API keys and sensitive information.