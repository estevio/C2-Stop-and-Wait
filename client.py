import SocketTCP

address = ('localhost', 8000)

# CLIENT
client_socketTCP = SocketTCP.SocketTCP()
client_socketTCP.connect(address)
# test 1
message = "Mensje de len=16".encode()
client_socketTCP.send(message)
# test 2
message = "Mensaje de largo 19".encode()
client_socketTCP.send(message)
# test 3
message = "Mensaje de largo 19".encode()
client_socketTCP.send(message)

client_socketTCP.close()

try:
    client_socketTCP.send(message)
except Exception as e:
    print(f"se reportó el error {e}")