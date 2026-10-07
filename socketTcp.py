import socket
from random import randint

class MensajeTCP():
    """
    tipo (bytes): el tipo de mensaje, puede ser uno de los siguientes "SYN", "ACK", "FIN", "A+S" "A+F"
    seq (bytes): el numero de secuencia en str
    msg (bytes): el contenido del mensaje

    todos los campos son caracteres
    """

    def __init__(self, tipo: bytes, seq: bytes = b"0", msg: bytes = b""):
        self.tipo = tipo
        self.seq = seq
        self.msg = msg

class SocketTCP():

    def __init__(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.destino = ('localhost', 8000)
        self.seq = 0
        self.header_size = 5
        self.msg_len = 16
        self.buf_size = self.header_size + self.msg_len

    @staticmethod
    def parse_segment(msg: bytes):
        return MensajeTCP(msg[0:3], msg[3:5], msg[5:])

    @staticmethod
    def create_segment(data: MensajeTCP):
        msg = bytearray(data.tipo)
        msg = msg + bytearray(data.seq) + bytearray(data.msg)
        return msg

    def bind(self, addr):
        self.socket.bind(addr)

    def connect(self, addr):
        print("conectando")
        self.seq = randint(0, 100)
        # enviar un mensaje syn
        msg = MensajeTCP(b"SYN", str(self.seq).encode())
        to_send = self.create_segment(msg)
        self.socket.sendto(to_send, addr)
        # recibir un mensaje devuelta
        rcv_msg, serv_addr = self.socket.recvfrom(19)
        # verificar ack, syn y addr
        parsed = self.parse_segment(rcv_msg)
        if parsed.tipo != b"A+S" or int(parsed.seq) <= self.seq:
            # en este momento no se checkea addr
            print("Hanshake no puede continuar")
            print(f"tipo: {parsed.tipo}\nseqs: {parsed.seq} <= {self.seq}\naddrs: {addr} {serv_addr}")
            return
        print("mensaje syn + ack recibido")
        self.seq = int(parsed.seq) + 1
        # enviar mensaje ack
        msg = MensajeTCP(b"ACK", str(self.seq).encode())
        to_send = self.create_segment(msg)
        self.socket.sendto(to_send, addr)
        print("conexion establecida!!")

    def accept(self):
        while True:
            print("recibiendo solicitudes")
            recv_msg, addr = self.socket.recvfrom(self.buf_size)
            parsed = self.parse_segment(recv_msg)
            if parsed.tipo != b"SYN":
                print("mensaje no es de tipo SYN")
                continue
            print("mensaje tipo syn recibido!")
            # enviar mensaje syn + ack
            self.seq = int(parsed.seq) + 1
            to_send = self.create_segment(MensajeTCP(b"A+S", str(self.seq).encode()))
            self.socket.sendto(to_send, addr)
            print("mensaje tipo syn+ack enviado!")
            # recibir mensaje tipo ack
            recv_msg, addr_2 = self.socket.recvfrom(self.buf_size)
            parsed = self.parse_segment(recv_msg)
            if parsed.tipo != b"ACK" or addr != addr_2 or int(parsed.seq) <= self.seq:
                print("tipo, addr o seq equivocado")
                continue
            print("mensaje tipo ack recibido!")

            # hanshake listo!
            new_socket = SocketTCP()
            new_socket.seq = parsed.seq
            new_socket.destino = addr
            new_addr = ('localhost', 8500)
            # direccion fija por simplicidad (no se puede crear 2 clientes al mismo tiempo)
            new_socket.bind(new_addr)
            print("conexion establecida!!")
            
            return (new_socket, new_addr)

