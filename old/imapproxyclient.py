
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

from twisted.internet import defer, protocol
from twisted.mail import imap4


class ImapProxyClient(object):        
    def __init__(self, uid, pwd,imap_server_address):
        if ALLVERBOSE or VERBOSE: print "ImapProxyClient.__init__('%s','%s','%s'" % (uid, pwd,imap_server_address)
        self.uid = uid
        self.pwd = pwd
        self.imap_server_address = imap_server_address
        self.mailboxCache = {} #dictionary of cached mailboxes keyed by path
        self.connectecd = False #indicates if connection is alive
        self.selected = None #path name of selected mailbox
        self.subscribed = [] #list of subscribeed mailbox pathname
        self.factory = None #protocol factory for server connection
        self.protocol = None #protocol for server connection
        

class ImapProxyClientProtocol(imap4.IMAP4Client):
    "Extension of Imap4Client class for debugging and customization"
    
    def lineReceived(self, line):
        if ALLVERBOSE or VERBOSE: print "C P<S:", line
        imap4.IMAP4Client.lineReceived(self,line)
        
    def sendLine(self,line):
        if ALLVERBOSE or VERBOSE: print "C P>S:", line
        imap4.IMAP4Client.sendLine(self,line)
    
    def serverGreeting(self, capabilities):
        "called when server connects"
        #Note - server capabilities are passed here but we are not doing anything witht hem yet
        if ALLVERBOSE or VERBOSE: print "ImapProxyClientProtocol.serverGreeting"
        login = self.login(self.factory.username, self.factory.password)
        login.addCallback(self.__loggedIN)
        login.chainDeferred(self.factory.deferred)
        
    def __loggedIN(self, results):
        "After initial login, returns reference to this protocol object for further server command execution"
        if ALLVERBOSE or VERBOSE: print "ImapProxyClientProtocol.__loggedIN"
        return self 
    
    def connectionLost(self, reason):
        "Called if connection is terminated"
        if ALLVERBOSE or VERBOSE: print"ImapProxyClientProtocol.connectionLost"
        if not self.factory.deferred.called:
            self.factory.deferred.errback(reason)
 
class ImapProxyClientProtocolFactory(protocol.ClientFactory):
    protocol = ImapProxyClientProtocol
    
    def __init__(self, username, password):
        if ALLVERBOSE or VERBOSE: print "ImapProxyClientProtocolFactory.__init__"
        self.username = username
        self.password = password
        self.deferred = defer.Deferred()
        
    def clientConnectionFailed(self, connection, reason):
        if ALLVERBOSE or VERBOSE: print "ImapProxyClientProtocolFactory.clientConnectionFailed"
        self.deferred.errback(reason)


        
     
        
