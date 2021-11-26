#!/usr/bin/env python3

import selectors
import socket
import types
import sys
''' Daniel Abraao de Melo - 20-11-2021 '''

BUFFER_SIZE = 1024

selector_holder = selectors.DefaultSelector()
messages = [b'Primeira mensage do cliente.', b'Segunda mensagem do cliente.']

def start_connections(host, port, num_connections):
	server_address = (host, port)
	for i in range(0, num_connections):
		connection_id = i + 1
		print('Iniciando a conexão id: [{}] com servidor: [{}]'.format(
			connection_id, 
			server_address
			)
		)
		sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		sock.setblocking(False)
		sock.connect_ex(server_address)
		events = selectors.EVENT_READ | selectors.EVENT_WRITE
		data = types.SimpleNamespace(
			connid=connection_id,
			msg_total=sum(len(m) for m in messages),
			recv_total=0,
			messages=list(messages),
			outb=b''
		)
		selector_holder.register(
			sock, 
			events, 
			data=data
		)
		
def service_connection(key, mask):
	sock = key.fileobj
	socket_data = key.data
	if mask & selectors.EVENT_READ:
		received_data = sock.recv(BUFFER_SIZE)
		if received_data:
			print('Recebidos {} da conexão {}'.format(
				repr(received_data), 
				socket_data.connid
				)
			)
			socket_data.recv_total += len(received_data)
		if not received_data or socket_data.recv_total == socket_data.msg_total:
			print('Encerrando a conexão {}'.format(
				socket_data.connid
				)
			)
			selector_holder.unregister(sock)
			sock.close()
	if mask & selectors.EVENT_WRITE:
		if not socket_data.outb and socket_data.messages:
			socket_data.outb = socket_data.messages.pop(0)
		if socket_data.outb:
			print('Enviando {} para conexão {}'.format(
				repr(socket_data.outb), 
				socket_data.connid
				)
			)
			data_sent = sock.send(socket_data.outb)
			socket_data.outb = socket_data.outb[data_sent:]
		
if len(sys.argv) != 4:
	print("Como utilizar esse script: {} <server_ip> <server_port> <num_connections>".format(
		sys.argv[0]
		)
	)
	sys.exit(1)
	
server_ip = sys.argv[1]
server_port = sys.argv[2]
num_connections = sys.argv[3]

start_connections(
	server_ip, 
	int(server_port), 
	int(num_connections)
)
	
try:
	while True:
		events = selector_holder.select(timeout=1)
		if events:
			for key, mask in events:
				service_connection(key, mask)
		if not selector_holder.get_map():
			break
except KeyboardInterrupt:
	print("Interrupção do teclado capturada, saindo")
finally:
	selector_holder.close()	
