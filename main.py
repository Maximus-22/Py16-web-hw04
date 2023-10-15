import json, logging, mimetypes, socket, urllib.parse
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread

from jinja2 import Environment, FileSystemLoader

BASE_DIR = Path()
BUFFER_SIZE = 1024
HTTP_PORT = 8080
HTTP_HOST = '0.0.0.0'
SOCKET_HOST = '127.0.0.1'
SOCKET_PORT = 4000

# оточення для джинджи та iнструмент роботи з файлом
jinja = Environment(loader=FileSystemLoader('templates'))


class GoitFramework(BaseHTTPRequestHandler):

    def do_GET(self):
        route = urllib.parse.urlparse(self.path)
        print(route.query)
        match route.path:
            case '/':
                self.send_html('index.html')
            case '/message':
                self.send_html('message.html')
            case '/blog':
                # jinja2 за допомогою функцiї [render_template()] вiдразу працюэ з каталогом
                self.render_template('blog.html')
            case _:
                file = BASE_DIR.joinpath(route.path[1:])
                if file.exists():
                    self.send_static(file)
                else:
                    self.send_html('error.html', 404)

    def do_POST(self):
        # браузер каже якого розмiру пакет даних
        size = self.headers.get('Content-Length')
        # [HTML] це рядки, тому переводимо до int()
        data = self.rfile.read(int(size))

        # ми вiдправляэмо данi на socket_server, знов кортеж!
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        client_socket.sendto(data, (SOCKET_HOST, SOCKET_PORT))
        client_socket.close()

        self.send_response(302)
        self.send_header('Location', '/message')
        self.end_headers()

    def send_html(self, filename, status_code=200):
        self.send_response(status_code)
        self.send_header('Content-Type', 'text/html')
        self.end_headers()
        with open(filename, 'rb') as file:
            self.wfile.write(file.read())

    def render_template(self, filename, status_code=200):
        self.send_response(status_code)
        self.send_header('Content-Type', 'text/html')
        self.end_headers()

        with open('storage/db.json', 'r', encoding='utf-8') as file:
            data = json.load(file)

        # поки що тiльки темплейт
        template = jinja.get_template(filename)
        message = None  # "Hello Sergiy!"
        # [blogs] та [message] обов'язково повинн бути у файлi [template/blog.jinja]
        html = template.render(blogs=data, message=message)
        self.wfile.write(html.encode())

    def send_static(self, filename, status_code=200):
        self.send_response(status_code)
        mime_type, *_ = mimetypes.guess_type(filename)
        if mime_type:
            self.send_header('Content-Type', mime_type)
        else:
            self.send_header('Content-Type', 'text/plain')
        self.end_headers()
        with open(filename, 'rb') as file:
            self.wfile.write(file.read())


def save_data_from_form(data):
    # unquote_plus() при декодуваннi замiнюэ знаки [+] на пробiли
    parse_data = urllib.parse.unquote_plus(data.decode())
    try:
        parse_dict = {key: value for key, value in [el.split('=') for el in parse_data.split('&')]}
        with open('data/data.json', 'w', encoding='utf-8') as file:
            json.dump(parse_dict, file, ensure_ascii=False, indent=4)
    except ValueError as err:
        logging.error(err)
    except OSError as err:
        logging.error(err)


def run_socket_server(host, port):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.bind((host, port))
    logging.info("Starting socket server")
    try:
        while True:
            msg, address = server_socket.recvfrom(BUFFER_SIZE)
            logging.info(f"Socket received from {address}:\n-> {msg}")
            save_data_from_form(msg)
    except KeyboardInterrupt:
        quit(501)
    finally:
        server_socket.close()


def run_http_server(host, port):
    address = (host, port)
    http_server = HTTPServer(address, GoitFramework)
    # logging.info("Starting http server")
    try:
        logging.info("Starting http server")
        http_server.serve_forever()
    except KeyboardInterrupt:
        quit(501)
    finally:
        http_server.server_close()


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format='%(threadName)s %(message)s')

    server = Thread(target=run_http_server, args=(HTTP_HOST, HTTP_PORT))
    server.start()

    server_socket = Thread(target=run_socket_server, args=(SOCKET_HOST, SOCKET_PORT))
    server_socket.start()