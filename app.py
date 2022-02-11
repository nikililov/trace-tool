import sys
from typing import Dict
from flask import Flask, jsonify, request, make_response
from trace_tool import TraceTool

app = Flask(__name__)
PARAMS: Dict = {}


@app.route("/request", methods=['GET'])
def get_params():
    global PARAMS
    return jsonify(PARAMS)


@app.route("/request", methods=['POST'])
def run_trace():
    global PARAMS

    try:
        PARAMS = request.get_json()
        trace = TraceTool(PARAMS)
        trace.run()
    except Exception as e:
        return f"Can not process: {e}", 400

    return "DONE", 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
