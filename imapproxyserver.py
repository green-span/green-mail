
#|##############################################################################
#|Copyright (c) 2009, The Green-Span Project. All rights reserved. This code is
#|Open Source Free Software - redistribution and use in source and binary forms,
#|with or without modification, are permitted under the Two Clause BSD License.
#|##############################################################################
#|File Created: 2009-04-01
#|Author(s): Sean Hastings,
#|##############################################################################

VERBOSE = True

from globals import ALLVERBOSE

"""
ImapProxyServer Object

Version 0.0.1
    Sets up framework for loging into proxy server
        spawns new CredentialsChecker
        spawns new protocol factory
        listens for connections

Version 0.0.0 - New File

"""

from twisted.internet import reactor, protocol
from twisted.cred import portal
from twisted.mail import imap4

from credentialschecker import CredentialsChecker
from imapproxyuserrealm import ImapProxyUserRealm

class ImapProxyServer(object):
    """Serves up protocol for incomming user imap-client connections"""

    def __init__(self,valid_logins):
        "gets valid email-addy:password combos from central object"
        #shared caching for connections to same IMAP account
        self.connected = {}
        #Start up server
        cred_check = CredentialsChecker(valid_logins)
        the_portal = portal.Portal(ImapProxyUserRealm(self))
        the_portal.registerChecker(cred_check)
        factory = ImapProxyServerProtocolFactory()
        factory.portal = the_portal
        reactor.listenTCP(143, factory) #TODO - convert to listenSSL
       
class ImapProxyServerProtocol(imap4.IMAP4Server):
    "Extension of Imap4Server class to expose functionality"
    
    def lineReceived(self, line):
        if ALLVERBOSE or VERBOSE: print "C>P S:", line
        imap4.IMAP4Server.lineReceived(self,line)
        
    def sendLine(self,line):
        if ALLVERBOSE or VERBOSE: print "C<P S", line
        imap4.IMAP4Server.sendLine(self,line)
        
    def connectionLost(self, reason):
        if ALLVERBOSE or VERBOSE: print "ImapProxyServerProtocol.connectionLost - %s", reason
        imap4.IMAP4Server.connectionLost(self,reason)
        
        
class ImapProxyServerProtocolFactory(protocol.Factory):
    protocol = ImapProxyServerProtocol
    portal = None
    
    def buildProtocol(self, address):
        p = self.protocol()
        p.portal = self.portal
        p.factory = self
        return p


 