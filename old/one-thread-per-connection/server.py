#!/usr/bin/env python
#! -*- coding: utf-8 -*-
import SocketServer
import sys
import hashlib
import re
from struct import pack
import threading
import os
import time
from daemon import Daemon
import gc


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


class MyTCPHandler(SocketServer.BaseRequestHandler):
    """
    The RequestHandler class for our server.

    It is instantiated once per connection to the server, and must
    override the handle() method to implement communication to the
    client.
    """
    def setup(self):
        if not hasattr(self.server, 'connections'):
            setattr(self.server, 'connections', [])
        self.server.connections.append(self.request)

    def finish(self):
        print "finish"

    def handshake(self, host, port, data):
        data = data.strip()
        #logging.debug('Handshake - request: %s' % data)
        headers = string_to_header(data)
        if ('origin' not in headers):
            return False
        key = generate_handshake_key(headers, data.split('\r\n')[-1])
        #print "KEY = %s" % (key)
       
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
        #logging.debug('Handshake - response: %s' % handshake)
        return handshake

    def handle(self):
        #HOST, PORT = "heroesofconquest.se", 8080
        # self.request is the TCP socket connected to the client
        data = self.request.recv(1024).strip()

        handshake = self.handshake(self.server.host, self.server.port, data)        
        print handshake
        self.request.send(handshake)
        #self.request.send("\x00%s\xff" % gc.collect())
        while 1:
            data = self.request.recv(1024)
            if not data:
                print 'connection close'
                self.request.close()
                self.server.connections.remove(self.request)
                for i in self.server.connections:
                    if i != self.request:
                        i.send("\x00%s\xff" % 'klient disconnect')
				#        i.send("\x00%s\xff" % gc.collect())
                #self.request.send("\x00%s\xff" % gc.collect())
                break
            msgs = data.split('\xff')
            data = msgs.pop()
            #self.request.send("\x00%s\xff" % threading.activeCount())
            self.request.send("\x00%s\xff" % len(self.server.connections))
            for msg in msgs:
                if msg and msg[0] == '\x00':
                    print msg[1:]
                    self.request.send("\x00%s\xff" % msg[1:])
                    for i in self.server.connections:
                        if i != self.request:
                            i.send("\x00%s\xff" % msg[1:])
                    break

class ThreadedTCPServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
    def __init__(self, server_address, RequestHandlerClass):
        SocketServer.TCPServer.__init__(self, server_address, RequestHandlerClass)
        self.host = server_address[0]
        self.port = server_address[1]

class MyDaemon(Daemon):
    def run(self):
        server = ThreadedTCPServer((HOST, PORT), MyTCPHandler)
        server.serve_forever()

if __name__ == "__main__":
    HOST, PORT = "heroesofconquest.se", 8080

    # Create the server, binding to localhost on port 9999
    #server = SocketServer.TCPServer((HOST, PORT), MyTCPHandler)

    # Activate the server; this will keep running until you
    # interrupt the program with Ctrl-C
    #server.serve_forever()


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

