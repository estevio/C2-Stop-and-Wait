from socketTcp import SocketTCP

address = ('localhost', 8000)
client_socketTCP = SocketTCP()
client_socketTCP.connect(address)