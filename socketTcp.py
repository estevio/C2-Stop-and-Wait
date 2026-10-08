import socket
from random import randint

class MensajeTCP():
    """
    clase que representa un mensaje TCP

    atributos:
        tipo (bytes): el tipo de mensaje, puede ser uno de los siguientes "SYN", "ACK", "FIN", "A+S", "A+F" o "MSG"
        seq (bytes): el numero de secuencia en str
        msg (bytes): el contenido del mensaje

    todos los campos son caracteres
    """

    def __init__(self, tipo: bytes, seq: bytes = b"\00", msg: bytes = b""):
        self.tipo = tipo
        self.seq = seq
        self.msg = msg

class SocketTCP():
    """
    clase que representa un socket TCP

    atributos:
        socket: un socket no orientado a conexión
        destino: dirección de destino de los mensajes
        seq (bytes): numero de secuencia validador del orden de los mensajes
        header_size (int): tamaño del header de un mensaje (tipo, seq)
        msg_len (int): tamaño máximo del contenido de un mensaje
        buf_size (int): tamaño del buffer (header_size + buf_size)
        timeout (int): segundos de espera máxima entre mensajes en stop and wait
    """

    def __init__(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.destino = ('localhost', 8000)
        self.seq = b""
        self.header_size = 5 # TODO: cambiar el tamaño para tener en cuenta el tamaño de seq en char (al menos 3)
        self.msg_len = 16
        self.buf_size = self.header_size + self.msg_len
        self.timeout = 3

    @staticmethod
    def parse_segment(msg: bytes):
        """
        recibe un mensaje tcp en bytes y retorna un objeto MensajeTCP que lo representa

        recibe:
            msg (bytes): el mensaje en bytes

        retorna:
            un objeto MensajeTCP
        """
        return MensajeTCP(msg[0:3], msg[3:5], msg[5:])

    @staticmethod
    def create_segment(data: MensajeTCP):
        """
        crea un mensaje en bytes a partir de un objeto MensajeTCP

        recibe:
            data (MensajeTCP): la información que va en el mensaje

        retorna:
            un mensaje en bytes
        """
        msg = data.tipo + data.seq + data.msg #TODO: agregar padding a seq
        return msg

    def bind(self, addr):
        """
        hace el bind del socket a la dirección dada

        recibe:
            addr: la dirección en la que el socket escucha
        """
        self.socket.bind(addr)

    def connect(self, addr):
        """
        establece una conexión mediante 3-way handshake.
        envía la primera solicitud

        recibe:
            addr: la dirección del servidor
        """
        print("conectando")
        self.seq = randint(0, 100).to_bytes(2)
        # enviar un mensaje syn
        msg = MensajeTCP(b"SYN", self.seq)
        to_send = self.create_segment(msg)
        self.socket.sendto(to_send, addr)
        # recibir un mensaje devuelta
        rcv_msg, serv_addr = self.socket.recvfrom(19)
        # verificar ack, syn y addr
        parsed = self.parse_segment(rcv_msg)
        if parsed.tipo != b"A+S" or parsed.seq <= self.seq:
            # en este momento no se checkea addr
            print("Hanshake no puede continuar")
            print(f"tipo: {parsed.tipo}\nseqs: {parsed.seq} <= {self.seq}\naddrs: {addr} {serv_addr}")
            return
        print("mensaje syn + ack recibido")
        self.seq = (int.from_bytes(parsed.seq) + 1).to_bytes(2)
        # enviar mensaje ack
        msg = MensajeTCP(b"ACK", self.seq)
        to_send = self.create_segment(msg)
        self.socket.sendto(to_send, addr)
        print("conexion establecida!!")

    def accept(self):
        """
        escucha por solicitudes a conexión y las acepta mediante 3-way handshake

        retorna:
            (SocketTCP para la conexión, dirección del SocketTCP)
        """
        while True:
            print("recibiendo solicitudes")
            recv_msg, addr = self.socket.recvfrom(self.buf_size)
            parsed = self.parse_segment(recv_msg)
            if parsed.tipo != b"SYN":
                print("mensaje no es de tipo SYN")
                continue
            print("mensaje tipo syn recibido!")
            # enviar mensaje syn + ack
            self.seq = (int.from_bytes(parsed.seq) + 1).to_bytes(2)
            to_send = self.create_segment(MensajeTCP(b"A+S", self.seq))
            self.socket.sendto(to_send, addr)
            print("mensaje tipo syn+ack enviado!")
            # recibir mensaje tipo ack
            recv_msg, addr_2 = self.socket.recvfrom(self.buf_size)
            parsed = self.parse_segment(recv_msg)
            if parsed.tipo != b"ACK" or addr != addr_2 or parsed.seq <= self.seq:
                print("tipo, addr o seq equivocado")
                continue
            print("mensaje tipo ack recibido!")

            # hanshake listo!
            new_socket = SocketTCP()
            new_socket.seq = (int.from_bytes(parsed.seq) + 1).to_bytes(2)
            new_socket.destino = addr
            new_addr = ('localhost', 8500)
            # direccion fija por simplicidad (no se puede crear 2 clientes al mismo tiempo)
            new_socket.bind(new_addr)
            print("conexion establecida!!")
            
            return (new_socket, new_addr)

    def send(self, msg: str):
        """
        envía un mensaje completo a través del socket.
        el primer mensaje lleva el largo del mensaje en el contenido.
        asume que la conexión fue establecida

        recibe:
            msg (str): el mensaje a enviar
        """
        if self.seq == b"":
            print("conexion no fue establecida")
            return

        # TODO: mover el timer al principio cuando ya este implementado el manejo de perdidas
        self.socket.settimeout(self.timeout)
        # enviar el primer mensaje que contiene el tamaño del mensaje
        msg = msg.encode()
        full_msg_len = msg.__sizeof__()
        self._send_pack(full_msg_len)
        i = 0
        while i < full_msg_len:
            # enviar 16 bytes de mensaje
            self._send_pack(msg[i:i+self.msg_len])
            i += self.msg_len

    def _send_pack(self, content: bytes):
        tipo = b"MSG"
        msg_tcp = MensajeTCP(tipo, self.seq, content)
        pack = self.create_segment(msg_tcp)
        self.socket.sendto(pack, self.destino)

        # esperar mensaje ack
        # caso 1: todo bien
        try:
            recv_msg, = self.socket.recvfrom(self.buf_size)
            parsed = self.parse_segment(recv_msg)
            if int(parsed.seq) <= self.seq:
                print("secuencia incorrecta")
                return
            # TODO: quizas esto debiera ser el largo del mensaje enviado u otro numero que permita verificar
            self.seq = (int.from_bytes(parsed.seq) + 1).to_bytes(2)
        # caso 2: no se recibe el mensaje de confirmación
        except TimeoutError:
            print("error de timeout en send, reenviando el mensaje")
            self._send_pack(content)




