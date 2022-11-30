"""
This file will be our API entrypoint.
"""
import json
import os
import warnings
import subprocess
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route

warnings.simplefilter('ignore', InsecureRequestWarning)


def shell(command):
    p = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True)
    out, err = p.communicate()
    json_obj = json.loads(out.decode("utf-8"))
    return json_obj


async def main():
    print("Endpoint started")


async def welcome_home(request):
    try:
        return JSONResponse({"message": "welcome home"})
    except Exception as e:
        return JSONResponse({"error": str(e)})


async def start(request):
    try:
        response = shell(["catalina.sh", "run"])
        return response
    except Exception as e:
        return JSONResponse({"error": str(e)})


async def stop_tomcat(request):
    try:
        response = shell(["catalina.sh", "stop"])
        return response
    except Exception as e:
        return JSONResponse({"error": str(e)})


async def truncate_database(request):
    try:
        db_name = os.getenv("DB_NAME")
        response = shell(["psql", "-U", "postgres", "-c", "DROP DATABASE IF EXISTS " + db_name])
        return response
    except Exception as e:
        return JSONResponse({"error": str(e)})


routes = [
    Route('/', endpoint=welcome_home, methods=['GET']),
    Route('/start', endpoint=start, methods=['GET']),
    Route('/stop', endpoint=stop_tomcat, methods=['GET']),
    Route('/truncate', endpoint=truncate_database, methods=['GET']),
]


app = Starlette(debug=False, routes=routes, on_startup=[main])
