import socket
import sys

"""
def recieve_full_message(socket, buff_size, end_sequence):
    recv_message, server_address = socket.recvfrom(buff_size)
    full_message = recv_message
    current_server_address = server_address
    is_end = contains_end_of_message(full_message, end_sequence)

    while not is_end:
        recv_message, server_address = socket.recvfrom(buff_size)
        full_message += recv_message
        is_end = contains_end_of_message(full_message, end_sequence)

    full_message = remove_end_of_message(full_message)

    return (full_message, current_server_address)
"""

def send_full_message(msg, sock, buff_size, addr, end_sequence):
    msg = msg.encode()
    msg += end_sequence
    msg_len = msg.__sizeof__()
    i = 0
    headers = b"\x01\x00\x00"
    while i < msg_len:
        sock.sendto((headers + msg[i:(i+buff_size)]), addr)
        i += buff_size

def contains_end_of_message(msg, end_seq):
    return msg.endswith(end_seq)

def remove_end_of_message(msg, end_seq):
    i = msg.rfind(end_seq)
    return msg[:i]

if __name__ == "__main__":

    if len(sys.argv) != 3:
        print("Modo de uso: cliente-prov [IP] [puerto]")

    end_sequence = b"end-of-message"
    server_address = (sys.argv[1], int(sys.argv[2]))
    buff_size = 19

    print("Creando socket - Cliente")

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    msg = ""
    while True:
        try:
            msg = msg + "\n" + input()
        except EOFError as e:
            break

    send_full_message(msg, client_socket, buff_size, server_address, end_sequence)