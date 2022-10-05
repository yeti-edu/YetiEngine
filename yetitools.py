from microdot import Response
import network
import socket
import ure
import time
import re
from random import randint


ap_ssid = "Yeti_ESP32_"+str(randint(0,1000))
ap_password = "12341234"
ap_authmode = 3  # WPA2

NETWORK_PROFILES = 'wifi.dat'
MAIN_PATH = "/main.py"
OUTPUT_PATH = "/output.txt"

wlan_ap = network.WLAN(network.AP_IF)
wlan_sta = network.WLAN(network.STA_IF)

server_socket = None

logger = None


def get_connection():
    """return a working WLAN(STA_IF) instance or None"""

    # First check if there already is any connection:
    if wlan_sta.isconnected():
        return wlan_sta

    connected = False
    try:
        # ESP connecting to WiFi takes time, wait a bit and try again:
        time.sleep(3)
        if wlan_sta.isconnected():
            return wlan_sta

        # Read known network profiles from file
        profiles = read_profiles()

        # Search WiFis in range
        wlan_sta.active(True)
        networks = wlan_sta.scan()

        AUTHMODE = {0: "open", 1: "WEP", 2: "WPA-PSK", 3: "WPA2-PSK", 4: "WPA/WPA2-PSK"}
        for ssid, bssid, channel, rssi, authmode, hidden in sorted(networks, key=lambda x: x[3], reverse=True):
            ssid = ssid.decode('utf-8')
            encrypted = authmode > 0
            print("ssid: %s chan: %d rssi: %d authmode: %s" % (ssid, channel, rssi, AUTHMODE.get(authmode, '?')))
            if encrypted:
                if ssid in profiles:
                    password = profiles[ssid]
                    connected = do_connect(ssid, password)
                else:
                    print("skipping unknown encrypted network")
            else:  # open
                connected = do_connect(ssid, None)
            if connected:
                break

    except OSError as e:
        print("exception", str(e))

    # start web server for connection manager:
    if not connected:
        connected = start_network_picker()

    return wlan_sta if connected else None


def read_profiles():
    with open(NETWORK_PROFILES) as f:
        lines = f.readlines()
    profiles = {}
    for line in lines:
        ssid, password = line.strip("\n").split(";")
        profiles[ssid] = password
    return profiles


def write_profiles(profiles):
    lines = []
    for ssid, password in profiles.items():
        lines.append("%s;%s\n" % (ssid, password))
    with open(NETWORK_PROFILES, "w") as f:
        f.write(''.join(lines))


def do_connect(ssid, password):
    wlan_sta.active(True)
    if wlan_sta.isconnected():
        return None
    print('Trying to connect to %s...' % ssid)
    wlan_sta.connect(ssid, password)
    for retry in range(100):
        connected = wlan_sta.isconnected()
        if connected:
            break
        time.sleep(0.1)
        print('.', end='')
    if connected:
        print('\nConnected. Network config: ', wlan_sta.ifconfig())
    else:
        print('\nFailed. Not Connected to: ' + ssid)
    return connected


def send_header(client, status_code=200, content_length=None ):
    client.sendall("HTTP/1.0 {} OK\r\n".format(status_code))
    client.sendall("Content-Type: text/html\r\n")
    if content_length is not None:
      client.sendall("Content-Length: {}\r\n".format(content_length))
    client.sendall("\r\n")


def send_response(client, payload, status_code=200):
    content_length = len(payload)
    send_header(client, status_code, content_length)
    if content_length > 0:
        client.sendall(payload)
    client.close()


def handle_root(client):
    wlan_sta.active(True)
    ssids = sorted(ssid.decode('utf-8') for ssid, *_ in wlan_sta.scan())
    send_header(client)
    client.sendall("""\
        <html>
            <h1 style="color: #0F173A; text-align: center;">
                <span style="color: #37BEAF;">
                    Wi-Fi Client Setup
                </span>
            </h1>
            <form action="configure" method="post">
                <table style="margin-left: auto; margin-right: auto;">
                    <tbody>
    """)
    while len(ssids):
        ssid = ssids.pop(0)
        client.sendall("""\
                        <tr>
                            <td colspan="2">
                                <input type="radio" name="ssid" value="{0}" />{0}
                            </td>
                        </tr>
        """.format(ssid))
    client.sendall("""\
                        <tr>
                            <td>Password:</td>
                            <td><input name="password" type="password" /></td>
                        </tr>
                    </tbody>
                </table>
                <p style="text-align: center;">
                    <input type="submit" value="Submit" />
                </p>
            </form>
            <p>&nbsp;</p>
            <hr />
            <h5>
                <span style="color: #37BEAF;">
                    Your ssid and password information will be saved into the
                    "%(filename)s" file in your ESP module for future usage.
                    Be careful about security!
                </span>
            </h5>
            <hr />
        </html>
    """ % dict(filename=NETWORK_PROFILES))
    client.close()


def handle_configure(client, request):
    match = ure.search("ssid=([^&]*)&password=(.*)", request)

    if match is None:
        send_response(client, "Parameters not found", status_code=400)
        return False
    # version 1.9 compatibility
    try:
        ssid = match.group(1).decode("utf-8").replace("%3F", "?").replace("%21", "!")
        password = match.group(2).decode("utf-8").replace("%3F", "?").replace("%21", "!")
    except Exception:
        ssid = match.group(1).replace("%3F", "?").replace("%21", "!")
        password = match.group(2).replace("%3F", "?").replace("%21", "!")

    if len(ssid) == 0:
        send_response(client, "SSID must be provided", status_code=400)
        return False

    if do_connect(ssid, password):
        response = """\
            <html>
                <center>
                    <br><br>
                    <h1 style="color: #0F173A; text-align: center;">
                        <span style="color: #37BEAF;">
                            ESP successfully connected to WiFi network %(ssid)s.
                        </span>
                    </h1>
                    <br><br>
                </center>
            </html>
        """ % dict(ssid=ssid)
        send_response(client, response)
        try:
            profiles = read_profiles()
        except OSError:
            profiles = {}
        profiles[ssid] = password
        write_profiles(profiles)

        time.sleep(5)

        return True
    else:
        response = """\
            <html>
                <center>
                    <h1 style="color: #0F173A; text-align: center;">
                        <span style="color: #37BEAF;">
                            ESP could not connect to WiFi network %(ssid)s.
                        </span>
                    </h1>
                    <br><br>
                    <form>
                        <input type="button" value="Go back!" onclick="history.back()"></input>
                    </form>
                </center>
            </html>
        """ % dict(ssid=ssid)
        send_response(client, response)
        return False


def handle_not_found(client, url):
    send_response(client, "Path not found: {}".format(url), status_code=404)


def stop():
    global server_socket

    if server_socket:
        print("Closing former server socket...")
        server_socket.close()
        server_socket = None


def start_network_picker(port=80):
    global server_socket

    addr = socket.getaddrinfo('0.0.0.0', port)[0][-1]

    stop()

    wlan_sta.active(True)
    wlan_ap.active(True)

    wlan_ap.config(essid=ap_ssid, password=ap_password, authmode=ap_authmode)

    server_socket = socket.socket()
    server_socket.bind(addr)
    server_socket.listen(1)

    print('Connect to WiFi ssid ' + ap_ssid + ', default password: ' + ap_password)
    print('and access the ESP via your favorite web browser at 192.168.4.1.')
    print('Listening on:', addr)

    while True:
        if wlan_sta.isconnected():
            return True

        client, addr = server_socket.accept()
        print('client connected from', addr)
        try:
            client.settimeout(5.0)

            request = b""
            try:
                while "\r\n\r\n" not in request:
                    request += client.recv(512)
            except OSError:
                pass

            print("Request is: {}".format(request))
            if "HTTP" not in request:  # skip invalid requests
                continue

            # version 1.9 compatibility
            try:
                url = ure.search("(?:GET|POST) /(.*?)(?:\\?.*?)? HTTP", request).group(1).decode("utf-8").rstrip("/")
            except Exception:
                url = ure.search("(?:GET|POST) /(.*?)(?:\\?.*?)? HTTP", request).group(1).rstrip("/")
            print("URL is {}".format(url))

            if url == "":
                handle_root(client)
            elif url == "configure":
                handle_configure(client, request)
            else:
                handle_not_found(client, url)

        finally:
            client.close()

# def start_editor(port=80):
#     global server_socket

#     addr = socket.getaddrinfo('0.0.0.0', port)[0][-1]

#     stop()
#     if not server_socket:
#         server_socket = socket.socket()
#         server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
#         server_socket.bind(addr)
#         server_socket.listen(1)

#     print('Openning web code editor')

#     while True:
#         client, addr = server_socket.accept()
#         print('client connected from', addr)
#         try:
#             client.settimeout(5.0)

#             request = b""
#             try:
#                 while "\r\n\r\n" not in request:
#                     request += client.recv(512)
#             except OSError:
#                 pass

#             print("Request is: {}".format(request))
#             if "HTTP" not in request:  # skip invalid requests
#                 continue

#             # version 1.9 compatibility
#             try:
#                 url = ure.search("(?:GET|POST) /(.*?)(?:\\?.*?)? HTTP", request).group(1).decode("utf-8").rstrip("/")
#             except Exception:
#                 url = ure.search("(?:GET|POST) /(.*?)(?:\\?.*?)? HTTP", request).group(1).rstrip("/")
#             print("URL is {}".format(url))

#             if url == "":
#                 handle_code_root(client)
#             elif url== "run":
#                 print("running current code!")
#                 break
#             elif url == "update":
#                 handle_code_update(client, request)
#                 print("hadled code update!")
#                 break
#             elif url == "upload_file":
#                 handle_upload_file(client, request)
#             else:
#                 handle_not_found(client, url)

#         finally:
#             client.close()
#             print("Closing web editor client...")


# def upload_new_main(path, code):
#     with open(path, "wb") as f:
#         f.write(code)

# def handle_upload_file(client, request):
#     pass

# def handle_code_root(client):
#     try:
#         with open(MAIN_PATH, "rb") as f:
#             code = f.read().decode()
#             print(code)
#     except:
#         code = ""
#     try:
#         with open(OUTPUT_PATH, "rb") as f:
#             output = f.read().decode()
#             print(output)
#     except:
#         output = ""
#     send_header(client)
#     client.sendall("""
#     <html>
#             <head>
#                 <style type="text/css">
#                 .input,
#                     .textarea {
#                     border: 1px solid #ccc;
#                     font-family: courier;
#                     white-space: pre-wrap;
#                     color:#F0A020;
#                     background-color:#1F274A;
#                     font-size: inherit;
#                     padding: 1px 6px;
#                     }
#                     .textarea {
#                     display: block;
#                     width: 100%;
#                     overflow: hidden;
#                     resize: both;
#                     min-height: 40px;
#                     line-height: 20px;
#                     }
#                     .textarea[contenteditable]:empty::before {
#                     content: "Your code here";
#                     color: gray;
#                     }
#                 </style>
#             </head>
#             <body style="background-color:#0F173A;">
#                 <h1 style="color: #0F173A; font-family:courier; text-align: center;">
#                     <span style="color: #37BEAF;">
#                         Yeti Code Editor
#                     </span>
#                 </h1>
#                 <form action="update" method="POST">
#                     <p style="color:#F0A020; background-color:#1F274A; text-align: left; vertical-align: top; font-family:courier;">""" + code.replace("\n", "<br>") +
#                     """</p>
#                     <label for="code"style="color:white;font-family:courier;">
#                     Last run output:
#                     </label>
#                     <p style="color:#FFFFFF; background-color:#000000; text-align: left; vertical-align: top; font-family:courier;">""" + output.replace("\n", "<br>") +
#                     """</p>
#                     <label for="code"style="color:white;font-family:courier;">
#                     Enter your code:
#                     </label>
#                     <p style="background-color:#FFFFFF; text-align: left; vertical-align: top; font-family:courier;"></p>
#                     <textarea class="textarea" placeholder="Your Code Here" name="code" id="code" rows="15" style="overflow-y: visible;"></textarea>
#                     <br/>
#                     <input type="submit" value="Upload Code">
#                 </form>
#                 <form action="run" method="POST">
#                     <input type="submit" value="Run Current Code">
#                 </form>
#                 <form action="upload_file" method="POST">
#                     <label for="file">Select a file:</label>
#                     <input type="file" id="file" name="file">
#                 </form>
#             <body>
#         </html>
# """)
    
    

# def handle_code_update(client, response):
    # global logger
    # logging.basicConfig(filename=OUTPUT_PATH,
    #                 filemode='w',
    #                 format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
    #                 datefmt='%H:%M:%S',
    #                 level=logging.DEBUG)

    # logger = logging.getLogger('output')
    code = str(response).split("code=")[-1]
    # print("#### Got:\n" + code)
    code = unquote_to_bytes(code.replace("+", " "))
    print("Parsed:\n" + code.decode())
    with open(MAIN_PATH, "wb") as f:
        if code:
            f.write(code)


def from_hex(hex_string: str):
    if len(hex_string) % 2 != 0:
        raise Exception("Failed parsing bytes of string " + hex_string)
    byte_string = b""
    for nibble_i in range(0, len(hex_string), 2):
        byte_value = int(hex_string[nibble_i:nibble_i+1], 16)
        byte_string = byte_string + chr(byte_value).encode()
    return byte_string

_hexdig = '0123456789ABCDEFabcdef'
_hextobyte = None


def unquote_to_bytes(string):
    """unquote_to_bytes('abc%20def') -> b'abc def'."""
    # Note: strings are encoded as UTF-8. This is only an issue if it contains
    # unescaped non-ASCII characters, which URIs should not.
    if not string:
        # Is it a string-like object?
        string.split
        return b''
    if isinstance(string, str):
        string.replace("+", " ")
        string = string.encode('utf-8')
    # print(string)
    bits = string.split(b'%')
    # print(bits)
    if len(bits) == 1:
        return string
    res = [bits[0]]
    append = res.append
    # Delay the initialization of the table to not waste memory
    # if the function is never called
    global _hextobyte
    if _hextobyte is None:
        _hextobyte = {(a + b).encode(): chr(int((a + b), 16))
                      for a in _hexdig for b in _hexdig}
    for item in bits[1:]:
        try:
            append(_hextobyte[item[:2]])
            append(item[2:])
        except KeyError:
            append(b'%')
            append(item)
    # print("res:", res)
    for i in range(len(res)):
        if not isinstance(res[i], bytes):
            res[i] = res[i].encode()
    return b''.join(res)[:-1]





import uasyncio
import sys
from microdot import Microdot, Response


# setup webserver
app = Microdot()


def start_server():
    print('Starting microdot app')
    app.run(port=80)
    print('Server started')

def run_code():
    pass

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
    return page(html_file_name).replace("{code}", code).replace("{output}", output)

@app.route('/', methods=["GET"])
def root(request):
	return Response(body=index_page("index.html"), status_code=200, headers={'Content-Type': 'text/html'})

@app.route('/run', methods=["GET"])
def run_main_code(request):
    run_code()
    return root(request)

@app.route('/upload_file', methods=["POST"])
def upload_file(request):
    fd = request.stream
    print(fd)
    print(fd.read())
    return Response(status_code=200)

@app.route('/upload', methods=["POST"])
def upload(request):
    update_code(request)
    return Response(status_code=200)

@app.route('/preview', methods=["POST"])
def preview(request):
	return Response(body=page("preview.html"), status_code=200, headers={'Content-Type': 'text/html'})




