from microdot import Microdot, Response
import microdot_websocket
from random import randint

NETWORK_PROFILES = 'wifi.dat'
MAIN_PATH = "/main.py"
TEMP_UPLOAD_PATH = "/temp_code/temp_main.py"
OUTPUT_PATH = "/output.txt"
CODE_PATH = "/code/main_{name}.py"

# setup webserver
app = Microdot()


def start_server():
    print('Starting microdot app')
    app.run(port=80)
    print('Server started')

def run_code():
    import main

def update_code(request_json):
    code = request_json["code"]
    print(code)
    print(type(code))
    with open(MAIN_PATH, "w") as f:
        if code:
            print(f"writing code to {MAIN_PATH}")
            f.write(code)


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

@app.route('/', methods=["GET"])
def root(request):
    return Response(body=index_page("index.html"), status_code=200, headers={'Content-Type': 'text/html'})

@app.route('/run', methods=["GET"])
def run_main_code(request):
    run_code()
    return root(request)

@app.route('/upload', methods=["POST"])
def upload(request):
    print(request.__dict__)
    update_code(request.json)
    return Response(status_code=200)

@app.route('/preview', methods=["GET"])
def preview(request):
    try:
        with open(TEMP_UPLOAD_PATH, "r") as f:
            upload_candidate_code = f.read().replace('\n', '<br>').replace('\t', '<t>').replace('    ', '<t>')
    except Exception as e:
        upload_candidate_code = ""
        print("No temporary code was uploaded.")
        return root(request)
    return Response(body=page("preview.html").replace("{code_from_temp_file}", upload_candidate_code), status_code=200, headers={'Content-Type': 'text/html'})

@app.route('/approve', methods=["POST"])
def aprove_code(request):
    ans = request.json
    aproval = ans["approval"]
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
    return Response(status_code=200)

@app.route('/upload_a_file')
@microdot_websocket.with_websocket
def receive_file(request, ws):
    payload = bytes()
    recv_loop = True
    while recv_loop:
        message = ws.receive()
        msg_type = (type(message))
        print(message)
        payload += message
        if msg_type == str and message[:9] == '---EOF---':
            recv_loop = False
    if len(payload) > 9:
        print("start writing new temp file.")
        with open(TEMP_UPLOAD_PATH, "wb") as f:
            f.write(payload[:-9])
            print("Written new temp file.")
    #print(payload[:-9])

