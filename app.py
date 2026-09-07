from flask import Flask, request
import os
import hmac
import hashlib
import base64
import json
import requests
import time
import random

app = Flask(__name__)

CHANNEL_SECRET = os.environ.get("LINE_CHANNEL_SECRET")
CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")

# Cloudinary
CLOUDINARY_CLOUD_NAME = os.environ.get("CLOUDINARY_CLOUD_NAME")
CLOUDINARY_API_KEY = os.environ.get("CLOUDINARY_API_KEY")
CLOUDINARY_API_SECRET = os.environ.get("CLOUDINARY_API_SECRET")

# Cloudinary 抽卡資料夾
CARD_FOLDER = "cards"

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


def get_cards():
    """
    取得 Cloudinary cards 資料夾裡所有圖片＋影片
    超過 500 個會自動繼續抓
    """

    url = "https://api.cloudinary.com/v1_1/" + CLOUDINARY_CLOUD_NAME + "/resources/by_asset_folder"

    cards = []
    next_cursor = None

    while True:

        params = {
            "asset_folder": CARD_FOLDER,
            "max_results": 500
        }

        if next_cursor:
            params["next_cursor"] = next_cursor

        response = requests.get(
            url,
            params=params,
            auth=(CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET),
            timeout=20
        )

        print("Cloudinary 回覆：", response.status_code)

        if response.status_code != 200:
            print("Cloudinary 錯誤：", response.text)
            return []

        data = response.json()

        for asset in data.get("resources", []):

            resource_type = asset.get("resource_type")
            secure_url = asset.get("secure_url")

            if not secure_url:
                continue

            # 圖片
            if resource_type == "image":

                cards.append({
                    "type": "image",
                    "url": secure_url
                })

            # 影片
            elif resource_type == "video":

                # Cloudinary 自動從影片第 0 秒產生 JPG 預覽圖
                preview_url = secure_url.replace(
                    "/video/upload/",
                    "/video/upload/w_600,q_auto,so_0/"
                )

                # 把影片副檔名改成 jpg
                if "." in preview_url:
                    preview_url = preview_url.rsplit(".", 1)[0] + ".jpg"

                cards.append({
                    "type": "video",
                    "url": secure_url,
                    "preview": preview_url
                })

        next_cursor = data.get("next_cursor")

        if not next_cursor:
            break

    print("目前抽卡池數量：", len(cards))

    return cards


def draw_card(reply_token):

    cards = get_cards()

    if not cards:
        print("抽卡池沒有找到圖片或影片")
        return

    card = random.choice(cards)

    print("抽到：", card)

    # 抽到圖片
    if card["type"] == "image":

        reply_message(
            reply_token,
            {
                "type": "image",
                "originalContentUrl": card["url"],
                "previewImageUrl": card["url"]
            }
        )

    # 抽到影片
    elif card["type"] == "video":

        reply_message(
            reply_token,
            {
                "type": "video",
                "originalContentUrl": card["url"],
                "previewImageUrl": card["preview"]
            }
        )


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

        # =========================
        # 雷達
        # =========================

        if text in [
            "雷達",
            "雨量",
            "下雨",
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

        # =========================
        # 看看老婆
        # =========================

        elif text == "看看老婆":

            draw_card(reply_token)

    return "OK", 200


@app.route("/")
def home():
    return "LINE Weather Bot OK", 200


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8080))
    )
