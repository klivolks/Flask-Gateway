import traceback
from markupsafe import escape

from environment import config_name
import datetime
import logging.config
import os
import time
import httpx
import threading
from markupsafe import escape

from daba.Mongo import collection
from flask import Flask, request, jsonify, g
from flask_cors import CORS
from werkzeug.exceptions import HTTPException
from werkzeug.local import LocalProxy

from APIVerification import APIVerification

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


@app.route("/")
def hello():
    return "<h1>Welcome to API gateway!</h1><p>This serves as the gateway to other micro-services</p>", 200


@app.route('/api/v1/<service>/', methods=['GET', 'POST', 'PUT', 'DELETE'])
async def processHome(service):
    try:
        api_verification = APIVerification()

        if not api_verification.verify_request():
            return jsonify({"error": "Invalid API key or Referer, or monthly limit exceeded"}), 403

        data = db.getAfterCount({"Service": service}, "CallCount")
        if not data:
            return jsonify({"error": "Requested service not found"}), 404

        auth_header = request.headers.get('Authorization')
        headers = {'X-API-Key': data.get('Key'), 'Referer': 'Gateway'}
        if auth_header:
            headers["Authorization"] = auth_header

        content_type = request.headers.get('Content-Type')
        if content_type:
            headers['Content-Type'] = content_type

        url = f'{data.get("Url")}'
        params = None
        if request.method.lower() == "get":
            # Apply `escape` to each query parameter
            params = {key: escape(value) for key, value in request.args.items()}

        async with httpx.AsyncClient() as client:
            if request.headers.get('Content-Type') == 'application/json':
                response = await client.request(request.method, url, headers=headers, params=params, json=request.json)
            else:
                response = await client.request(request.method, url, headers=headers, params=params, data=request.form)

        end_time = time.time()
        execution_time = end_time - start_time

        # Update api_logs collection
        if os.environ.get('DB_LOG') and os.environ.get('DB_LOG') == 'on':
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
        if status == "unhealthy":
            db.set({"_id": data["_id"]}, {"Status": status, "LastChecked": datetime.datetime.now()})
        return response.text, response.status_code

    except HTTPException as http:
        logging.error(http)
        return jsonify({"error": http.description}), http.code

    except Exception as e:
        logging.error(traceback.format_exc())
        return jsonify({"error": "An error occurred processing your request"}), 500


@app.route('/api/v1/<service>/swagger')
async def processSwagger(service):
    try:
        data = db.getAfterCount({"Service": service}, "CallCount")
        if not data:
            return jsonify({"error": "Requested service not found"}), 404
        url = f'{data.get("Url")}swagger'

        async with httpx.AsyncClient(timeout=120.0) as client:
             response = await client.request(request.method, url)

        return response
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({"error": "An error occurred processing your request"}), 500


@app.route('/api/v1/<service>/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE'])
async def processAPI(service, path):
    try:
        api_verification = APIVerification()

        if not api_verification.verify_request():
            return jsonify({"error": "Invalid API key or Referer, or monthly limit exceeded"}), 403

        data = db.getAfterCount({"Service": service}, "CallCount")
        if not data:
            return jsonify({"error": "Requested service not found"}), 404

        headers = {'X-API-Key': data.get('Key'), 'Referer': 'Gateway'}

        content_type = request.headers.get('Content-Type')
        if content_type:
            headers['Content-Type'] = content_type

        url = f'{data.get("Url")}{path}'
        params = request.args if request.method.lower() == "get" else None
        async with httpx.AsyncClient(timeout=120.0) as client:
            if request.headers.get('Content-Type') == 'application/json':
                response = await client.request(request.method, url, headers=headers, params=params, json=request.json)
            else:
                response = await client.request(request.method, url, headers=headers, params=params, data=request.form)

        # Note: In the case of file uploads, additional handling will be needed.

        end_time = time.time()
        execution_time = end_time - start_time

        # Update api_logs collection
        if os.environ.get('DB_LOG') and os.environ.get('DB_LOG') == 'on':
            api_logs = collection('api_logs')
            log_data = {
                "RequestTime": datetime.datetime.fromtimestamp(int(start_time)),
                "ResponseTime": datetime.datetime.fromtimestamp(int(end_time)),
                "API": data["_id"],
                "ExecutionTime": execution_time  # seconds
            }
            api_logs.put(log_data)

        # Update apis collection
        status = 'healthy' if response.status_code < 500 else 'unhealthy'
        if status == "unhealthy":
            db.set({"_id": data["_id"]}, {"Status": status, "LastChecked": datetime.datetime.now()})

        return response.text, response.status_code

    except Exception as e:
        print(traceback.format_exc())
        return jsonify({"error": "An error occurred processing your request"}), 500


@app.errorhandler(404)
def app_handler(param=404):
    return jsonify({"error": 'The requested service not found'}), 404


async def health_check():
    """
    This function is part of health check which run a thread to check api health every 6 hours and if fails it will
    change the flag to unhealthy in database
    :return:
    """
    while True:
        time.sleep(21600)  # sleep for 6 hours
        apis = db.get({})
        for api in apis:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(api["Url"])
                status = 'healthy' if response.status_code < 500 else 'unhealthy'
                db.set({"_id": api["_id"]}, {"Status": status, "LastChecked": datetime.datetime.now()})
            except Exception as e:
                logging.error(e)


def run():
    if os.environ.get('HEALTH_CHECK') and os.environ.get('HEALTH_CHECK') == 'on':
        health_check_thread = threading.Thread(target=health_check, daemon=True)
        health_check_thread.start()
    app.run(host=os.getenv('HOST'), port=os.getenv('PORT'))


if __name__ == "__main__":
    run()
