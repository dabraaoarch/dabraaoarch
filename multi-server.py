#!/usr/bin/env python3

import selectors
import socket
import types
import sys 

''' Daniel Abraao de Melo - 20-11-2021 '''

BUFFER_SIZE = 1024

selector_holder = selectors.DefaultSelector()

def accept_wrapper(sock):
	connection_holder, client_address = sock.accept()
	print("Conexão de {} aceita.".format(
		client_address
		)
	)
	connection_holder.setblocking(False)
	socket_data = types.SimpleNamespace(
		addr=client_address,
		inb=b'', 
		outb=b''
	)
	events = selectors.EVENT_READ | selectors.EVENT_WRITE
	selector_holder.register(
		connection_holder, 
		events, 
		data=socket_data
	)
	
def service_connection(key, mask):
	sock = key.fileobj
	socket_data = key.data
	if mask & selectors.EVENT_READ:
		received_data = sock.recv(BUFFER_SIZE)
		if received_data:
			socket_data.outb += received_data
		else:
			print('Encerrando a conexao com {}'.format(
				socket_data.addr
				)
			)
			selector_holder.unregister(sock)
			sock.close()
	if mask & selectors.EVENT_WRITE:
		if socket_data.outb:
			print('Respondendo {} para {}'.format(
				repr(socket_data.outb), 
				socket_data.addr
				)
			)
			data_sent = sock.send(socket_data.outb)
			socket_data.outb = socket_data.outb[data_sent:]

if len(sys.argv) != 3:
	print("Como utilizar esse script: {} <server_ip> <server_port>".format(
		sys.argv[0]
		)
	)
	sys.exit(1)


server_ip = sys.argv[1]
server_port = int(sys.argv[2])

local_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
local_sock.bind((server_ip, server_port))
local_sock.listen()
print("Listening on [ {} : {} ]".format(server_ip, server_port))
local_sock.setblocking(False)
selector_holder.register(local_sock, selectors.EVENT_READ, data=None)


try: 
	while True:
		events = selector_holder.select(timeout=None)
		for key, mask in events:
			if key.data is None:
				accept_wrapper(key.fileobj)
			else:
				service_connection(key, mask)
except KeyboardInterrupt:
	print("Interrupção do teclado capturada, saindo")
finally:
	selector_holder.close()	

			
