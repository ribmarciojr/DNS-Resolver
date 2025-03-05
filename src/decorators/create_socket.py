import socket
from typing import Callable

def create_socket_conn(qtype: str) -> Callable:  # 'A' para IPv4, 'AAAA' para IPv6
    """
        A decorator that creates a UDP socket for network communication, automatically setting
        the IP protocol version (IPv4 or IPv6) based on the `qtype` parameter.

        The created socket is passed as the `server_socket` argument to the decorated function.
        After the function execution, the socket is automatically closed.

        Parameters:
            qtype (str): Defines the IP version. Must be 'A' for IPv4 or 'AAAA' for IPv6.

        Exceptions:
            ValueError: If `qtype` is not 'A' or 'AAAA'.

        Example usage:

        @create_socket_conn("A")  # Creates an IPv4 socket
        def send_message(message: str, server_socket: socket.socket):
            server_socket.sendto(message.encode(), ("127.0.0.1", 8080))
            print("Message sent!")

        send_message("Hello, UDP!")
    """
    
    def wrapper(func: Callable):
        def inner(*args, **kwargs):
            ip_protocol = {
                "A": socket.AF_INET,  # IPv4
                "AAAA": socket.AF_INET6  # IPv6
            }
            
            ip_version = ip_protocol.get(qtype)

            if not ip_version:
                raise ValueError(f"Invalid argument for IP protocol version: {qtype}")

            server_socket = socket.socket(ip_protocol[qtype], socket.SOCK_DGRAM)
            
            try:
                return func(*args, **kwargs, server_socket=server_socket)
            finally:
                server_socket.close()
        
        return inner
    return wrapper
