#!/usr/bin/env python3

import socket

''' Daniel Abraao de Melo - 20-11-2021 '''

ENDERECO_HOSPEDEIRO='127.0.0.1'
PORTA_HOSPEDEIRO = 61234
BUFFER_SIZE = 1024

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as socket_holder:
	socket_holder.bind((ENDERECO_HOSPEDEIRO, PORTA_HOSPEDEIRO))
	socket_holder.listen()
	connection_holder, connection_address = socket_holder.accept()
	with connection_holder:
		print("Conectado em", connection_address)
		while True:
				data = connection_holder.recv(BUFFER_SIZE)
				if not data:
					break
				connection_holder.sendall(data)
