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
        last_sent (bytes): el ultimo mensaje de cinfirmacion enviado
        debug (bool): imprime mensajes que indican el manejo de perdidas
    """

    def __init__(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.destino = ('localhost', 8000)
        self.seq = b""
        self.header_size = 5
        self.msg_len = 16
        self.buf_size = self.header_size + self.msg_len
        self.expecting = 0
        self.socket.settimeout(5) # espera 5 segundos antes de reenviar
        self.cach = b""
        self.last_sent = b""
        self.debug = False

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
        self.debug_prints("conectando")
        self.seq = randint(0, 100).to_bytes(2)
        # enviar un mensaje syn
        msg = MensajeTCP(b"SYN", self.seq)
        to_send = self.create_segment(msg)
        while True:
            while True:
                try:
                    self.socket.sendto(to_send, addr)
                    # recibir un mensaje devuelta
                    rcv_msg, serv_addr = self.socket.recvfrom(19) # TODO: esta direccion deberia ser la del nuevo socket?
                    break
                except TimeoutError:
                    self.debug_prints("timeout en connect (mensaje confirmacion)")
                    continue

            # verificar ack, syn y addr
            parsed = self.parse_segment(rcv_msg)
            if parsed.tipo != b"A+S":
                self.debug_prints("tipo equivocado (esperado A+S)")
                self.debug_prints(f"tipo: {parsed.tipo.decode()}")
                
            elif parsed.seq <= self.seq:
                self.debug_prints("Secuencia incorrecta")
                self.debug_prints(f"seqs: {int.from_bytes(parsed.seq)} <= {int.from_bytes(self.seq)}")
                
            else:
                self.destino = serv_addr
                self.seq = (int.from_bytes(parsed.seq) + 1).to_bytes(2)
                # enviar mensaje ack
                msg = MensajeTCP(b"ACK", self.seq)
                to_send = self.create_segment(msg)
                self.socket.sendto(to_send, self.destino)
                self.last_sent = to_send
                self.debug_prints("conexion establecida!!")
                break

    def accept(self):
        """
        escucha por solicitudes a conexión y las acepta mediante 3-way handshake

        retorna:
            (SocketTCP para la conexión, dirección del SocketTCP)
        """
        while True:
            self.debug_prints("recibiendo solicitudes")
            try:
                recv_msg, addr = self.socket.recvfrom(self.buf_size)
                parsed = self.parse_segment(recv_msg)
                if parsed.tipo != b"SYN":
                    self.debug_prints("mensaje no es de tipo SYN")
                    continue

            except TimeoutError:
                self.debug_prints("error de timeout en accept (primer mensaje)")
                continue

            # crear un nuevo socket para la comunicacion
            new_socket = SocketTCP()
            new_socket.seq = (int.from_bytes(parsed.seq) + 1).to_bytes(2)
            new_socket.destino = addr
            new_addr = ('localhost', 8500)
            # direccion fija por simplicidad (no se puede crear 2 clientes al mismo tiempo)
            new_socket.bind(new_addr)
            # enviar mensaje syn + ack
            to_send = self.create_segment(MensajeTCP(b"A+S", new_socket.seq))
            
            while True:
                try:
                    new_socket.socket.sendto(to_send, addr)
                    # recibir mensaje tipo ack
                    recv_msg, addr_2 = new_socket.socket.recvfrom(self.buf_size)
                    parsed = self.parse_segment(recv_msg)
                    if parsed.tipo == b"MSG":
                        self.debug_prints("hanshake incompleto, pero continuando")
                        break
                    elif parsed.seq <= new_socket.seq:
                        self.debug_prints("error de secuencia en accept (mensaje de confirmacion)")
                    elif parsed.tipo == b"ACK":
                        break
                    else:
                        continue
                except TimeoutError:
                    self.debug_prints("error de timeout en accept (mensaje de confirmacion)")

            self.debug_prints("conexion establecida!!")
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
            self.debug_prints("conexion no fue establecida")
            return
        self.debug_prints(f"mensaje completo por enviar: {msg.decode()}")

        # enviar el primer mensaje que contiene el tamaño del mensaje
        full_msg_len = len(msg)
        self._send_pack(str(full_msg_len).encode())
        i = 0
        while i < full_msg_len:
            # enviar 16 bytes de mensaje
            self._send_pack(msg[i:i+self.msg_len])
            i += self.msg_len

    def _send_pack(self, content: bytes):

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
                    self.debug_prints(f"secuencia incorrecta en confirmacion de send: {int.from_bytes(parsed.seq)} <= {int.from_bytes(self.seq)}")
                    self.debug_prints("enviando confirmacion anterior")
                    self.socket.sendto(self.last_sent, self.destino)
                    self._send_pack(content)
                elif parsed.tipo == b"FIN":
                    self.debug_prints("se ha recibido un mensaje tipo FIN")
                    self.recv_close()
                    return
                else:
                    # TODO: quizas esto debiera ser el largo del mensaje enviado u otro numero que permita verificar
                    self.seq = (int.from_bytes(parsed.seq) + 1).to_bytes(2)
                    break
            # caso 2: no se recibe el mensaje de confirmación
            except TimeoutError:
                self.debug_prints(f"error de timeout en send")
        
    def recv(self, buff_size):
        # caso 1: primer mensaje (msg_len)
        if self.expecting <= 0:
            try:
                recvd = self._recv_pack().decode()
                if recvd is not None:
                    self.expecting = int(recvd)
                else:
                    return self.recv(buff_size)
            except TimeoutError:
                self.debug_prints("timeout error al recibir largo del mensaje")
                return self.recv(buff_size)
        # caso 2: continuacion del mensaje
        recv_msg = self.cach
        pack_len = min(self.expecting, buff_size)
        while pack_len > 0:
            recv_content = self._recv_pack()
            if recv_content != None:
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
                self.debug_prints(f"secuencia incorrecta, {int.from_bytes(parsed.seq)} <= {int.from_bytes(self.seq)}")
                self.debug_prints("reenviando ultimo mensaje")
                self.socket.sendto(self.last_sent, self.destino)
                return self._recv_pack()
            elif parsed.tipo == b"FIN":
                self.debug_prints("se ha recibido un mensaje tipo FIN")
                self.recv_close()
                return
            elif parsed.tipo != b"MSG":
                self.debug_prints(f"tipo incorrecto, recibido: {parsed.tipo}")
                return
            else:
                self.seq = (int.from_bytes(parsed.seq) + 1).to_bytes(2)
                to_send = self.create_segment(MensajeTCP(b"ACK", self.seq))
                self.socket.sendto(to_send, self.destino)
                self.last_sent = to_send
                return parsed.msg
        except TimeoutError:
            self.debug_prints("error de timeout en recv")
            return self._recv_pack()

    def close(self):
        to_send = self.create_segment(MensajeTCP(b"FIN", self.seq))
        tries = 0
        while tries < 3:
            try:
                self.debug_prints(f"enviando mensaje fin")
                self.socket.sendto(to_send, self.destino)
                recv_msg, _ = self.socket.recvfrom(self.buf_size)
                parsed = self.parse_segment(recv_msg)
                if parsed.tipo == b"A+F":
                    self.seq = (int.from_bytes(parsed.seq) + 1).to_bytes(2)
                    break

            except TimeoutError:
                self.debug_prints("error de timeout en fin")
                tries += 1
            
        if tries < 3:
            tries = 0
            to_send = self.create_segment(MensajeTCP(b"ACK", self.seq))
            self.debug_prints("mensaje de confirmacion de fin de comunicacion junto a solicitud fin recibido, enviando confirmacion devuelta")

        while tries < 3:
            try:
                self.socket.sendto(to_send, self.destino)
                self.debug_prints("mensaje enviado")
                self.socket.recvfrom(self.buf_size)
            except TimeoutError:
                tries += 1
                self.debug_prints(f"timeout error en close, intento # {tries}")
            except:
                self.debug_prints("otro error en close, quizas el socket ya se cerró??")
                break

        self.socket.close()

    def recv_close(self):
        to_send = self.create_segment(MensajeTCP(b"A+F", self.seq))
        tries = 0
        while tries < 3:
            try:
                self.debug_prints("enviando mensaje tipo A+F")
                self.socket.sendto(to_send, self.destino)
                recv_msg, _ = self.socket.recvfrom(self.buf_size)
                parsed = self.parse_segment(recv_msg)
                if parsed.tipo == b"ACK" and self.seq < parsed.seq:
                    self.debug_prints("mensaje tipo ACK recibido")
                    break
            except TimeoutError:
                self.debug_prints("timeout error en recv_close")
                tries += 1
            except: 
                self.debug_prints("otro error en close, quizas el socket ya se cerró??")
                break

        self.socket.close()

    def debug_prints(self, msg: str):
        if self.debug == True:
            print(msg)