#!/usr/bin/env python
#! -*- coding: utf-8 -*-
import sys
import hashlib
import re
from struct import pack
import os
import time
from daemon import Daemon
import asyncore
import socket
import logging
import threading
import SocketServer

def string_to_header(data):
    data = data.split('\r\n\r\n', 1)
    lines = data[0].split('\r\n')
    headers = {}
    for line in lines:
        i = line.find(':')
        if i > 0:
            headers[line[:i].lower()] = line[i+1:].strip()
    return headers

def generate_handshake_key(headers, data):
    if ('sec-websocket-key1' not in headers and 'sec-websocket-key2' not in headers):
        return False
    digitRe = re.compile(r'[^0-9]')
    spacesRe = re.compile(r'\s')
    key1 = headers['sec-websocket-key1']
    key2 = headers['sec-websocket-key2']
    #print "key1 = %s and key 2 = %s" % (key1,key2)
    end = data
    space1 = len(spacesRe.findall(key1))
    space2 = len(spacesRe.findall(key2))
    key1 = int(digitRe.sub('', key1))
    key2 = int(digitRe.sub('', key2))
    if (space1 == 0 or space2 == 0 or key1 % space1 != 0 or key2 % space2 != 0):
        return False
    pkey1 = key1/space1
    pkey2 = key2/space2

    catstring = pack('!L',pkey1) + pack('!L',pkey2) + end
    magic = hashlib.md5(catstring).digest()
    return magic

class BaseWebSocketHandler:
    def __init__(self, server, client, connections):
        self.server = server
        self.client = client
        self.connections = connections

    def set_connections(self, connections):
        self.connections = connections

    def handshake(self, host, port, data):
        data = data.strip()
        logging.debug('Handshake - request: %s' % data)
        headers = string_to_header(data)
        if ('origin' not in headers):
            return False
        key = generate_handshake_key(headers, data.split('\r\n')[-1])
       
        # header['host'] instead of HOST? http://code.google.com/p/phpwebsocket/source/browse/trunk/%20phpwebsocket/server.php
        handshake = (
            "HTTP/1.1 101 WebSocket Protocol Handshake\r\n"
            "Upgrade: WebSocket\r\n"
            "Connection: Upgrade\r\n"
            "WebSocket-Origin: %(origin)s\r\n"
            "WebSocket-Location: ws://%(host)s:%(port)s/\r\n"
            "Sec-Websocket-Origin: %(origin)s\r\n"
            "Sec-Websocket-Location: ws://%(host)s:%(port)s/\r\n"
            "\r\n"
            "%(key)s"
        ) % {'origin': headers['origin'], 'host': host, 'port': port, 'key': key}
        logging.debug('Handshake - response: %s' % handshake)
        return handshake

    def onconnect(self):
        pass

    def onrecieve(self, message):
        for connection in self.connections:
            #if self.client != connection:
            self.onsend(connection, message)

    def onsend(self, connection, message):
        if isinstance(message, unicode):
            message = message.encode('utf-8')
        elif not isinstance(message, str):
            message = str(message)
        #try:
        connection.send("\x00%s\xff" % message)
        #except Exception, e:
        #    self.connections.remove(connection)

    def ondisconnect(self):
        pass

class WebSocketHandler(BaseWebSocketHandler):
    pass

class ThreadedWebSocketHandler(SocketServer.BaseRequestHandler, BaseWebSocketHandler):
    def setup(self):
        logging.debug('Incoming connection from %s' % repr(self.client_address))
        self.handler = self.server.handler(self.server, self.request, self.server.connections)

    def handle(self):
        data = self.request.recv(1024).strip()

        handshake = self.handshake(self.server.host, self.server.port, data)        
        if not handshake:
            return False
        self.request.send(handshake)
        self.server.connections.append(self.request)
        self.handler.set_connections(self.server.connections)
        self.handler.onconnect()

        while 1:
            data = self.request.recv(1024)
            if not data:
                self.request.close()
                self.server.connections.remove(self.request)
                self.handler.set_connections(self.server.connections)
                self.handler.ondisconnect()
                logging.debug('Connection close - No of connection:%s' % len(self.server.connections))
                break
            msgs = data.split('\xff')
            data = msgs.pop()
            for msg in msgs:
                if msg and msg[0] == '\x00':
                    logging.debug('Recived message:%s' % msg[1:])
                    self.handler.onrecieve(msg[1:])
                    break

class AsyncWebSocketHandler(asyncore.dispatcher_with_send, BaseWebSocketHandler):
    handshaken = False

    def __init__(self, sock=None, map=None):
        asyncore.dispatcher_with_send.__init__(self, sock, map)
    #def __init__(self):
    #    asyncore.dispatcher_with_send.__init__(self)
    #    self.handshaken = False

    def set_server(self, server):
        self.server = server

    def set_client(self, client):
        self.client = client

    def set_handler(self, handler):
        self.handler = handler(self.server, self.client, self.server.connections)

    def handle_read(self):
        try:
            data = self.recv(1024)
        except socket.timeout:
            self.handle_close()
            logging.debug('timeout')
            return False
        logging.debug('handle_read')
        if not data:
            self.handle_close()
            return False
            
        if not self.handshaken:
            handshake = self.handshake(self.server.host, self.server.port, data)
            if handshake:
                self.send(handshake)
                self.handshaken = True
                #for connection in self.server.connections:
                #    if int(time.time()) - connection.time > 60*60:
                #        self.server.connections.remove(connection)
                #logging.debug(str(self.client))
                #self.client.__dict__['time'] = int(time.time())
                self.server.connections.append(self.client)
                self.handler.set_connections(self.server.connections)
                self.handler.onconnect()
        else:
            msgs = data.split('\xff')
            data = msgs.pop()
            for msg in msgs:
                if msg and msg[0] == '\x00':
                    logging.debug('Recived message:%s' % msg[1:])
                    try:
                        self.handler.onrecieve(msg[1:])
                        #self.client.__dict__['time'] = int(time.time())
                    except Exception, e:
                        self.handle_close()
                    break

    def log_info(self, message, type='info'):
        logging.debug('log_info::%s::%s' % (type,message))

    def handle_close(self):
        logging.debug('handle_close')
        self.close()
        if self.client in self.server.connections:
            self.server.connections.remove(self.client)
            self.handler.set_connections(self.server.connections)
            logging.debug('Connection close - No of connection:%s' % len(self.server.connections))
            self.handler.ondisconnect()

class BaseWebSocketServer:
    def __init__(self, host, port, handler):
        self.connections = []
        self.host = host
        self.port = port
        self.handler = handler

class ThreadedWebSocketServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer, BaseWebSocketServer):
    def __init__(self, host, port, handler=BaseWebSocketHandler):
        BaseWebSocketServer.__init__(self, host, port, handler)
        SocketServer.TCPServer.__init__(self, (host,port), ThreadedWebSocketHandler)

class AsyncWebSocketServer(asyncore.dispatcher, BaseWebSocketServer):
    def __init__(self, host, port, handler=BaseWebSocketHandler):
        BaseWebSocketServer.__init__(self, host, port, handler)
        asyncore.dispatcher.__init__(self)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.set_reuse_addr()
        self.bind((host, port))
        self.listen(5)

    def handle_accept(self):
        sock, addr = self.accept()
        logging.debug('Incoming connection from %s' % repr(addr))
        handler = AsyncWebSocketHandler(sock)
        handler.set_server(self)
        handler.set_client(sock)
        handler.set_handler(self.handler)

class BaseWebSocket:
    pass

class ThreadedWebSocket(BaseWebSocket):
    def __init__(self, host, port, handler=BaseWebSocketHandler):
        server = ThreadedWebSocketServer(host, port, handler)
        server.serve_forever()

class AsyncWebSocket(BaseWebSocket):
    def __init__(self, host, port, handler=BaseWebSocketHandler):
        server = AsyncWebSocketServer(host, port, handler)
        asyncore.loop()

class MyDaemon(Daemon):
    def run(self):
        logging.debug('Starting server on %s:%s' % (HOST, PORT))
        AsyncWebSocket(HOST, PORT, WebSocketHandler)

if __name__ == "__main__":
    logging.basicConfig(filename='websocket.log', level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
    HOST, PORT = "localhost", 8080

    daemon = MyDaemon('/tmp/daemon-example.pid')
    if len(sys.argv) == 2:
        if 'start' == sys.argv[1]:
            daemon.start()
        elif 'stop' == sys.argv[1]:
            daemon.stop()
        elif 'restart' == sys.argv[1]:
            daemon.restart()
        else:
            print "Unknown command"
            sys.exit(2)
        sys.exit(0)
    else:
        print "usage: %s start|stop|restart" % sys.argv[0]
        sys.exit(2)

