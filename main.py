import requests
import time
from telegram import Bot
import os

# 🔹 텔레그램 봇 정보 입력
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "YOUR_CHAT_ID")

bot = Bot(token=TELEGRAM_BOT_TOKEN)

# 🔹 업비트 API 엔드포인트
UPBIT_TICKER_INFO_URL = "https://api.upbit.com/v1/ticker"
UPBIT_CANDLES_URL = "https://api.upbit.com/v1/candles/minutes/5"
UPBIT_MARKET_URL = "https://api.upbit.com/v1/market/all"

# 🔹 KRW 마켓의 코인 목록 (한글명 매핑)
def get_korean_ticker_names():
    try:
        response = requests.get(UPBIT_MARKET_URL)
        response.raise_for_status()
        markets = response.json()
        
        return {
            market["market"]: market["korean_name"]
            for market in markets if market["market"].startswith("KRW")
        }
    except Exception as e:
        print(f"❌ 업비트 티커 목록 가져오기 오류: {e}")
        return {}

KOREAN_TICKER_NAMES = get_korean_ticker_names()

# 🔹 거래대금 상위 15개 코인 가져오기
def get_top_15_tickers():
    try:
        response = requests.get(UPBIT_TICKER_INFO_URL)
        response.raise_for_status()
        data = response.json()

        sorted_tickers = sorted(data, key=lambda x: x['acc_trade_price_24h'], reverse=True)
        return [x['market'] for x in sorted_tickers[:15] if x['market'].startswith("KRW")]
    except Exception as e:
        print(f"❌ 거래대금 상위 코인 가져오기 오류: {e}")
        return []

# 🔹 5분봉 데이터 가져오기
def get_candles(ticker, count=20):
    try:
        params = {"market": ticker, "count": count}
        response = requests.get(UPBIT_CANDLES_URL, params=params)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"❌ {ticker} 캔들 데이터 가져오기 오류: {e}")
        return []

# 🔹 최근 5분 내 조건 충족 여부 확인
alert_sent = {}

def check_conditions():
    tickers = get_top_15_tickers()
    for ticker in tickers:
        candles = get_candles(ticker, count=20)
        if len(candles) < 20:
            continue

        # 코인 한글명 가져오기
        coin_name = KOREAN_TICKER_NAMES.get(ticker, ticker)

        # 가격 변동률 계산 (5% 이상 상승 체크)
        open_price = candles[0]["opening_price"]
        high_price = candles[0]["high_price"]
        price_rise = (high_price - open_price) / open_price * 100

        # 거래량 급증 체크 (400% 이상 증가)
        avg_volume = sum(candle["candle_acc_trade_volume"] for candle in candles[1:]) / 19
        last_volume = candles[0]["candle_acc_trade_volume"]
        volume_spike = last_volume >= avg_volume * 4

        # 🚨 조건 충족 여부 확인
        conditions_met = []
        if price_rise >= 5:
            conditions_met.append("📈 5% 이상 상승")
        if volume_spike:
            conditions_met.append("🔥 거래량 400% 증가")

        if conditions_met and (ticker not in alert_sent or time.time() - alert_sent[ticker] > 300):
            message = (
                f"🚀 {coin_name} ({ticker})\n"
                f"{' / '.join(conditions_met)} 조건 충족!\n"
                f"현재 가격: {high_price}원\n"
                f"거래량: {last_volume:.2f} (평균 {avg_volume:.2f})"
            )
            try:
                bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
                print(f"✅ 메시지 전송 성공: {message}")
            except Exception as e:
                print(f"❌ 텔레그램 메시지 전송 오류: {e}")
            
            alert_sent[ticker] = time.time()

# 🔹 봇 시작 메시지 전송
try:
    bot.send_message(chat_id=TELEGRAM_CHAT_ID, text="🚀 봇이 시작되었습니다!")
    print("✅ 텔레그램 봇 시작 메시지 전송 성공")
except Exception as e:
    print(f"❌ 텔레그램 봇 시작 메시지 오류: {e}")

# 🔹 1분마다 실행 + 1시간마다 상태 메시지 전송
start_time = time.time()

while True:
    try:
        check_conditions()

        # ⏳ 1시간마다 작동 확인 메시지 전송
        if time.time() - start_time >= 3600:
            try:
                bot.send_message(chat_id=TELEGRAM_CHAT_ID, text="✅ 봇이 정상 작동 중입니다!")
                print("✅ 1시간마다 상태 메시지 전송 성공")
            except Exception as e:
                print(f"❌ 상태 메시지 전송 오류: {e}")
            start_time = time.time()
    
    except Exception as e:
        error_message = f"❌ 오류 발생: {e}"
        print(error_message)
        try:
            bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=error_message)
        except:
            print("❌ 텔레그램 메시지 전송 실패")
    
    time.sleep(60)  # 1분마다 실행
