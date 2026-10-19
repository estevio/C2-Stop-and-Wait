import SocketTCP

def recieve_full_message(socket: SocketTCP.SocketTCP, buff_size: int, end_sequence: bytes):
    recv_message = socket.recv(buff_size)
    print(f"chunk recibido: {recv_message.decode()}")
    full_message = recv_message
    is_end = contains_end_of_message(full_message, end_sequence)
    
    while not is_end:
        recv_message = socket.recv(buff_size)
        print(f"chunk recibido: {recv_message.decode()}")
        full_message += recv_message
        is_end = contains_end_of_message(full_message, end_sequence)

    return full_message

def contains_end_of_message(msg, end_seq):
    return msg.endswith(end_seq)

def remove_end_of_message(msg, end_seq):
    i = msg.rfind(end_seq)
    return msg[:i]

if __name__ == "__main__":
    end_sequence = b"end-of-message"
    server_address = ('localhost', 8000)
    buff_size = 16

    print("Creando socket - Servidor")

    server_socket = SocketTCP.SocketTCP()

    try:
        server_socket.bind(server_address)
    except:
        print("bind fracasado")

    print("Esperando clientes...")
    new_socket, new_address = server_socket.accept()
    print("Conexion establecida")

    print("Reciebiendo mensaje completo")
    recv_message = recieve_full_message(new_socket, 19, end_sequence)
    print(f"\n -> Se ha recibido el seguiente mensaje:\n{recv_message}\n")

    print("confirmando cierre")
    try:
        new_socket.send(recv_message)
    except Exception as e:
        print(f"se reportó el error {e}")