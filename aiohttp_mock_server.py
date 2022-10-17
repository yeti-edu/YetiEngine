import asyncio
import time
import base64
from random import randint
from cryptography import fernet
import aiohttp
from aiohttp import web
import aiohttp.web_request

routes = web.RouteTableDef()

#copied
ap_ssid = "Yeti_ESP32_"+str(randint(0,1000))
ap_password = "12341234"
ap_authmode = 3  # WPA2

NETWORK_PROFILES = 'wifi.dat'
MAIN_PATH = "main.py"
CODE_PATH = "code/main_{name}.py"
TEMP_UPLOAD_PATH = "temp_code/temp_main.py"
OUTPUT_PATH = "output.txt"

global host_ip
host_ip = "127.0.0.1"

def page(html_file_name: str):
    """
    return: html file content for body of response
    """
    print(html_file_name)
    with open(f"website/{html_file_name}", "r") as f:
        data = f.read()
    return data

def index_page(html_file_name: str):
    with open(OUTPUT_PATH, "r") as f:
        output = f.read().replace("\n", "<br>")
    with open(MAIN_PATH, "r") as f:
        code = f.read().replace("\n", "<br>")
    return page(html_file_name).replace("{code}", code).replace("{output}", output).replace("{host_ip}", host_ip)


def update_code(request_json):
    code = request_json["code"]
    print(code)
    print(type(code))
    with open(MAIN_PATH, "w") as f:
        if code:
            print(f"writing code to {MAIN_PATH}")
            f.write(code)

####################

def write_payload_to_temp(payload):
    print("start writing new temp file.")
    with open(TEMP_UPLOAD_PATH, "wb") as f:
        f.write(payload)
    print("Written new temp file.")

@routes.get("/upload_a_file")
async def receive_file(request): #receive_file mock
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    payload = bytes()
    async for msg in ws:
        if msg.type == aiohttp.WSMsgType.TEXT:
            if msg.data == '---EOF---':
                await ws.close()
                write_payload_to_temp(payload)
            else:
                await ws.send_str(msg.data + '/answer')
        elif msg.type == aiohttp.WSMsgType.BINARY:
            print(msg.data)
            payload += msg.data
        elif msg.type == aiohttp.WSMsgType.ERROR:
            print('ws connection closed with exception %s' %
                  ws.exception())
        print('websocket connection closed')
    return ws

@routes.get('/')
async def root(request):
    #copiede
    return web.Response(body=index_page("index.html"), status=200, headers={'Content-Type': 'text/html'})


@routes.route(path='/run', method="GET")
def run_main_code(request):
    pass
    return root(request)

@routes.route(path='/upload', method="POST")
def upload(request):
    print(request.__dict__)
    update_code(request.json)
    return web.Response(status=200)

@routes.route(path='/preview', method="GET")
def preview(request):
    try:
        with open(TEMP_UPLOAD_PATH, "r") as f:
            upload_candidate_code = f.read().replace('\n', '<br>').replace('\t', '<t>').replace('    ', '<t>')
    except Exception as e:
        upload_candidate_code = ""
        print("No temporary code was uploaded.")
        return root(request)
    return web.Response(body=page("preview.html").replace("{code_from_temp_file}", upload_candidate_code), status=200, headers={'Content-Type': 'text/html'})

@routes.route(path='/approve', method="POST")
async def aprove_code(request):
    ans = await request.json()
    type(ans)
    aproval = ans["approval"]
    print(type(request))
    if aproval == "OK":
        print("got OK with filename: " + ans["file_name"])
        with open(TEMP_UPLOAD_PATH, "rb") as f:
            code = f.read()
        with open(CODE_PATH.format(name=ans["file_name"]), "wb") as f:
            f.write(code)
    if aproval == "CANCEL":
        with open(TEMP_UPLOAD_PATH, "wb") as f:
            print("got CANCEL")
            f.write(bytes())
            print("erased temp file.")
    return web.Response(status=200)



#######################################
async def make_app():
    app = web.Application()
    app.add_routes(routes)
    return app

web.run_app(make_app(), port=8000)
