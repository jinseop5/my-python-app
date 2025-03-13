import requests
import time
import pandas as pd
from telegram import Bot
from flask import Flask
import os

# 🔹 텔레그램 봇 정보 입력 (BotFather에서 발급)
TELEGRAM_BOT_TOKEN = "8025718450:AAHPdi-tgOhY-OqWTV8RvmN_T9betoCwpto"
TELEGRAM_CHAT_ID = "7752168245"

bot = Bot(token=TELEGRAM_BOT_TOKEN)
PORT = os.environ.get("PORT", 8080)

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

if __name__ == "__main__": 
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# 🔹 업비트 API 엔드포인트
UPBIT_TICKER_INFO_URL = "https://api.upbit.com/v1/ticker"
UPBIT_CANDLES_URL = "https://api.upbit.com/v1/candles/minutes/5"
UPBIT_MARKET_URL = "https://api.upbit.com/v1/market/all"

# 🔹 KRW 마켓의 코인 목록 (한글명 매핑)
def get_korean_ticker_names():
    response = requests.get(UPBIT_MARKET_URL)
    markets = response.json()
    
    return {market["market"]: market["korean_name"] for market in markets if market["market"].startswith("KRW")}

KOREAN_TICKER_NAMES = get_korean_ticker_names()

# 🔹 거래대금 상위 15개 코인 가져오기
def get_top_15_tickers():
    response = requests.get(UPBIT_TICKER_INFO_URL)
    data = response.json()
    
    return [x['market'] for x in sorted(data, key=lambda x: x['acc_trade_price_24h'], reverse=True)[:15] if x['market'].startswith("KRW")]

# 🔹 5분봉 데이터 가져오기
def get_candles(ticker, count=20):
    response = requests.get(UPBIT_CANDLES_URL, params={"market": ticker, "count": count})
    return response.json() if response.status_code == 200 else []

# 🔹 최근 5분 내 조건 충족 여부 확인
alert_sent = {}

def check_conditions():
    tickers = get_top_15_tickers()
    
    for ticker in tickers:
        candles = get_candles(ticker, count=20)
        if len(candles) < 20:
            continue
        
        coin_name = KOREAN_TICKER_NAMES.get(ticker, ticker)  # 한글명 없으면 티커 사용

        # 5% 이상 상승 확인
        open_price, high_price = candles[0]["opening_price"], candles[0]["high_price"]
        price_rise = (high_price - open_price) / open_price * 100

        # 거래량 400% 증가 확인
        avg_volume = sum(candle["candle_acc_trade_volume"] for candle in candles[1:]) / 19
        last_volume = candles[0]["candle_acc_trade_volume"]
        volume_spike = last_volume >= avg_volume * 4

        # 🚨 조건 충족 여부
        conditions_met = []
        if price_rise >= 5:
            conditions_met.append("📈 5% 이상 상승")
        if volume_spike:
            conditions_met.append("🔥 거래량 400% 증가")
        
        if conditions_met and (ticker not in alert_sent or time.time() - alert_sent[ticker] > 300):
            message = f"🚀 {coin_name} ({ticker})\n{' / '.join(conditions_met)} 조건 충족!\n현재 가격: {high_price}원\n거래량: {last_volume:.2f} (평균 {avg_volume:.2f})"
            bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
            alert_sent[ticker] = time.time()
            print(message)

# 🔹 봇 시작 메시지 전송
bot.send_message(chat_id=TELEGRAM_CHAT_ID, text="🚀 봇이 시작되었습니다!")

# 🔹 1분마다 실행 + 1시간마다 상태 메시지 전송
start_time = time.time()

while True:
    try:
        check_conditions()
        
        # ✅ 1시간마다 작동 확인 메시지 전송
        current_time = time.time()
        if current_time - start_time >= 3600:
            bot.send_message(chat_id=TELEGRAM_CHAT_ID, text="✅ 봇이 정상 작동 중입니다!")
            start_time = current_time  # ⏳ 1시간 기준 갱신

    except Exception as e:
        error_message = f"❌ 오류 발생: {e}"
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=error_message)
        print(error_message)

    time.sleep(60)  # ⏳ 1분마다 실행
