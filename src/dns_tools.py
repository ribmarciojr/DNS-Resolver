import ctypes
import socket
import struct
from decorators.create_socket import create_socket_conn

class DNSHeaderBitfields(ctypes.BigEndianStructure):
    _fields_ = [
        ("qr", ctypes.c_uint16, 1),
        ("opcode", ctypes.c_uint16, 4),
        ("aa", ctypes.c_uint16, 1),
        ("tc", ctypes.c_uint16, 1),
        ("rd", ctypes.c_uint16, 1),
        ("ra", ctypes.c_uint16, 1),
        ("reserved", ctypes.c_uint16, 3),
        ("rcode", ctypes.c_uint16, 4)
    ]


class DNS:

    @staticmethod
    def rcode_to_str(rcode):
        """Convert response code to string."""
        if rcode == 0:
            return "No error"
        elif rcode == 1:
            return "Format error (name server could not interpret your request)"
        elif rcode == 2:
            return "Server failure"
        elif rcode == 3:
            return "Name Error (Domain does not exist)"
        elif rcode == 4:
            return "Not implemented (name server does not support your request type)"
        elif rcode == 5:
            return "Refused (name server refused your request for policy reasons)"
        else:
            return "WARNING: Unknown rcode"

    @staticmethod
    def qtype_to_str(qtype):
        """Convert query type to string."""
        if qtype == 1:
            return "A"
        elif qtype == 2:
            return "NS"
        elif qtype == 5:
            return "CNAME"
        elif qtype == 15:
            return "MX"
        elif qtype == 28:
            return "AAAA"
        else:
            return "WARNING: Record type not decoded"

    @staticmethod
    def class_to_str(qclass):
        """Convert query class to string."""
        if qclass == 1:
            return "IN"
        else:
            return "WARNING: Class not decoded"

    @staticmethod
    def decode_dns(raw_bytes):
        """Decode DNS message and display it."""
        print("Server Response")
        print("---------------")

        # Parse DNS header
        bitfields = DNSHeaderBitfields()
        (hdr_message_id, bitfields_raw, hdr_qdcount, hdr_ancount,
         hdr_nscount, hdr_arcount) = struct.unpack("!H2sHHHH", raw_bytes[:12])

        ctypes.memmove(ctypes.addressof(bitfields), bitfields_raw, 2)

        print(f"Message ID: {hdr_message_id}")
        print(f"Response code: {DNS.rcode_to_str(bitfields.rcode)}")
        print(f"Counts: Query {hdr_qdcount}, Answer {hdr_ancount}, "
              f"Authority {hdr_nscount}, Additional {hdr_arcount}")

        # Parse questions
        offset = 12
        for x in range(hdr_qdcount):
            qname = ""
            start = True
            while True:
                qname_len = struct.unpack("B", raw_bytes[offset:offset+1])[0]
                if qname_len == 0:
                    offset += 1
                    break
                if not start:
                    qname += "."
                qname += raw_bytes[offset+1:offset+1+qname_len].decode()
                offset += 1 + qname_len
                start = False

            qtype, qclass = struct.unpack("!HH", raw_bytes[offset:offset+4])
            print(f"Question {x + 1}:")
            print(f"  Name: {qname}")
            print(f"  Type: {DNS.qtype_to_str(qtype)}")
            print(f"  Class: {DNS.class_to_str(qclass)}")

            offset += 4

        # Parse answers
        for x in range(hdr_ancount):
            aname, atype, aclass, attl, ardlength = struct.unpack(
                "!HHHIH", raw_bytes[offset:offset+12]
            )

            if atype == 1:
                aaddr = socket.inet_ntop(socket.AF_INET, raw_bytes[offset+12:offset+16]) + " (IPv4)"
                offset += 16
            elif atype == 28:
                aaddr = socket.inet_ntop(socket.AF_INET6, raw_bytes[offset+12:offset+28]) + " (IPv6)"
                offset += 28
            else:
                aaddr = "WARNING: Addr format not IPv4 or IPv6"
                offset += 12

            print(f"Answer {x + 1}:")
            print(f"  Name: 0x{aname:x}")
            print(f"  Type: {DNS.qtype_to_str(atype)}, Class: {DNS.class_to_str(aclass)}, TTL: {attl}")
            print(f"  RDLength: {ardlength} bytes")
            print(f"  Addr: {aaddr}")

    @staticmethod
    def build_dns_query(domain: str, ip_protocol_version: int = 1) -> bytes:
        """
        Cria um pacote de consulta DNS para um domínio com as especificações detalhadas.
        """
        from random import randint

        # ID da mensagem (2 bytes) - valor arbitrário
        transaction_id = int(randint(0, 0xFFFF)) 

        # QR (1 bit) + OPCODE (4 bits) + AA (1 bit) + TC (1 bit) + RD (1 bit)
        # RD (bit 0) = 1 para Recursion Desired
        qr_opcode_aa_tc_rd = 0b0000000100000000  # RD = 1

        # RA (1 bit) + Z (3 bits) + RCODE (4 bits)
        # RA e RCODE são definidos na resposta do servidor (0 aqui por padrão)
        ra_z_rcode = 0b0000000000000000

        # QDCOUNT (2 bytes) - Número de questões
        qdcount = 1

        # ANCOUNT, NSCOUNT e ARCOUNT (2 bytes cada) - Todos definidos como 0 para consulta
        ancount = 0
        nscount = 0
        arcount = 0

        # Cabeçalho DNS: 12 bytes no total
        header = struct.pack(
            '>HHHHHH',
            transaction_id,
            qr_opcode_aa_tc_rd,
            qdcount,
            ancount,
            nscount,
            arcount
        )

        # Converter o domínio em formato DNS (exemplo: www.google.com -> 3www6google3com0)
        query = b''
        for part in domain.split('.'):
            query += struct.pack('B', len(part)) + part.encode()
        query += b'\x00' 

        # QTYPE (2 bytes) e QCLASS (2 bytes)
        qtype = ip_protocol_version  
        qclass = 1 
        question = query + struct.pack('>HH', qtype, qclass)

        return header + question

    @staticmethod
    @create_socket_conn("A")
    def send_dns_ipv4_request(server_socket: socket.socket, dns_query, remote_address: tuple):
        """
            Envia uma solicitação de resolução dns via ipv4
        """
        
        server_socket.sendto(dns_query, remote_address)

        # Recebe a resposta (até 1500 bytes conforme o padrão DNS)
        response, _ = server_socket.recvfrom(1500)

        return response
    
    @staticmethod
    @create_socket_conn("AAAA")
    def send_dns_ipv6_request(server_socket: socket.socket, dns_query, remote_address: tuple):
        """
            Envia uma solicitação de resolução dns via ipv6
        """
        
        server_socket.sendto(dns_query, remote_address)

        # Recebe a resposta (até 1500 bytes conforme o padrão DNS)
        response, _ = server_socket.recvfrom(1500)

        return response