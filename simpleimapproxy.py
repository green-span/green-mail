#|##############################################################################
#|Copyright (c) 2012, The Green-Span Project. All rights reserved. This code is
#|Open Source Free Software - redistribution and use in source and binary forms,
#|with or without modification, are permitted under the Two Clause BSD License.
#|##############################################################################
#|File Created: 2012-08-15
#|Author(s): Sean Hastings,
#|##############################################################################


from twisted.internet import ssl, reactor
from twisted.internet.protocol import ClientFactory, Factory, Protocol
from twisted.python import log


class SimpleImapProxy(Protocol):

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


class SimpleImapProxyClient(SimpleImapProxy):

    def connectionMade(self):
        self.peer.setPeer(self)
        # We're connected, everybody can read to their hearts content.
        self.peer.transport.resumeProducing()

    def dataReceived(self, data):
        print "C   P < S: %s" %data
        altered_data = self.alterImapServerMessage(data) 
        print "C < P   S: %s" %altered_data
        SimpleImapProxy.dataReceived(self, altered_data)
        
    def alterImapServerMessage(self, data):
        """Makes alterations to data stream from server to client"""
        
        #Do not tell mail client of IMAP compression capability
        altered_data = data.replace("COMPRESS=DEFLATE","NOTHING=TO=SEE=HERE")
        
        return altered_data


class SimpleImapProxyClientFactory(ClientFactory):

    protocol = SimpleImapProxyClient

    def setServer(self, server):
        self.server = server

    def buildProtocol(self, *args, **kw):
        prot = ClientFactory.buildProtocol(self, *args, **kw)
        prot.setPeer(self.server)
        return prot

    def clientConnectionFailed(self, connector, reason):
        self.server.transport.loseConnection()


class SimpleImapProxyServer(SimpleImapProxy):

    clientFactory = SimpleImapProxyClientFactory

    def connectionMade(self):
        # Don't read anything from the connecting client until we have
        # somewhere to send it to.
        self.transport.pauseProducing()

        client = self.clientFactory()
        client.setServer(self)

        reactor.connectSSL(self.factory.host, self.factory.port, client, ssl.ClientContextFactory())
        
    def dataReceived(self, data):
        print "C > S: %s" %data
        SimpleImapProxy.dataReceived(self, data)

    def dataReceived(self, data):
        print "C > P   S: %s" %data
        altered_data = self.alterImapClientMessage(data) 
        print "C   P > S: %s" %altered_data
        SimpleImapProxy.dataReceived(self, altered_data)
        
    def alterImapClientMessage(self, data):
        """Makes alterations to data stream from client to server"""
        
        altered_data = data
        
        return altered_data    

class SimpleImapProxyServerFactory(Factory):

    protocol = SimpleImapProxyServer

    def __init__(self, host, port):
        self.host = host
        self.port = port


factory = SimpleImapProxyServerFactory('imap.googlemail.com',993)
reactor.listenSSL(993, factory, ssl.DefaultOpenSSLContextFactory('ssl/server.key', 'ssl/server.crt'))
#SSL key and self signed cert generated following instructions at https://help.ubuntu.com/10.04/serverguide/certificates-and-security.html
print "Proxy Started"
reactor.run()
print "Proxy Stopped"