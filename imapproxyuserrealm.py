
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

from twisted.internet import defer, reactor, ssl
from twisted.mail import imap4
from twisted.cred import portal
from zope.interface import implements

from imapproxyaccount import ImapProxyAccount
from imapproxyclient import ImapProxyClientProtocolFactory
from imapproxyclient import ImapProxyClient

class ImapProxyUserRealm:
    implements(portal.IRealm)
    avatarInterfaces = {imap4.IAccount: ImapProxyAccount,}

    def __init__(self,proxy):
        if ALLVERBOSE or VERBOSE: print "ImapProxyUserRealm.__init__"
        #shared cache across multiple connections
        self.proxy = proxy
        pass
        
    def __getattribute__(self, name):
        if ALLVERBOSE or VERBOSE: print "ImapProxyUserRealm.__getattribute__(%s)" % name
        return object.__getattribute__(self, name)
    
    def requestAvatar(self, avatar_id, mind, *interfaces):
        if ALLVERBOSE or VERBOSE: print "ImapProxyUserRealm.requestAvatar"
        #Only one interface/class exists, but this is the way Twisted does this...
        for requestedInterface in interfaces:
            if self.avatarInterfaces.has_key(requestedInterface):
                #return account class from cache if exists or create new
                avatar_class = self.avatarInterfaces[requestedInterface]
                #set up new proxy
                account = avatar_class(avatar_id, self.proxy)
                #parse uid, @server, and pwd from passed avatarid in which this info was encoded 
                address, pwd = avatar_id.split(':')
                uid, imap_server_address = address.split('@')
                if ALLVERBOSE or VERBOSE: print uid, imap_server_address, pwd           
                #Set up account connection to server
                #Reuses existing connection or creates a new one and caches it for reuse
                if self.proxy.connected.has_key(avatar_id):
                    account.server = self.proxy.connected[avatar_id]
                else:
                    account.server = ImapProxyClient(uid,pwd,imap_server_address)
                    self.proxy.connected[avatar_id] = account.server
                    account.server.factory = ImapProxyClientProtocolFactory(uid, pwd)
                    account.server.factory.deferred.addCallback(account.firstConnect).addErrback(account.connectError)
                    reactor.connectSSL(imap_server_address, 993, account.server.factory, ssl.ClientContextFactory())
                #return account.factory.deferred
                return account.server.factory.deferred.addCallback(self.__requestedAvatar,requestedInterface, account, lambda: None) #lambda is used to create a null logout function

        #If no interface supported
        raise KeyError("None of the requested avatar interfaces is supported")
    
    def __requestedAvatar(self,results,requestedInterface, account, logout):
        "Returns interface information from requestID function, once defered server login has has completed"
        return (requestedInterface, account, logout)