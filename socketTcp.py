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
        expecting (int): largo del contenido que se espera
        cach (bytes): mensaje que sobra respecto al tamaño del buffer
    """

    def __init__(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.destino = ('localhost', 8000)
        self.seq = b""
        self.header_size = 5 # TODO: cambiar el tamaño para tener en cuenta el tamaño de seq en char (al menos 3)
        self.msg_len = 16
        self.buf_size = self.header_size + self.msg_len
        self.expecting = 0
        self.socket.settimeout(10) # espera 10 segundos antes de reenviar
        self.cach = b""

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
        rcv_msg, serv_addr = self.socket.recvfrom(19) # TODO: esta direccion deberia ser la del nuevo socket?
        # verificar ack, syn y addr
        parsed = self.parse_segment(rcv_msg)
        if parsed.tipo != b"A+S" or parsed.seq <= self.seq:
            # en este momento no se checkea addr
            print("Hanshake no puede continuar")
            print(f"tipo: {parsed.tipo}\nseqs: {parsed.seq} <= {self.seq}\naddrs: {addr} {serv_addr}")
            return
        print("mensaje syn + ack recibido")
        self.destino = serv_addr
        self.seq = (int.from_bytes(parsed.seq) + 1).to_bytes(2)
        # enviar mensaje ack
        msg = MensajeTCP(b"ACK", self.seq)
        to_send = self.create_segment(msg)
        self.socket.sendto(to_send, self.destino)
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
            # crear un nuevo socket para la comunicacion
            new_socket = SocketTCP()
            new_socket.seq = (int.from_bytes(parsed.seq) + 1).to_bytes(2)
            new_socket.destino = addr
            new_addr = ('localhost', 8500)
            # direccion fija por simplicidad (no se puede crear 2 clientes al mismo tiempo)
            new_socket.bind(new_addr)
            # enviar mensaje syn + ack
            to_send = self.create_segment(MensajeTCP(b"A+S", new_socket.seq))
            new_socket.socket.sendto(to_send, addr)
            print("mensaje tipo syn+ack enviado!")
            # recibir mensaje tipo ack
            recv_msg, addr_2 = new_socket.socket.recvfrom(self.buf_size)
            parsed = self.parse_segment(recv_msg)
            if parsed.tipo != b"ACK" or addr != addr_2 or parsed.seq <= new_socket.seq:
                print("tipo, addr o seq equivocado")
                continue
            print("mensaje tipo ack recibido!")
            print("conexion establecida!!")
            return (new_socket, new_addr)

    def send(self, msg: bytes):
        """
        envía un mensaje completo a través del socket.
        el primer mensaje lleva el largo del mensaje en el contenido.
        asume que la conexión fue establecida

        recibe:
            msg (bytes): el mensaje a enviar
        """
        if self.seq == b"":
            print("conexion no fue establecida")
            return
        print(f"mensaje completo por enviar: {msg.decode()}")

        # enviar el primer mensaje que contiene el tamaño del mensaje
        full_msg_len = len(msg)
        self._send_pack(str(full_msg_len).encode())
        i = 0
        while i < full_msg_len:
            # enviar 16 bytes de mensaje
            self._send_pack(msg[i:i+self.msg_len])
            i += self.msg_len

    def _send_pack(self, content: bytes):
        # TODO: ahora se pierden datos si el mensaje es más largo que buff_size (solo se elimina)
        print(f"contenido a mandar: {content.decode()} a direccion {self.destino}")
        tipo = b"MSG"
        msg_tcp = MensajeTCP(tipo, self.seq, content)
        pack = self.create_segment(msg_tcp)
        self.socket.sendto(pack, self.destino)

        # caso 1: todo bien
        try:
            recv_msg, addr= self.socket.recvfrom(self.buf_size)
            parsed = self.parse_segment(recv_msg)
            if parsed.seq <= self.seq:
                print("secuencia incorrecta")
                self._send_pack(content)
            else:
                print("enviando mensaje")
                # TODO: quizas esto debiera ser el largo del mensaje enviado u otro numero que permita verificar
                self.seq = (int.from_bytes(parsed.seq) + 1).to_bytes(2)
        # caso 2: no se recibe el mensaje de confirmación
        except TimeoutError:
            print(f"\nerror de timeout en send\ncontenido del mensaje:\ntipo: {msg_tcp.tipo}\nseq: {msg_tcp.seq}")
            self._send_pack(content)
        
    def recv(self, buff_size):
        # caso 1: primer mensaje (msg_len)
        print("recibiendo el largo del mensaje")
        if self.expecting == 0:
            self.expecting = int(self._recv_pack().decode())
        # caso 2: continuacion del mensaje
        recv_msg = self.cach
        pack_len = min(self.expecting, buff_size)
        while pack_len > 0:
            recv_content = self._recv_pack()
            self.expecting -= len(recv_content)
            pack_len -= len(recv_content)
            recv_msg += recv_content
        self.cach = recv_msg[buff_size:]
        return recv_msg[:buff_size]
            
    def _recv_pack(self):
        try:
            recv_msg, addr = self.socket.recvfrom(self.buf_size)
            parsed = self.parse_segment(recv_msg)
            if parsed.seq <= self.seq:
                print("secuencia incorrecta")
                self._recv_pack()
            elif parsed.tipo != b"MSG":
                print(f"tipo incorrecto, recibido: {parsed.tipo}")
                self._recv_pack()
            else:
                self.seq = (int.from_bytes(parsed.seq) + 1).to_bytes(2)
                self.socket.sendto(self.create_segment(MensajeTCP(b"ACK", self.seq)), self.destino)
                print(f"contenido recibido: {parsed.msg.decode()}")
                return parsed.msg
        except TimeoutError:
            print("error de timeout en recv")
            self._recv_pack()
