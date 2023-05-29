![Python](https://img.shields.io/badge/python-v3.7+-blue.svg)
![Docker](https://img.shields.io/badge/docker%20build-automated-066da5.svg)

# Flask-API-Gateway by Klivolks

A dynamic flask-mongo python gateway with inbuilt dual-way API Key and Referer verification. It includes a health verification feature and provides real-time status updates to help you monitor and analyze the condition of your microservices.

This tool is designed to integrate with your existing application, enhancing its functionality and making your work easier. The gateway was initially used in Klivolks's flagship product, iCorp, and is now publicly available under the GNU v3 license.

## Getting Started

These instructions will guide you on how to set up and run the project on your local machine for development and testing purposes.

### Prerequisites

- Docker installed on your machine. You can get Docker [here](https://www.docker.com/products/docker-desktop).
- MongoDB URL and Database name. Visit [MongoDB Cloud](https://www.mongodb.com/cloud) if you need to set up a MongoDB database.

### Installation

- Pull the Docker image using the following command: 
```sh
docker pull klivolks/klivolks-api-gateway:1.0.2
```
- Docker will automatically clone the latest release from the repository:
```sh
git clone https://github.com/klivolks/Flask-Gateway
```
- Docker will also rename `.env-example` to `.env` and automatically generate a flask secret key.
- You will need to set your MongoDB URL and Database name in the `.env` file:
```sh
MONGO_URL=<your-mongodb-url>
MONGO_DB=<your-db>
```
### Collections Required for Setup

Please ensure the following collections exist in your MongoDB:

**apis collection:**

| Field      | Type   | Description |
|------------|--------|-------------|
| Url        | String | The endpoint of the API. |
| Key        | String | The unique key associated with the API. |
| Status     | String | The current status of the API (either "healthy" or "unhealthy"). |
| Service    | String | The name of the service. |
| CallCount  | Integer| The number of calls made to the API. |

**referers collection:**

| Field      | Type   | Description |
|------------|--------|-------------|
| _id        | ObjectId | The unique identifier of the referer. |
| Referer    | String | The referer. |
| Key        | String | The unique key associated with the referer. |
| Limit      | Integer | The monthly limit for the referer. |
| Status     | Integer | The status of the referer. |
| CallCount  | Integer | The number of calls made by the referer. |

### Usage

Access the gateway using the following URL pattern: 

`<your-host>/api/v1/<service>/<path>`

This gateway integrates microservices built on various programming languages to function seamlessly as a single application. It supports all types of calls, from RESTful calls to file downloads like PDF and Excel.

## Built With

- [Flask](https://flask.palletsprojects.com/en/2.0.x/) - The web framework used.
- [Docker](https://www.docker.com/) - Container platform to encapsulate the application setup.
- [daba](https://pypi.org/project/daba/) - Python library for MongoDB operations.

## Contributing

We welcome contributions to this project. Please feel free to fork, make your changes, and open a pull request. For major changes, please open an issue first to discuss what you would like to change.

## License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.