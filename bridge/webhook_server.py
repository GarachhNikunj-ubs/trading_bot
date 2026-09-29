import os
import json
import logging
from datetime import datetime
from flask import Flask, request, jsonify

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("AlgoBridge")

app = Flask(__name__)
AUTH_TOKEN = os.getenv("WEBHOOK_SECRET", "ALPHA_SECRET_KEY_987")

# Paper trading state file
PAPER_FILE = os.path.join(os.path.dirname(__file__), "..", "results", "paper_orders.json")

def record_paper_trade(order_data: dict):
    os.makedirs(os.path.dirname(PAPER_FILE), exist_ok=True)
    orders = []
    if os.path.exists(PAPER_FILE):
        try:
            with open(PAPER_FILE, "r") as f:
                orders = json.load(f)
        except Exception:
            orders = []
    orders.append(order_data)
    with open(PAPER_FILE, "w") as f:
        json.dump(orders, f, indent=2)

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ONLINE", "timestamp": datetime.now().isoformat()}), 200

@app.route('/webhook', methods=['POST'])
def handle_tradingview_alert():
    """
    Receives alerts from Pine Script v6 strategies (TradingView Webhook)
    Dispatches to broker API (Dhan / FYERS / Angel One) or Paper Trading engine.
    """
    payload = request.get_json(silent=True)
    if not payload:
        return jsonify({"error": "Empty or invalid JSON payload"}), 400

    secret = payload.get("secret")
    if secret != AUTH_TOKEN:
        logger.warning(f"Unauthorized webhook attempt with secret: {secret}")
        return jsonify({"error": "Unauthorized request"}), 401

    action = payload.get("action")   # BUY / SELL / CLOSE_LONG / CLOSE_SHORT
    symbol = payload.get("symbol", "NIFTY")
    qty = payload.get("qty", 1)
    sl = payload.get("sl")
    price = payload.get("price")
    strategy = payload.get("strategy", "Quantitative Suite")

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logger.info(f"[ORDER RECEIVED] -> Strat: {strategy} | Action: {action} | Ticker: {symbol} | Qty: {qty} | SL: {sl} | Price: {price}")

    order_record = {
        "timestamp": timestamp,
        "strategy": strategy,
        "symbol": symbol,
        "action": action,
        "qty": qty,
        "sl": sl,
        "price": price,
        "status": "FILLED_PAPER"
    }

    # Dispatch to Broker API if keys are provided, else log to Paper Trading ledger
    # Example for Dhan / Fyers / Angel One:
    broker = os.getenv("BROKER", "PAPER")
    if broker.upper() == "DHAN":
        # dhan_client.place_order(...)
        order_record["status"] = "DISPATCHED_DHAN"
    elif broker.upper() == "FYERS":
        # fyers_client.place_order(...)
        order_record["status"] = "DISPATCHED_FYERS"
    else:
        record_paper_trade(order_record)

    return jsonify({
        "status": "SUCCESS",
        "mode": broker,
        "dispatched": action,
        "symbol": symbol,
        "timestamp": timestamp
    }), 200

if __name__ == '__main__':
    port = int(os.getenv("PORT", 5000))
    logger.info(f"Starting Quantitative Algorithmic Suite Webhook Server on port {port}...")
    app.run(host='0.0.0.0', port=port)
