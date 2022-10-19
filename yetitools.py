from microdot import Microdot, Response
import microdot_websocket
import json

NETWORK_PROFILES = 'wifi.dat'
MAIN_PATH = "/main.py"
TEMP_UPLOAD_PATH = "/temp_code/temp_main.py"
OUTPUT_PATH = "/output.txt"
CODE_PATH = "/code/main{num}.py"
CODE_CONFIG_PATH = "/code/code.json"

global host_ip
host_ip = ""


# setup webserver
app = Microdot()


def start_server(server_ip):
    global host_ip
    print('Starting microdot app')
    host_ip = server_ip
    app.run(port=80)
    print('Server started')

def run_code():
    print("running all code files...")
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
    with open(CODE_PATH, "r") as f:
        main_number = str(int(json.loads(f.read())["next_file"]) - 1)
    with open(CODE_PATH.format(num=main_number), "r") as f:
        code = f.read().replace("\n", "<br>")
    return page(html_file_name).replace("{code}", code).replace("{output}", output).replace("{host_ip}", host_ip)

@app.route('/', methods=["GET"])
def root(request):
    return Response(body=index_page("index.html"), status_code=200, headers={'Content-Type': 'text/html'})

@app.route('/run', methods=["GET"])
def run_main_code(request):
    run_code()
    return root(request)

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
        print("got OK with file to main number:")
        with open(CODE_CONFIG_PATH, "r") as f:
            info = json.loads(f.read())
        print(info["next_file"])
        with open(TEMP_UPLOAD_PATH, "rb") as f:
            code = f.read()
            print("Loaded file to transfer...")
        with open(CODE_PATH.format(num=info["next_file"]), "wb") as f:
            f.write(code)
            print("Flushed file to main #"+info["next_file"]+" to "+CODE_PATH.format(num=info["next_file"]))
        nextfilenum = int(info["next_file"])
        if nextfilenum == 10:
            info["next_file"] = '0'
        else:
            info["next_file"] = str(nextfilenum + 1)
        print("next main number is "+info["next_file"])
        with open(CODE_CONFIG_PATH, "w") as f:
            f.write(json.dumps(info))
        print("next main number updated.")
    if aproval == "CANCEL":
        with open(TEMP_UPLOAD_PATH, "wb") as f:
            print("got CANCEL")
            f.write(bytes())
            print("erased temp file.")
    return Response(status_code=200)

@app.route('/upload_a_file')
@microdot_websocket.with_websocket
def receive_file(request, ws):
    print("got upload a file request")
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

