import socket
from random import randint

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
        self.buf_size = 19

    @staticmethod
    def parse_segment(msg: bytes):
        return MensajeTCP(msg[0], msg[1:3], msg[3:])        

    @staticmethod
    def create_segment(data: MensajeTCP):
        msg = bytearray(data.tipo)
        msg = msg + bytearray(data.seq) + bytearray(data.msg)
        return msg

    def bind(self, addr):
        self.socket.bind(addr)

    def connect(self, addr):
        seq = randint(0, 100)
        msg = MensajeTCP(b"\x00", seq.to_bytes)
        to_send = self.create_segment(msg)
        # enviar un mensaje syn
        self.socket.sendto(msg, addr)
        rcv_msg, serv_addr = self.socket.recvfrom(to_send)
        # verificar ack, syn y addr
        parsed = self.parse_segment(rcv_msg)
        if parsed.tipo != b"\x03" or parsed.seq <= seq or addr != serv_addr:
            print("Hanshake no puede continuar")
            return
        seq = int(parsed.seq) + 1
        msg = MensajeTCP(b"\x01", seq.to_bytes)

    def accept(self):
        while True:
            recv_msg, addr = self.socket.recvfrom(self.buf_size)
            parsed = self.parse_segment(recv_msg)
            if parsed.tipo != b"\x00":
                continue
            seq = int(parsed.seq) + 1
            to_send = self.create_segment(b"\x03", seq.to_bytes)
            self.socket.sendto(to_send, addr)

            recv_msg, addr_2 = self.socket.recvfrom(self.buf_size)
            parsed = self.parse_segment(recv_msg)
            if parsed.tipo != b"\x01" or addr != addr_2:
                continue

            # hanshake listo!
            new_socket = SocketTCP()
            new_socket.seq = parsed.seq
            new_socket.destino = addr
            # direccion fija por simplicidad (no se puede crear 2 clientes al mismo tiempo)
            new_socket.bind(('localhost', 8500))

