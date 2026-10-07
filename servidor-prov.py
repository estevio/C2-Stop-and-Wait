import socket
import socketTcp

def recieve_full_message(socket, buff_size, end_sequence):
    recv_message, server_address = socket.recvfrom(buff_size)
    tcp_msg = socketTcp.SocketTCP.parse_segment(recv_message)
    full_message = tcp_msg.msg
    print(f"tipo: {tcp_msg.tipo}, seq: {tcp_msg.seq}\nmsg: {tcp_msg.msg}")
    current_server_address = server_address
    is_end = contains_end_of_message(full_message, end_sequence)

    while not is_end:
        recv_message, server_address = socket.recvfrom(buff_size)
        tcp_msg = socketTcp.SocketTCP.parse_segment(recv_message)
        print(f"msg: {tcp_msg.msg}")
        full_message += tcp_msg.msg
        is_end = contains_end_of_message(full_message, end_sequence)

    full_message = remove_end_of_message(full_message, end_sequence)

    return (full_message.decode(), current_server_address)

def contains_end_of_message(msg, end_seq):
    return msg.endswith(end_seq)

def remove_end_of_message(msg, end_seq):
    i = msg.rfind(end_seq)
    return msg[:i]

if __name__ == "__main__":
    end_sequence = b"end-of-message"
    server_address = ('localhost', 8000)
    buff_size = 19

    print("Creando socket - Servidor")

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    try:
        server_socket.bind(server_address)
    except:
        print("bind fracasado")

    while True:
        print("Esperando clientes...")
        try:
            recv_message, client_address = recieve_full_message(server_socket, buff_size, end_sequence)
            print(f" -> Se ha recibido el seguiente mensaje:\n{recv_message}")
        except Exception as e:
            print(f"error: {e}")
            server_socket.close()
            break
