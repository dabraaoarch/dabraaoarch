#!/usr/bin/env python3

import selectors
import socket
import io
import struct
import types
import sys
import traceback
	
''' Daniel Abraao de Melo 26-11-2021 '''

class Message:
	'''
	Inicia a instancia.
	'''
	def __init__(self, selector, sock, addr, request):
		self.selector = selector
		self.sock = sock
		self.addr = addr
		self.request = request
		self._recv_buffer = b""
		self._send_buffer = b""
		self._request_queued = False
		self._jsonheader_len = None
		self.jsonheader = None
		self.response = None

	'''Mudar essa funcao para utilizar design pattern'''
	'''
		Altera o tipo de evento do selector, de acordo com o parâmetro recebido
		o parâmetro é definido com base no evento que gerou a chamada 	
	'''
	def _set_selector_events_mask(self, mode):
		"""Set selector to listen for events: mode is 'r', 'w', or 'rw'."""
		if mode == "r":
			events = selectors.EVENT_READ
		elif mode == "w":
			events = selectors.EVENT_WRITE
		elif mode == "rw":
			events = selectors.EVENT_READ | selectors.EVENT_WRITE
		else:
			raise ValueError(f"Invalid events mask mode {repr(mode)}.")
		self.selector.modify(self.sock, events, data=self)

	''' 
		realiza a leitura de 4096 bytes do socket e salva em
		_recv_buffer 
	
	'''
	def _read(self):
		try:
			# Should be ready to read
			data = self.sock.recv(4096)
		except BlockingIOError:
			# Resource temporarily unavailable (errno EWOULDBLOCK)
			pass
		else:
			if data:
				self._recv_buffer += data
			else:
				raise RuntimeError("Peer closed.")

	'''
		envia os dados que estão no buffer de saida para o cliente, contabiliza
		a quantidade de bytes enviados e subtrai essa quantidade do buffer.
	'''
	def _write(self):
		if self._send_buffer:
			print("sending", repr(self._send_buffer), "to", self.addr)
			try:
				# Should be ready to write
				sent = self.sock.send(self._send_buffer)
			except BlockingIOError:
				# Resource temporarily unavailable (errno EWOULDBLOCK)
				pass
			else:
				self._send_buffer = self._send_buffer[sent:]
	'''
		retorna a mensagem (obj) codificada da forma solicitada (encoding) 
	'''
	def _json_encode(self, obj, encoding):
		return json.dumps(obj, ensure_ascii=False).encode(encoding)


	'''
		Retorna a mensagem (json_bytes) decodificada de acordo com a codificação
		informada (encoding)
	'''
	def _json_decode(self, json_bytes, encoding):
		tiow = io.TextIOWrapper(
			io.BytesIO(json_bytes), encoding=encoding, newline=""
		)
		obj = json.load(tiow)
		tiow.close()
		return obj


	'''
		Cria e retorna uma mensagem completa, contendo:
			- header 
			- payload
			- 2 bytes informando o tamanho do header
	'''
	def _create_message(
		self, *, content_bytes, content_type, content_encoding
	):
		jsonheader = {
			"byteorder": sys.byteorder,
			"content-type": content_type,
			"content-encoding": content_encoding,
			"content-length": len(content_bytes),
		}
		jsonheader_bytes = self._json_encode(jsonheader, "utf-8")
		message_hdr = struct.pack(">H", len(jsonheader_bytes))
		message = message_hdr + jsonheader_bytes + content_bytes
		return message

	def _process_response_json_content(self):
		content = self.response
		result = content.get("result")
		print(f"got result: {result}")

	def _process_response_binary_content(self):
		content = self.response
		print(f"got response: {repr(content)}")


	'''
		método onde inicia o processamento  do evento. Cada novo evento no
		socket chama esse procedimento e passa os dados (mask) para serem avaliados.
		 Verifica se é uma escrita ou leitura e faz o direcionamento 
	'''
	def process_events(self, mask):
		if mask & selectors.EVENT_READ:
			self.read()
		if mask & selectors.EVENT_WRITE:
			self.write()

	'''
		procedimento para leitura dos dados, na seguinte ordem:
			- Se o tamanho do cabeçalho (2bytes) ainda não foi informado
				realiza a leitura do mesmo a partir do socket.
			- se o tamanho do cabeçalho já foi recebido, faz o 
				recebimento da da mensagem.
			- se a mensagem já tiver sido recebida, faz o processamenta 
				da mesma.
	'''
	def read(self):
		self._read()

		if self._jsonheader_len is None:
			self.process_protoheader()

		if self._jsonheader_len is not None:
			if self.jsonheader is None:
				self.process_jsonheader()

		if self.jsonheader:
			if self.response is None:
				self.process_response()

	'''
		inicia o processamento de uma requisição de escrita.
		Primeiro verifica se já existe alguma mensagem na fila,
		caso contrário, realiza a requisição. Caso a mensagem seja
		corretamente adicionada ao buffer de saida ela é enviada e
		a a instância deve retornar ao modo de leitura.
	'''
	def write(self):
		if not self._request_queued:
			self.queue_request()

		self._write()

		if self._request_queued:
			if not self._send_buffer:
				# Set selector to listen for read events, we're done writing.
				self._set_selector_events_mask("r")

	'''
		Encerra a conexão e realiza o unregister do socket no selector.
		Após o unregister o socket é fechado.
	'''
	def close(self):
		print("closing connection to", self.addr)
		try:
			self.selector.unregister(self.sock)
		except Exception as e:
			print(
				"error: selector.unregister() exception for",
				f"{self.addr}: {repr(e)}",
			)

		try:
			self.sock.close()
		except OSError as e:
			print(
				"error: socket.close() exception for",
				f"{self.addr}: {repr(e)}",
			)
		finally:
			# Delete reference to socket object for garbage collection
			self.sock = None

	'''
		Realiza a montagem do cabeçalho adequado para a mensagem de envio,
		de acordo com o content-type. Adiciona a mensagem completa (payload + header)
		ao buffer de saida e altera o flag de requisição na fila para True
	'''
	def queue_request(self):
		content = self.request["content"]
		content_type = self.request["type"]
		content_encoding = self.request["encoding"]
		if content_type == "text/json":
			req = {
				"content_bytes": self._json_encode(content, content_encoding),
				"content_type": content_type,
				"content_encoding": content_encoding,
			}
		else:
			req = {
				"content_bytes": content,
				"content_type": content_type,
				"content_encoding": content_encoding,
			}
		message = self._create_message(**req)
		self._send_buffer += message
		self._request_queued = True

	'''
		Verifica se o buffer de entrada tem o tamanho maior ou igual a 2
		caso afirmativo, separa os dois primeiros bytes (tamanho do header json)
		e remove esses dois bytes do buffer. O tamanho do header json é salvo
		em _jsonheader_len.
	'''
	def process_protoheader(self):
		hdrlen = 2
		if len(self._recv_buffer) >= hdrlen:
			self._jsonheader_len = struct.unpack(
				">H", self._recv_buffer[:hdrlen]
			)[0]
			self._recv_buffer = self._recv_buffer[hdrlen:]

	'''
		A partir do tamanho do cabeçalho json (_jsonheader_len) faz o 
		processamento do cabeçalho,salvo em jsonheader, com codificação UTF-8.
		Caso algum campo esteja ausente, uma exceção é levantada.
	'''
	def process_jsonheader(self):
		hdrlen = self._jsonheader_len
		if len(self._recv_buffer) >= hdrlen:
			self.jsonheader = self._json_decode(
				self._recv_buffer[:hdrlen], "utf-8"
			)
			self._recv_buffer = self._recv_buffer[hdrlen:]
			for reqhdr in (
				"byteorder",
				"content-length",
				"content-type",
				"content-encoding",
			):
				if reqhdr not in self.jsonheader:
					raise ValueError(f'Missing required header "{reqhdr}".')

	'''
		Realiza o processamento do payload. O tamanho do payload é
		obtido por meio do cabeçalho json. Caso o content-encoding não
		seja binário, a mensagem é decodificada. Caso o conteúdo
		seja binário, o conteúdo é salvo em response, para ser reenviado
		ao remetente.
	'''
	def process_response(self):
		content_len = self.jsonheader["content-length"]
		if not len(self._recv_buffer) >= content_len:
			return
		data = self._recv_buffer[:content_len]
		self._recv_buffer = self._recv_buffer[content_len:]
		if self.jsonheader["content-type"] == "text/json":
			encoding = self.jsonheader["content-encoding"]
			self.response = self._json_decode(data, encoding)
			print("received response", repr(self.response), "from", self.addr)
			self._process_response_json_content()
		else:
			# Binary or unknown content-type
			self.response = data
			print(
				f'received {self.jsonheader["content-type"]} response from',
				self.addr,
			)
			self._process_response_binary_content()
		# Close when response has been processed
		self.close()
		

''' 
	Cria o Selector, que é responsável por monitorar os sockets abertos
	para cada novo socket criado, ele é registrado dentro do selector. Quando
	uma determinada conexão gera um evento, o selector retorna o um event
	composto por uma chave e uma máscara.
''' 
selector_holder = selectors.DefaultSelector()

'''
	Aceita a conexão e registra ela no selector, junto com uma instância
	da classe Message, que contém as operações de leitura e escrita e 
	manipulação dos dados.
'''
def accept_wrapper(sock):
	connection_holder, server_address = sock.accept()  # Should be ready to read
	print("accepted connection from", server_address)
	connection_holder.setblocking(False)
	message = Message(selector_holder, connection_holder, server_address)
	selector_holder.register(connection_holder, selectors.EVENT_READ, data=message)

'''
	Verifica se a chamada do script foi realizada de forma correta,
	caso contrário encerra a execução.
'''
if len(sys.argv) != 3:
	print("usage:", sys.argv[0], "<host> <port>")
	sys.exit(1)

'''
	Cria um novo socket TCP com base no endereço e porta
	informados na chamada do script.
'''
host_address, host_port = sys.argv[1], int(sys.argv[2])
socket_holder = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

'''
	Configura o socket, realiza o bind, inicia a escuta e registra o
	socket no selector.
	O socket é o configurado para aceitar multiplas conexões e não
	realizar o bloqueio ao iniciar uma conversa com um cliente.
'''
socket_holder.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
socket_holder.bind((host_address, host_port))
socket_holder.listen()
print("listening on", (host_address, host_port))
socket_holder.setblocking(False)
selector_holder.register(socket_holder, selectors.EVENT_READ, data=None)


'''
	Loop principal do script, cada novo evento de socket ele verifica se
	o evento foi gerado por uma nova conexão, se for, ele chama a função
	accept_wrapper, que vai criar uma nova instância da classe Message e
	registrar ela, junto com a nova conexão no selector. Caso o evento
	tenha sido gerado por uma conexão já existente, a instância de Message
	é recuperada e os dados do novo evento (mask) são passados para o 
	método process_events do objeto message. 
'''
try:
	while True:
		events = selector_holder.select(timeout=None)
		for key, mask in events:
			if key.data is None:
				accept_wrapper(key.fileobj)
			else:
				message = key.data
				try:
					message.process_events(mask)
				except Exception:
					print(
						"main: error: exception for",
						f"{message.addr}:\n{traceback.format_exc()}",
					)
					message.close()
except KeyboardInterrupt:
	print("caught keyboard interrupt, exiting")
finally:
	sel.close()