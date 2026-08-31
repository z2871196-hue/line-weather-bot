from flask import Flask, request

app = Flask(__name__)

@app.route("/webhook", methods=["POST"])
def webhook():
    print("收到 LINE Webhook")
    return "OK", 200

@app.route("/")
def home():
    return "LINE Weather Bot OK", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
