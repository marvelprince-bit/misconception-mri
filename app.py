"""Misconception MRI in the browser.

    pip install -r requirements.txt
    python app.py            # then open http://127.0.0.1:5000

Runs the same engine as the tests and evaluations. With ANTHROPIC_API_KEY set, live Claude
is offered as the AI rule-writer; without it, a saved live Claude run is replayed.
"""
from __future__ import annotations

from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

from mri import scan

WEB = Path(__file__).resolve().parent / "web"
app = Flask(__name__)
app.json.sort_keys = False  # keep topics in teaching order: negatives, then fractions


@app.get("/")
def index():
    return send_from_directory(WEB, "index.html")


@app.get("/api/catalogue")
def catalogue():
    return jsonify({"topics": scan.catalogue(), "writers": scan.ai_writers()})


@app.post("/api/scan")
def run_scan():
    body = request.get_json(force=True)
    try:
        return jsonify(scan.scan(body["student"], hide=bool(body.get("hide")),
                                 writer=body.get("writer", "replay"), seed=int(body.get("seed", 7))))
    except KeyError:
        return jsonify({"error": "Choose a student first."}), 400


@app.post("/api/start")
def start():
    return jsonify(scan.start(request.get_json(force=True).get("topic", "integers")))


@app.post("/api/answer")
def answer():
    body = request.get_json(force=True)
    return jsonify(scan.answer(body.get("sid", ""), body.get("answer", "")))


if __name__ == "__main__":
    app.run(debug=False, port=5000)
