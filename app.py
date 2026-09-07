from flask import Flask, request
import os
import hmac
import hashlib
import base64
import json
import requests
import time

app = Flask(__name__)

CHANNEL_SECRET = os.environ.get("LINE_CHANNEL_SECRET")
CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")

# 中央氣象署：衛星雲圖
SATELLITE_URL = "https://cwaopendata.s3.ap-northeast-1.amazonaws.com/Observation/O-B0028-003.jpg"

# 中央氣象署：雷達整合回波圖
RADAR_URL = "https://cwaopendata.s3.ap-northeast-1.amazonaws.com/Observation/O-A0058-001.png"


def verify_signature(body, signature):
    hash_value = hmac.new(
        CHANNEL_SECRET.encode("utf-8"),
        body,
        hashlib.sha256
    ).digest()

    expected_signature = base64.b64encode(hash_value).decode("utf-8")

    return hmac.compare_digest(expected_signature, signature)


def reply_message(reply_token, message):
    url = "https://api.line.me/v2/bot/message/reply"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {CHANNEL_ACCESS_TOKEN}"
    }

    data = {
        "replyToken": reply_token,
        "messages": [message]
    }

    response = requests.post(
        url,
        headers=headers,
        json=data
    )

    print("LINE 回覆結果：", response.status_code, response.text)


@app.route("/webhook", methods=["POST"])
def webhook():

    body = request.get_data()
    signature = request.headers.get("x-line-signature", "")

    if not CHANNEL_SECRET:
        return "Channel Secret missing", 500

    if not signature or not verify_signature(body, signature):
        return "Invalid signature", 400

    data = json.loads(body)

    for event in data.get("events", []):

        if event.get("type") != "message":
            continue

        message = event.get("message", {})

        if message.get("type") != "text":
            continue

        text = message.get("text", "").strip()
        reply_token = event.get("replyToken")

        # 測試
        if text in ["測試", "test", "TEST"]:

            reply_message(
                reply_token,
                {
                    "type": "text",
                    "text": "LINE Weather Bot 正常運作中 ☁️"
                }
            )

        # 衛星雲圖
        elif text in ["衛星", "衛星雲圖", "雲圖"]:

            image_url = SATELLITE_URL + "?t=" + str(time.time())

            reply_message(
                reply_token,
                {
                    "type": "image",
                    "originalContentUrl": image_url,
                    "previewImageUrl": image_url
                }
            )

        # 雷達回波圖
        elif text in [
            "雨量",
            "下雨",
            "雷達",
            "雷達回波",
            "雷達回波圖"
        ]:

            image_url = RADAR_URL + "?t=" + str(time.time())

            reply_message(
                reply_token,
                {
                    "type": "image",
                    "originalContentUrl": image_url,
                    "previewImageUrl": image_url
                }
            )

    return "OK", 200


@app.route("/")
def home():
    return "LINE Weather Bot OK", 200


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8080))
    )
