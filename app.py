import traceback
from flask import Flask, request, jsonify, g
from flask_cors import CORS
from daba.Mongo import collection
import threading
import time
import datetime
from werkzeug.local import LocalProxy
from werkzeug.exceptions import HTTPException
import requests
import os
import logging.config
from dotenv import load_dotenv

from APIVerification import APIVerification

load_dotenv()
current_dir = os.path.dirname(os.path.abspath(__file__))
log_file = os.path.join(current_dir, 'logging.ini')
logging.config.fileConfig(log_file)

app = Flask(__name__)
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True
app.config.update(
    SECRET_KEY=os.getenv('SECRET_KEY')
)
CORS(app, expose_headers="content-disposition", supports_credentials=True)
db = collection('apis')


# Use LocalProxy to access the request start time
def get_start_time():
    return getattr(g, '_start_time', None)


start_time = LocalProxy(get_start_time)


@app.before_request
def before_request():
    g._start_time = time.time()


@app.route("/api/v1/")
def hello():
    return "<h1>Welcome to API gateway!</h1><p>This serves as the gateway to other micro-services</p>", 200


@app.route('/api/v1/<service>/', methods=['GET', 'POST', 'PUT', 'DELETE'])
def processHome(service):
    try:
        api_verification = APIVerification()

        if not api_verification.verify_request():
            return jsonify({"error": "Invalid API key or Referer, or monthly limit exceeded"}), 403

        data = db.getAfterCount({"Status": 'healthy', "Service": service}, "CallCount")
        if not data:
            return jsonify({"error": "Requested service not found"}), 404

        auth_header = request.headers.get('Authorization')
        headers = {'X-API-Key': data.get('Key'), 'Referer': 'Gateway', 'Authorization': auth_header,
                   'Content-Type': request.headers.get('Content-Type')}
        url = f'{data.get("Url")}'
        content_type = request.headers.get('Content-Type')

        if content_type == 'application/json':
            response = requests.request(request.method, url, headers=headers, json=request.json)
        else:
            response = requests.request(request.method, url, headers=headers, data=request.form)

        end_time = time.time()
        execution_time = end_time - start_time

        # Update api_logs collection
        api_logs = collection('api_logs')
        log_data = {
            "RequestTime": datetime.datetime.fromtimestamp(int(start_time)),
            "ResponseTime": datetime.datetime.fromtimestamp(int(end_time)),
            "API": data["_id"],
            "ExecutionTime": execution_time
        }
        api_logs.put(log_data)

        # Update apis collection
        status = 'healthy' if response.status_code < 500 else 'unhealthy'
        db.set({"_id": data["_id"]}, {"Status": status, "LastChecked": datetime.datetime.now()})
        return response.text, response.status_code

    except HTTPException as http:
        logging.error(http)
        return jsonify({"error": http.description}), http.code

    except Exception as e:
        logging.error(traceback.format_exc())
        return jsonify({"error": "An error occurred processing your request"}), 500


@app.route('/api/v1/<service>/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE'])
def processAPI(service, path):
    try:
        api_verification = APIVerification()

        if not api_verification.verify_request():
            return jsonify({"error": "Invalid API key or Referer, or monthly limit exceeded"}), 403

        data = db.getAfterCount({"Status": 'healthy', "Service": service}, "CallCount")
        if not data:
            return jsonify({"error": "Requested service not found"}), 404

        auth_header = request.headers.get('Authorization')
        headers = {'X-API-Key': data.get('Key'), 'Referer': 'Gateway'}
        url = f'{data.get("Url")}{path}'
        content_type = request.headers.get('Content-Type')

        if auth_header is not None:
            headers["Authorization"] = auth_header

        if content_type == 'application/json':
            response = requests.request(request.method, url, headers=headers, json=request.json)
        else:
            print("headers", headers)
            print("request.form", request.form)
            response = requests.request(request.method, url, headers=headers, data=request.form, files=request.files)

        end_time = time.time()
        execution_time = end_time - start_time

        # Update api_logs collection
        api_logs = collection('api_logs')
        log_data = {
            "RequestTime": datetime.datetime.fromtimestamp(int(start_time)),
            "ResponseTime": datetime.datetime.fromtimestamp(int(end_time)),
            "API": data["_id"],
            "ExecutionTime": execution_time
        }
        api_logs.put(log_data)

        # Update apis collection
        status = 'healthy' if response.status_code < 500 else 'unhealthy'
        db.set({"_id": data["_id"]}, {"Status": status, "LastChecked": datetime.datetime.now()})
        return response.text, response.status_code

    except HTTPException as http:
        logging.error(http)
        return jsonify({"error": http.description}), http.code

    except Exception as e:
        logging.error(traceback.format_exc())
        return jsonify({"error": "An error occurred processing your request"}), 500


@app.errorhandler(404)
def app_handler(param=404):
    return jsonify({"error": 'The requested service not found'}), 404


def health_check():
    while True:
        time.sleep(2 * 60 * 60)  # sleep for 2 hours
        apis = db.get({})
        for api in apis:
            try:
                response = requests.get(api["Url"])
                status = 'healthy' if response.ok else 'unhealthy'
                db.set({"_id": api["_id"]}, {"Status": status, "LastChecked": datetime.datetime.now()})
            except Exception as e:
                logging.error(e)


def run():
    load_dotenv()
    health_check_thread = threading.Thread(target=health_check, daemon=True)
    health_check_thread.start()
    app.run(host=os.getenv('HOST'), port=os.getenv('PORT'), debug=True, load_dotenv='development')


if __name__ == "__main__":
    run()
