from socketTcp import SocketTCP

address = ('localhost', 8000)
server_socketTCP = SocketTCP()
server_socketTCP.bind(address)
connection_socketTCP, new_address = server_socketTCP.accept()