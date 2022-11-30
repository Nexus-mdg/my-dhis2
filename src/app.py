"""
This file will be our API entrypoint.
"""
import json
import os
import subprocess
import warnings

import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from starlette.applications import Starlette
from starlette.responses import JSONResponse, PlainTextResponse
from starlette.routing import Route

warnings.simplefilter('ignore', InsecureRequestWarning)


def shell(command):
    p = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True)
    out, err = p.communicate()
    plain_text_obj = out.decode("utf-8")
    return plain_text_obj


async def main():
    print("Endpoint started")


async def welcome_home(request):
    return JSONResponse({"message": "welcome home"})


async def start(request):
    response = shell(["catalina.sh run"])
    return PlainTextResponse(response)


async def restart(request):
    shell(["catalina.sh stop"])
    response = shell(["catalina.sh run"])
    return PlainTextResponse(response)


async def stop_tomcat(request):
    response = shell(["catalina.sh stop"])
    return PlainTextResponse(response)


async def truncate_database(request):
    db_name = os.getenv("DB_NAME")
    response = shell(["psql", "-U", "postgres", "-c", "DROP DATABASE IF EXISTS " + db_name])
    return PlainTextResponse(response)


async def get_tomcat_version(request):
    response = shell(["catalina.sh version"])
    return PlainTextResponse(response)


async def test_dhis2_endpoint(request):
    if os.getenv("ENCRYPTED") == "TRUE":
        url = "https://localhost:8443/dhis-web-commons/security/login.action"
    else:
        url = "http://localhost:8080/dhis-web-commons/security/login.action"
    response = requests.get(url, verify=False)
    return PlainTextResponse(str(response.status_code))


routes = [
    Route('/', endpoint=welcome_home, methods=['GET']),
    Route('/start', endpoint=start, methods=['GET']),
    Route('/restart', endpoint=restart, methods=['GET']),
    Route('/stop', endpoint=stop_tomcat, methods=['GET']),
    Route('/truncate', endpoint=truncate_database, methods=['GET']),
    Route('/version', endpoint=get_tomcat_version, methods=['GET']),
    Route('/test', endpoint=test_dhis2_endpoint, methods=['GET']),
]

app = Starlette(debug=False, routes=routes, on_startup=[main])
