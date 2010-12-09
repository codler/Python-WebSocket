# Python WebSocket


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
* One thread per connection takes about 8MB RAM each!

## Feedback

I appreciate all feedback, thanks!