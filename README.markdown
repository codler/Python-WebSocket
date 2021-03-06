# Python WebSocket

* Tested and works on Python 2.5

* PROTOCOL - draft-hixie-thewebsocketprotocol-76 / draft-ietf-hybi-thewebsocketprotocol-00

* CONNECTION METHOD - Asynchronous socket (RECOMMEND) / "One-thread-per-connection" (no longer maintained)

## How to use

	class WebSocketHandler(BaseWebSocketHandler):
		def onconnect(self):
			pass

		def onrecieve(self, message):
			for connection in self.connections:
				self.onsend(connection, message)

		def onsend(self, connection, message):
			if isinstance(message, unicode):
				message = message.encode('utf-8')
			elif not isinstance(message, str):
				message = str(message)
			connection.send("\x00%s\xff" % message)

		def ondisconnect(self):
			pass

#### Some notes
* One-thread-per-connection takes about >8MB RAM for each connection! I recommend using asynchronous-socket instead.

* Bug, "self.server.connections" does not always remove unused connection from the list.

## Feedback

I appreciate all feedback, thanks!