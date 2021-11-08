#!/usr/bin/python3

import socket
import signal
import sys
import os
import datetime
import time
import threading

BUFFER_SIZE = 1024
EXPIRATION_TIME = 120


def signal_handler(sig, frame):
    print('Interrupt received, shutting down ...')
    sys.exit(0)


def prepare_get_message(req_file, file_name):
    modifiedTime = os.path.getmtime(req_file)
    mtime_obj = datetime.datetime(*time.localtime(modifiedTime)[:6])
    mtime_obj.strftime('%a, %d %b %Y %H:%M:%S EDT')
    request = f'GET {file_name} HTTP/1.1\r\nIf-modified-since:{mtime_obj}\r\n\r\n'
    return request


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
    elif value == '523':
        message = message + value + ' Origin Is Unreachable\r\n' + date_string + '\r\n'
    return message


def send_response_to_client(sock, code, file_name):
    if (file_name.endswith('.jpg')) or (file_name.endswith('.jpeg')):
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


def check_file_timestamp(modifiedTime):
    current_time = datetime.datetime.now()
    time_diff = current_time - modifiedTime
    return time_diff.total_seconds() > EXPIRATION_TIME


def print_file_from_socket(sock, bytes_to_read):
    bytes_read = 0
    while bytes_read < bytes_to_read:
        chunk = sock.recv(BUFFER_SIZE)
        bytes_read += len(chunk)
        print(chunk.decode())


def save_file_from_socket(sock, bytes_to_read, file_name):
    with open(file_name, 'wb') as file_to_write:
        bytes_read = 0
        while bytes_read < bytes_to_read:
            chunk = sock.recv(BUFFER_SIZE)
            bytes_read += len(chunk)
            file_to_write.write(chunk)


def handle_client(connection, client_address):
    print('[NEW CONNECTION] ', client_address)
    request = get_line_from_socket(connection)
    print('Received request:  ' + request)

    request_list = request.split()
    server = get_line_from_socket(connection)
    server_list = server.split(':')
    server_host = server_list[1]
    server_port = int(server_list[2])

    server_path = server_host + '_' + server_list[2]
    while get_line_from_socket(connection) != '':
        pass
    file_name = request_list[1]

    req_file = server_path + request_list[1]

    dir_list = req_file.split('/')
    dir_path = ''
    counter = 0
    while counter < len(dir_list) - 1:
        dir_path = dir_path + dir_list[counter] + '/'
        counter += 1

    if os.path.exists(req_file):
        modifiedTime = datetime.datetime.fromtimestamp(os.path.getmtime(req_file))
        expire = check_file_timestamp(modifiedTime)
        if expire:
            conditionValue = False
            os.remove(req_file)
            print("The file expired, need update from server")
        else:
            conditionValue = True
    else:
        conditionValue = False
    try:
        socket_connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        socket_connection.connect((server_host, server_port))
    except ConnectionRefusedError:
        print('Error:  That host or port is not accepting connections.')
        send_response_to_client(connection, '523', '523.html')

    if conditionValue:
        message = prepare_get_message(req_file, file_name)
        print("File exists in the cache, connect server for checking file version...")
    else:
        message = request + '\r\n' + '\r\n\r\n'
        print("File does not exist in the cache, connect server for downloading...")

    socket_connection.send(message.encode())
    response_line = get_line_from_socket(socket_connection)
    response_list = response_line.split(' ')
    headers_done = False

    if response_list[1] != '200' and response_list[1] != '304':
        send_response_to_client(connection, response_list[1], response_list[1] + '.html')
        if response_list[1] == '404':
            try:
                os.remove(req_file)
            except OSError:
                pass
        print('Error:  An error response was received from the server.  Details:\n')
        print(response_line)
        bytes_to_read = 0
        while not headers_done:
            header_line = get_line_from_socket(socket_connection)
            print(header_line)
            header_list = header_line.split(' ')
            if header_line == '':
                headers_done = True
            elif header_list[0] == 'Content-Length:':
                bytes_to_read = int(header_list[1])
        print_file_from_socket(socket_connection, bytes_to_read)

    else:
        if response_list[1] == '200':
            print(response_line)
            if not os.path.isdir(dir_path):
                os.makedirs(dir_path)
            bytes_to_read = 0
            while not headers_done:
                header_line = get_line_from_socket(socket_connection)
                header_list = header_line.split(' ')
                print(header_line)
                if header_line == '':
                    headers_done = True
                elif header_list[0] == 'Content-Length:':
                    bytes_to_read = int(header_list[1])

            save_file_from_socket(socket_connection, bytes_to_read, req_file)
            print('Success:  Server is sending file.  Downloading it now.')

        elif response_list[1] == '304':
            print(response_line)
            bytes_to_read = 0
            while not headers_done:
                header_line = get_line_from_socket(socket_connection)
                print(header_line)
                header_list = header_line.split(' ')
                if header_line == '':
                    headers_done = True
                elif header_list[0] == 'Content-Length:':
                    bytes_to_read = int(header_list[1])
            print_file_from_socket(socket_connection, bytes_to_read)
        print('Sending file...')
        send_response_to_client(connection, '200', req_file)
        print('Transfer success!')
    connection.close()


def main():
    signal.signal(signal.SIGINT, signal_handler)
    cache_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    cache_socket.bind(('', 0))
    print('Listening at port ' + str(cache_socket.getsockname()[1]))
    cache_socket.listen(1)
    while True:
        connection, client_address = cache_socket.accept()
        thread = threading.Thread(target=handle_client, args=(connection, client_address))
        thread.start()
        print(f'Active connections: {threading.active_count() - 1}')


if __name__ == '__main__':
    main()
