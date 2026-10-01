"""
Flask REST API — handles JSON requests between the Next.js web app
(apps/web) and the recommendation engine.

Run with: flask --app kaziforce_api.app run
"""

from flask import Flask, jsonify

app = Flask(__name__)


@app.get("/health")
def health():
    return jsonify(status="ok")


# TODO(Sprint 3-4):
#   POST /match       -> run hybrid matching for a worker/job pair
#   GET  /explain/<id> -> return explanation for a given match

if __name__ == "__main__":
    app.run(debug=True)
