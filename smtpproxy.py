#|##############################################################################
#|Copyright (c) 2012, The Green-Span Project. All rights reserved. This code is
#|Open Source Free Software - redistribution and use in source and binary forms,
#|with or without modification, are permitted under the Two Clause BSD License.
#|##############################################################################
#|File Created: 2012-08-15
#|Author(s): Sean Hastings,
#|##############################################################################

VERBOSE = True
DEBUG = True

from twisted.internet import ssl, reactor
from twisted.internet.protocol import ClientFactory, Factory, Protocol
from twisted.python import log
import string, re

HOST_NAME = 'smtp.googlemail.com' #Assumed hostname (later versions will discover from login or have on file)

#Client Commands that the proxy needs to know about
CLIENT_COMMANDS = ['APPEND','CAPABILITY','CHECK','COPY','CREATE','DELETE','EXAMINE','FETCH','GETQUOTAROOT','ID','IDLE','LIST','LOGIN','LSUB','NAMESPACE','NOOP','RENAME','SELECT','STATUS','SUBSCRIBE','UID','UNSUBSCRIBE']

#Commands that need their parameters changed in passing through the proxy
CHANGE_FIRST_PARAM = ['APPEND','CREATE','DELETE','EXAMINE','GETQUOTAROOT','RENAME','SELECT','STATUS','SUBSCRIBE','UNSUBSCRIBE']
CHANGE_SECOND_PARAM = ['COPY','RENAME','LIST','LSUB']
#LIST and LSUB also have a first "context" parameter that maybe should be greenwashed
#but it is often blank and seems to have different meanings based on second parameter
#this is something to look at again later...


class GreenMailSmtpProxy(Protocol):

    noisy = True
    peer = None

    def setPeer(self, peer):
        self.peer = peer

    def connectionLost(self, reason):
        if self.peer is not None:
            self.peer.transport.loseConnection()
            self.peer = None
        elif self.noisy:
            log.msg("Unable to connect to peer: %s" % (reason,))

    def dataReceived(self, data):
        self.peer.transport.write(data)

    def handleData(self, data):
        """Builds data lines for parsing"""
        altered_data = ""
        #process raw data into lines for processing
        lines = data.split('\n')
        #add any previous line fragment to begining of first line
        lines[0] = self.fragment + lines[0]
        #remove and store any final fragement for use in later complete line
        self.fragment = string.join(lines[-1:])
        lines = lines[:-1]
        #parse/alter each full line
        for line in lines:
            altered_line = self.parseDataLine(line)
            if altered_line:
                altered_data += altered_line  + "\n"
        #send altered data on to Server
        return altered_data

    def parseDataLine(self, line):
        """Override to Parse and sometimes alter each line of data"""
        altered_line = line
        return altered_line   

class GreenMailSmtpProxyClient(GreenMailSmtpProxy):
    """This half of the proxy recieves data from an IMAP server and sometimes alters it
    before passing it along to the real connected client."""

    def __init__(self):
        self.fragment = ""

    def connectionMade(self):
        """Establishes internal proxy connection and start data flow once remote server connects"""
        self.peer.setPeer(self)
        self.peer.transport.resumeProducing()

    def dataReceived(self, data):
        if VERBOSE: print "C   P < S: %s" % data
        altered_data = self.handleData(data)
        if altered_data:
            if VERBOSE: print "C < P   S: %s" % altered_data
            GreenMailSmtpProxy.dataReceived(self, altered_data)
        
    def parseDataLine(self, line):
        """Parse and sometimes alter each line of data"""
        altered_line = line
        #Return altered
        return altered_line   
          
class GreenMailSmtpProxyClientFactory(ClientFactory):

    protocol = GreenMailSmtpProxyClient

    def setServer(self, server):
        self.server = server

    def buildProtocol(self, *args, **kw):
        new_protocol = ClientFactory.buildProtocol(self, *args, **kw)
        new_protocol.setPeer(self.server)
        return new_protocol

    def clientConnectionFailed(self, connector, reason):
        self.server.transport.loseConnection()


class GreenMailSmtpProxyServer(GreenMailSmtpProxy):
    """This half of the proxy recieves data from a client and sometimes alters it
        before passing it along to the real connected server."""    

    clientFactory = GreenMailSmtpProxyClientFactory
    
    def __init__(self):
        self.fragment = ""
        self.sending = False
        self.recipients = []

    def connectionMade(self):
        """Pauses data flow until remote server connects, sets up for future data flow"""
        self.transport.pauseProducing()
        client = self.clientFactory()
        client.setServer(self)
        reactor.connectSSL(self.factory.host, self.factory.port, client, ssl.ClientContextFactory())

    def dataReceived(self, data):
        """Overide for handling data sent from client"""
        if VERBOSE: print "C > P   S: %s" % data
        altered_data = self.handleData(data) 
        if altered_data:
            if VERBOSE: print "C   P > S: %s" %  altered_data
            GreenMailSmtpProxy.dataReceived(self, altered_data)        
    
    def parseDataLine(self, line):
        """Parse and sometimes alter each line of data"""
        altered_line = line
        if len(line) >= 4 and line[:4].upper() == "DATA":
            self.sending = True
            if DEBUG: print "PROXY INTERNAL: <RECIPIENTS=%s>"%self.recipients
        elif self.stripReturn(line) == ".":
            self.sending = False
        if not self.sending:
            if len(line) >= 8 and line[:8].upper() == "RCPT TO:":
                self.recipients.append(self.stripReturn(line[8:]))
        return altered_line
    
    def stripReturn(self,line):
        """Strip \r character if it exists at end of line"""
        if line[-1:] == "\r":
            return line[:-1]
        return line

class GreenMailSmtpProxyServerFactory(Factory):

    protocol = GreenMailSmtpProxyServer

    def __init__(self, host, port):
        self.host = host
        self.port = port

#Execute from shell
if __name__ == "__main__":
    factory = GreenMailSmtpProxyServerFactory(HOST_NAME,465)
    reactor.listenSSL(465, factory, ssl.DefaultOpenSSLContextFactory('ssl/server.key', 'ssl/server.crt'))
    #SSL key and self signed cert generated following instructions at https://help.ubuntu.com/10.04/serverguide/certificates-and-security.html
    print "Proxy Started"
    reactor.run()
    print "Proxy Stopped"
