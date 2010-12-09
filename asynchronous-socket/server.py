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

class MyDaemon(Daemon):
    def run(self):
        logging.debug('Starting server on %s:%s' % (HOST, PORT))
        server = EchoServer(HOST, PORT)
        asyncore.loop()

class EchoHandler(asyncore.dispatcher_with_send):
    handshaken = False

    def _init__(self):
        asyncore.dispatcher_with_send.__init__(self)
        #self.client = client
        #self.server = server
        self.handshaken = False

    def set_server(self, server):
        self.server = server

    def set_client(self, client):
        self.client = client

    def handshake(self, host, port, data):
        data = data.strip()
        logging.debug('Handshake - request: %s' % data)
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
        logging.debug('Handshake - response: %s' % handshake)
        return handshake
    
    def handle_read(self):
        data = self.recv(1024)
        logging.debug('handle_read')
        if not data:
            self.handle_close()
            
        if not self.handshaken:
            handshake = self.handshake(self.server.host, self.server.port, data)
            if handshake:
                self.send(handshake)
                self.handshaken = True
        else:
            msgs = data.split('\xff')
            data = msgs.pop()
            for msg in msgs:
                if msg and msg[0] == '\x00':
                    #print msg[1:]
                    logging.debug('Recived message:%s' % msg[1:])
                    self.send("\x00%s\xff" % msg[1:])
                    for i in self.server.connections:
                        if i != self.client:
                            i.send("\x00%s\xff" % msg[1:])
                    break
    def log_info(self, message, type='info'):
        logging.debug('log_info::%s::%s' % (type,message))

    def handle_close(self):
        logging.debug('handle_close')
        self.close()
        if self.client in self.server.connections:
            self.server.connections.remove(self.client)
            logging.debug('Connection close - No of connection:%s' % len(self.server.connections))
            for i in self.server.connections:
                if i != self.client:
                    i.send("\x00%s\xff" % 'client disconnect')

class EchoServer(asyncore.dispatcher):

    def __init__(self, host, port):
        asyncore.dispatcher.__init__(self)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.set_reuse_addr()
        self.bind((host, port))
        self.listen(5)
        self.connections = []
        self.host = host
        self.port = port

    def handle_accept(self):
        sock, addr = self.accept()
        logging.debug('Incoming connection from %s' % repr(addr))
        #print 'Incoming connection from %s' % repr(addr)
        self.connections.append(sock)
        handler = EchoHandler(sock)
        handler.set_server(self)
        handler.set_client(sock)

if __name__ == "__main__":
    logging.basicConfig(filename='websocket.log', level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
    HOST, PORT = "heroesofconquest.se", 8080

    # server = EchoServer(HOST, PORT)
    # asyncore.loop()

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

