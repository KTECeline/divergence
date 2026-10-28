from flask import Flask, jsonify

app = Flask(__name__)


def invoice_total(items):
    return round(sum(i["qty"] * i["price"] for i in items), 2)


@app.get("/health")
def health():
    return jsonify(status="ok")


if __name__ == "__main__":
    app.run(port=8000)
