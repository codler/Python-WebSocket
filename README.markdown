# Python WebSocket

* Tested and works on Python 2.5

* PROTOCOL - draft-hixie-thewebsocketprotocol-76 / draft-ietf-hybi-thewebsocketprotocol-00

* CONNECTION METHOD - Asynchronous socket (RECOMMEND) / "One-thread-per-connection"

## How to use

	class WebSocketHandler(BaseWebSocketHandler):
		def onconnect(self):
			pass

		def onrecieve(self, message):
			for connection in self.connections:
				if self.client != connection:
					self.onsend(connection, message)

		def onsend(self, connection, message):
			connection.send("\x00%s\xff" % message)

		def ondisconnect(self):
			pass

#### Some notes
* One-thread-per-connection takes about >8MB RAM for each connection! I recommend using asynchronous-socket instead.

## Feedback

I appreciate all feedback, thanks!