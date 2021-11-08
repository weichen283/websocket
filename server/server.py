import socket
import os
import datetime
import signal
import sys
import threading

BUFFER_SIZE = 1024


def signal_handler(sig, frame):
    print('Interrupt received, shutting down ...')
    sys.exit(0)


def prepare_response_message(value):
    date = datetime.datetime.now()
    date_string = 'Date: ' + date.strftime('%a, %d %b %Y %H:%M:%S EDT')
    message = 'HTTP/1.1 '
    if value == '200':
        message = message + value + ' OK\r\n' + date_string + '\r\n'
    elif value == '404':
        message = message + value + ' Not Found\r\n' + date_string + '\r\n'
    elif value == '501':
        message = message + value + ' Method Not Implemented\r\n' + date_string + '\r\n'
    elif value == '505':
        message = message + value + ' Version Not Supported\r\n' + date_string + '\r\n'
    elif value == '304':
        message = message + value + ' Not Modified\r\n' + date_string + '\r\n'
    return message


def send_response_to_client(sock, code, file_name):
    if file_name.endswith('.jpg') or file_name.endswith('.jpeg'):
        type = 'image/jpeg'
    elif file_name.endswith('.gif'):
        type = 'image/gif'
    elif file_name.endswith('.png'):
        type = 'image/jpegpng'
    elif (file_name.endswith('.html')) or (file_name.endswith('.htm')):
        type = 'text/html'
    else:
        type = 'application/octet-stream'

    file_size = os.path.getsize(file_name)

    header = prepare_response_message(code) + 'Content-Type: ' + type + '\r\nContent-Length: ' + str(
        file_size) + '\r\n\r\n'
    sock.send(header.encode())

    with open(file_name, 'rb') as file_to_send:
        while True:
            chunk = file_to_send.read(BUFFER_SIZE)
            if chunk:
                sock.send(chunk)
            else:
                break


def get_line_from_socket(sock):
    done = False
    line = ''
    while not done:
        char = sock.recv(1).decode()
        if char == '\r':
            pass
        elif char == '\n':
            done = True
        else:
            line = line + char
    return line


def handle_client(conn, addr):
    print('[NEW CONNECTION] ', addr)
    request = get_line_from_socket(conn)
    print('Received request:  ' + request)
    request_list = request.split()

    headers = get_line_from_socket(conn)
    headers_list = headers.split(':')

    while get_line_from_socket(conn) != '':
        pass

    if request_list[0] != 'GET':
        print('Invalid type of request received ... responding with error!')
        send_response_to_client(conn, '501', '501.html')

    elif request_list[2] != 'HTTP/1.1':
        print('Invalid HTTP version received ... responding with error!')
        send_response_to_client(conn, '505', '505.html')

    else:
        req_file = request_list[1]
        while req_file[0] == '/':
            req_file = req_file[1:]

        if not os.path.exists(req_file):
            print('Requested file does not exist ... responding with error!')
            send_response_to_client(conn, '404', '404.html')

        else:
            if headers_list[0] == 'If-modified-since':
                modifiedTime = datetime.datetime.fromtimestamp(os.path.getmtime(req_file))
                date = headers_list[1].split('-')
                year = date[0]
                month = date[1]
                day = date[2].split(' ')[0]
                hour = date[2].split(' ')[1]
                minute = headers_list[2]
                second = headers_list[3]

                modi_cache = datetime.datetime(int(year), int(month), int(day), int(hour), int(minute), int(second))

                if modifiedTime <= modi_cache:
                    print('Requested file is the lasted version in the cache, good to send to the client...')
                    send_response_to_client(conn, '304', '304.html')
                else:
                    print('The version in Cache is old.  Sending the lasted version file ...')
                    send_response_to_client(conn, '200', req_file)
            else:
                print('Sending file...')
                send_response_to_client(conn, '200', req_file)
                print('Transfer success!')
    conn.close()


def main():
    signal.signal(signal.SIGINT, signal_handler)
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('', 0))
    print('Listening at port ' + str(server_socket.getsockname()[1]))
    server_socket.listen(1)

    while True:
        conn, addr = server_socket.accept()
        thread = threading.Thread(target=handle_client, args=(conn, addr))
        thread.start()
        print(f'Active connections: {threading.active_count() - 1}')


if __name__ == '__main__':
    main()
