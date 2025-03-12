import requests
import time
import pandas as pd
from telegram import Bot

# 🔹 텔레그램 봇 정보 입력 (BotFather에서 발급)
TELEGRAM_BOT_TOKEN = "8025718450:AAHPdi-tgOhY-OqWTV8RvmN_T9betoCwpto"
TELEGRAM_CHAT_ID = "7752168245"

bot = Bot(token=TELEGRAM_BOT_TOKEN)

# 🔹 업비트 API 엔드포인트
UPBIT_TICKER_INFO_URL = "https://api.upbit.com/v1/ticker"
UPBIT_CANDLES_URL = "https://api.upbit.com/v1/candles/minutes/5"

# 🔹 거래대금 상위 15개 코인 가져오기
def get_top_15_tickers():
    response = requests.get(UPBIT_TICKER_INFO_URL)
    data = response.json()
    
    sorted_tickers = sorted(data, key=lambda x: x['acc_trade_price_24h'], reverse=True)
    top_15_tickers = [x['market'] for x in sorted_tickers[:15] if x['market'].startswith("KRW")]
    
    return top_15_tickers

# 🔹 5분봉 데이터 가져오기
def get_candles(ticker, count=20):
    params = {"market": ticker, "count": count}
    response = requests.get(UPBIT_CANDLES_URL, params=params)
    
    if response.status_code != 200:
        return []
    
    return response.json()

# 🔹 최근 5분 내 조건 충족 여부 확인
alert_sent = {}

def check_conditions():
    tickers = get_top_15_tickers()
    for ticker in tickers:
        candles = get_candles(ticker, count=20)
        
        if len(candles) < 20:
            continue
        
        # 5분봉 기준 시가 대비 고가 5% 이상 상승 확인
        first_candle = candles[0]
        open_price = first_candle["opening_price"]
        high_price = first_candle["high_price"]
        if (high_price - open_price) / open_price * 100 >= 5:
            if ticker not in alert_sent or time.time() - alert_sent[ticker] > 300:
                message = f"🚀 {ticker} 5분봉 기준 시가 대비 고가 5% 이상 상승!\n현재 가격: {high_price}원"
                bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
                alert_sent[ticker] = time.time()
                print(message)
        
        # 5분봉 기준 20봉 내 평균 거래량 대비 400% 이상 증가 확인
        avg_volume = sum(candle["candle_acc_trade_volume"] for candle in candles[:-1]) / 19
        last_volume = candles[0]["candle_acc_trade_volume"]
        if last_volume >= avg_volume * 4:
            if ticker not in alert_sent or time.time() - alert_sent[ticker] > 300:
                message = f"🔥 {ticker} 거래량 급증! (400% 이상 증가)\n현재 거래량: {last_volume:.2f}, 평균 거래량: {avg_volume:.2f}"
                bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
                alert_sent[ticker] = time.time()
                print(message)

# 🔹 1분마다 실행
while True:
    try:
        check_conditions()
    except Exception as e:
        print(f"에러 발생: {e}")
    
    time.sleep(60)  # 1분마다 실행
