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
        self.last_sent = b""

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
        print(f"seq: {int.from_bytes(self.seq)}")
        # enviar un mensaje syn
        msg = MensajeTCP(b"SYN", self.seq)
        to_send = self.create_segment(msg)
        while True:
            while True:
                print(f"seq: {int.from_bytes(self.seq)}")
                try:
                    self.socket.sendto(to_send, addr)
                    # recibir un mensaje devuelta
                    rcv_msg, serv_addr = self.socket.recvfrom(19) # TODO: esta direccion deberia ser la del nuevo socket?
                    break
                except TimeoutError:
                    print("timeout en connect (mensaje confirmacion)")
                    continue

            # verificar ack, syn y addr
            parsed = self.parse_segment(rcv_msg)
            if parsed.tipo != b"A+S":
                print("tipo equivocado (esperado A+S)")
                print(f"tipo: {parsed.tipo.decode()}")
                
            elif parsed.seq <= self.seq:
                print("Secuencia incorrecta")
                print(f"seqs: {int.from_bytes(parsed.seq)} <= {int.from_bytes(self.seq)}")
                
            else:
                print("mensaje syn + ack recibido")
                self.destino = serv_addr
                self.seq = (int.from_bytes(parsed.seq) + 1).to_bytes(2)
                # enviar mensaje ack
                msg = MensajeTCP(b"ACK", self.seq)
                to_send = self.create_segment(msg)
                self.socket.sendto(to_send, self.destino)
                self.last_sent = to_send
                print("conexion establecida!!")
                break

    def accept(self):
        """
        escucha por solicitudes a conexión y las acepta mediante 3-way handshake

        retorna:
            (SocketTCP para la conexión, dirección del SocketTCP)
        """
        while True:
            print("recibiendo solicitudes")
            try:
                recv_msg, addr = self.socket.recvfrom(self.buf_size)
                parsed = self.parse_segment(recv_msg)
                if parsed.tipo != b"SYN":
                    print("mensaje no es de tipo SYN")
                    continue
                print("mensaje tipo syn recibido!")
            except TimeoutError:
                print("error de timeout en accept (primer mensaje)")
                continue

            # crear un nuevo socket para la comunicacion
            new_socket = SocketTCP()
            new_socket.seq = (int.from_bytes(parsed.seq) + 1).to_bytes(2)
            print(f"new_skt.seq: {int.from_bytes(new_socket.seq)}")
            new_socket.destino = addr
            new_addr = ('localhost', 8500)
            # direccion fija por simplicidad (no se puede crear 2 clientes al mismo tiempo)
            new_socket.bind(new_addr)
            # enviar mensaje syn + ack
            to_send = self.create_segment(MensajeTCP(b"A+S", new_socket.seq))
            
            while True:
                try:
                    new_socket.socket.sendto(to_send, addr)
                    print("mensaje tipo syn+ack enviado!")
                    # recibir mensaje tipo ack
                    recv_msg, addr_2 = new_socket.socket.recvfrom(self.buf_size)
                    parsed = self.parse_segment(recv_msg)
                    print(f"parsed.seq: {int.from_bytes(parsed.seq)}, skt.seq: {int.from_bytes(new_socket.seq)}")
                    if parsed.tipo == b"MSG":
                        print("hanshake incompleto, pero continuando")
                        break
                    elif parsed.seq <= new_socket.seq:
                        print("error de secuencia en accept (mensaje de confirmacion)")
                    elif parsed.tipo == b"ACK":
                        print("mensaje ack recibido!")
                        break
                    else:
                        continue
                except TimeoutError:
                    print("error de timeout en accept (mensaje de confirmacion)")

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
        print(f"seq actual: {int.from_bytes(self.seq)}")

        # enviar el primer mensaje que contiene el tamaño del mensaje
        full_msg_len = len(msg)
        self._send_pack(str(full_msg_len).encode())
        i = 0
        while i < full_msg_len:
            # enviar 16 bytes de mensaje
            self._send_pack(msg[i:i+self.msg_len])
            i += self.msg_len

    def _send_pack(self, content: bytes):
        print(f"contenido a mandar: {content.decode()} a direccion {self.destino}")
        print(f"seq actual: {int.from_bytes(self.seq)}")
        tipo = b"MSG"
        msg_tcp = MensajeTCP(tipo, self.seq, content)
        pack = self.create_segment(msg_tcp)
        

        while True:
            # caso 1: todo bien
            try:
                self.socket.sendto(pack, self.destino)
                recv_msg, addr= self.socket.recvfrom(self.buf_size)
                parsed = self.parse_segment(recv_msg)
                if parsed.seq <= self.seq:
                    print(f"secuencia incorrecta en confirmacion de send: {int.from_bytes(parsed.seq)} <= {int.from_bytes(self.seq)}")
                    print("enviando confirmacion anterior")
                    self.socket.sendto(self.last_sent, self.destino)
                    self._send_pack(content)
                else:
                    print("mensaje enviado con confirmacion recibida")
                    # TODO: quizas esto debiera ser el largo del mensaje enviado u otro numero que permita verificar
                    self.seq = (int.from_bytes(parsed.seq) + 1).to_bytes(2)
                    break
            # caso 2: no se recibe el mensaje de confirmación
            except TimeoutError:
                print(f"\nerror de timeout en send\ncontenido del mensaje:\ntipo: {msg_tcp.tipo.decode()}\nseq: {int.from_bytes(msg_tcp.seq)}")
        
    def recv(self, buff_size):
        # caso 1: primer mensaje (msg_len)
        print("recibiendo el largo del mensaje")
        print(f"seq actual: {int.from_bytes(self.seq)}")
        if self.expecting <= 0:
            try:
                recvd = self._recv_pack().decode()
                if recvd is not None:
                    self.expecting = int(recvd)
                else:
                    return self.recv(buff_size)
            except TimeoutError:
                print("timeout error al recibir largo del mensaje")
                return self.recv(buff_size)
        # caso 2: continuacion del mensaje
        recv_msg = self.cach
        print(f"rcv_msg hasta ahora: {recv_msg}")
        pack_len = min(self.expecting, buff_size)
        while pack_len > 0:
            recv_content = self._recv_pack()
            if recv_content != None:
                self.expecting -= len(recv_content)
                pack_len -= len(recv_content)
                recv_msg += recv_content
                print(f"rcv_msg hasta ahora (dentro de while): {recv_msg}")
        self.cach = recv_msg[buff_size:]
        print(f"expecting: {self.expecting}")
        return recv_msg[:buff_size]
            
    def _recv_pack(self):
        print(f"seq actual: {int.from_bytes(self.seq)}")
        try:
            recv_msg, addr = self.socket.recvfrom(self.buf_size)
            parsed = self.parse_segment(recv_msg)
            if parsed.seq <= self.seq:
                print(f"secuencia incorrecta, {int.from_bytes(parsed.seq)} <= {int.from_bytes(self.seq)}")
                print("reenviando ultimo mensaje")
                self.socket.sendto(self.last_sent, self.destino)
                return self._recv_pack()
            elif parsed.tipo != b"MSG":
                print(f"tipo incorrecto, recibido: {parsed.tipo}")
                return
            else:
                self.seq = (int.from_bytes(parsed.seq) + 1).to_bytes(2)
                to_send = self.create_segment(MensajeTCP(b"ACK", self.seq))
                self.socket.sendto(to_send, self.destino)
                self.last_sent = to_send
                print(f"contenido recibido: {parsed.msg.decode()}")
                return parsed.msg
        except TimeoutError:
            print("error de timeout en recv")
            return self._recv_pack()
