#!/usr/bin/env python3

import socket

''' Daniel Abraao de Melo - 20-11-2021 '''

ENDERECO_SERVIDOR = '127.0.0.1'
PORTA_SERVIDOR = 61234
BUFFER_SIZE = 1024

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as socket_holder:
	socket_holder.connect((ENDERECO_SERVIDOR, PORTA_SERVIDOR))
	socket_holder.sendall(b'Daniel Melo')
	pacote_dados = socket_holder.recv(BUFFER_SIZE)
	
print('Recebido', repr(pacote_dados))