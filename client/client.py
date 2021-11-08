import socket
import sys
import argparse
from urllib.parse import urlparse

BUFFER_SIZE = 1024


def prepare_get_message(host, port, file_name):
    request = f'GET {file_name} HTTP/1.1\r\nHost:{host}:{port}\r\n\r\n'
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("url", help="URL to fetch with an HTTP GET request")
    parser.add_argument("-proxy", help="Proxy to fetch with a web cache connection")
    args = parser.parse_args()

    try:
        if args.proxy:
            parsed_proxy = args.proxy.split(':')
            cache_host = parsed_proxy[0]
            cache_port = int(parsed_proxy[1])

        parsed_url = urlparse(args.url)
        if (parsed_url.scheme != 'http') or (parsed_url.port is None) or (parsed_url.path == '') or (
                parsed_url.path == '/') or (parsed_url.hostname is None):
            raise ValueError
        server_host = parsed_url.hostname
        server_port = parsed_url.port
        file_name = parsed_url.path

    except ValueError:
        print('Error:  Invalid URL.  Enter a URL of the form:  http://host:port/file')
        sys.exit(1)

    if args.proxy:
        host = cache_host
        port = cache_port
        connect_message = "Connecting to cache ..."
        sending_message = "Connection to cache established. Sending message...\n"
    else:
        host = server_host
        port = server_port
        connect_message = "Connecting to server ..."
        sending_message = "Connection to server established. Sending message...\n"

    print(connect_message)
    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((host, port))
    except ConnectionRefusedError:
        print('Error:  That host or port is not accepting connections.')
        sys.exit(1)
    print(sending_message)
    message = prepare_get_message(server_host, server_port, file_name)
    client_socket.send(message.encode())
    response_line = get_line_from_socket(client_socket)
    response_list = response_line.split(' ')
    headers_done = False

    print(response_list[1])
    if response_list[1] != '200':
        print('Error:  An error response was received from the server.  Details:\n')
        print(response_line)
        bytes_to_read = 0
        while not headers_done:
            header_line = get_line_from_socket(client_socket)
            print(header_line)
            header_list = header_line.split(' ')
            if header_line == '':
                headers_done = True
            elif header_list[0] == 'Content-Length:':
                bytes_to_read = int(header_list[1])
        print_file_from_socket(client_socket, bytes_to_read)
        sys.exit(1)
    else:
        print(response_line)

        while file_name[0] == '/':
            file_name = file_name.split('/')[-1]
        bytes_to_read = 0
        while not headers_done:
            header_line = get_line_from_socket(client_socket)
            header_list = header_line.split(' ')
            print(header_line)
            if header_line == '':
                headers_done = True
            elif header_list[0] == 'Content-Length:':
                bytes_to_read = int(header_list[1])
        save_file_from_socket(client_socket, bytes_to_read, file_name)
        print('Success:  Server is sending file.  Downloading it now.')


if __name__ == '__main__':
    main()
