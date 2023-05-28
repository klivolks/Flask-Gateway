from flask import Flask, request, jsonify
from flask_cors import CORS
from daba.Mongo import collection
from werkzeug.exceptions import HTTPException
import requests
import os
import logging.config
from dotenv import load_dotenv

load_dotenv()
logging.config.fileConfig('logging.ini')

app = Flask(__name__)
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True
app.config.update(
    SECRET_KEY=os.getenv('SECRET_KEY')
)
CORS(app, expose_headers="content-disposition", supports_credentials=True)
db = collection('apis')


@app.route("/")
def hello():
    return "<h1>Welcome to API gateway!</h1><p>This serves as the gateway to other micro-services</p>"


@app.route('/api/v1/<service>/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE'])
def processAPI(service, path):
    try:
        data = db.getAfterCount({"Status": 1, "Service": service}, "CallCount")
        if not data:
            raise HTTPException(description="Service not found", status_code=404)

        auth_header = request.headers.get('Authorization')
        headers = {'X-API-Key': data.get('Key'), 'Referer': 'Gateway', 'Authorization': auth_header}
        url = f'{data.get("Url")}/{path}'
        content_type = request.headers.get('Content-Type')

        if content_type == 'application/json':
            response = requests.request(request.method, url, headers=headers, json=request.json)
        else:
            response = requests.request(request.method, url, headers=headers, data=request.form)

        response.raise_for_status()
        return response.text, response.status_code

    except HTTPException as http:
        logging.error(http)
        return jsonify({"error": http.description}), http.code

    except Exception as e:
        logging.error(e)
        return jsonify({"error": "An error occurred processing your request"}), 500


def run():
    app.run(host="0.0.0.0", port=os.getenv('PORT', 5001), debug=True, load_dotenv='development')


if __name__ == "__main__":
    run()
