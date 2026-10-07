import socket

class MensajeTCP():
    """
    tipo (bytes): el tipo de mensaje, tiene largo 1
        0: SYN
        1: ACK
        2: FIN
        3: SYN + ACK
        4: FIN + ACK

    seq (bytes): el numero de secuencia
    """

    def __init__(self, tipo: bytes, seq: bytes = 0, msg: bytes = b""):
        self.tipo = tipo
        self.seq = seq
        self.msg = msg

class SocketTCP():

    def __init__(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.destino = ('localhost', 8000)
        self.seq = 0

    @staticmethod
    def parse_segment(msg: bytes):
        return MensajeTCP(msg[0], msg[1:3], msg[3:])        

    @staticmethod
    def create_segment(data: MensajeTCP):
        msg = bytearray(data.tipo)
        msg = msg + bytearray(data.seq) + bytearray(data.msg)
        return msg
