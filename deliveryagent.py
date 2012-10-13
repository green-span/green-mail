#|##############################################################################
#|Copyright (c) 2012, The Green-Span Project. All rights reserved. This code is
#|Open Source Free Software - redistribution and use in source and binary forms,
#|with or without modification, are permitted under the Two Clause BSD License.
#|##############################################################################
#|File Created: 2012-10-03
#|Author(s): Morgan Baron
#|##############################################################################

# TODO
# fix IDLE/DONE
# make idle client call delivery agent on new message arrival



from twisted.mail import imap4
from twisted.internet import reactor, protocol, defer, ssl
from getpass import getpass
import sys
import time
import re

DEBUG = 1
MAILBOX = 'INBOX'

class DeliveryAgentProtocol(imap4.IMAP4Client):

    def connectionMade(self):
        if DEBUG:
            print "connection made!"

    def connectionLost(self, reason):
        print "connection lost."

    @defer.inlineCallbacks
    def serverGreeting(self, caps):
        if DEBUG:
            print "Greetings and Salutations!"        
 
        try:
            yield self.login(self.factory.username, self.factory.password)
            if DEBUG:
                print "Logged in!"
 
            yield self.select(self.factory.mailbox)
            if DEBUG:
                print "%s mailbox selected." % self.factory.mailbox

            # search for message of green.mail.tester+blah@gmail.com
            qq = imap4.Query(all=1, to='+')
            messageUids = yield self.search(qq, uid=1)

            # if we found any
            if messageUids:
                ms = imap4.MessageSet()
                for uid in messageUids:
                    ms.add(uid)
            
                if DEBUG:
                    print messageUids

                # fetch To headers
                headerFields = ['To']
                to_headers = yield self.fetchSpecific(ms, uid=1, headerType='HEADER.FIELDS', headerNumber=None, headerArgs=headerFields)
                     
                for idx in to_headers:
                    uid =  to_headers[idx][0][1] 
                   
                    # strip whitespace
                    header = to_headers[idx][0][4].strip()
                    if DEBUG:
                        print "UID: %s To: %s" % (uid, header)
                
                    # get destination folder from email address
                    dest_regexp = re.search('\+(.+)@', header)
                    dest_folder = "+/" + dest_regexp.group(1).upper() + "/INBOX"
                    if DEBUG:
                        print dest_folder
                    flags = ['\Deleted']
                
                    # move message to desination folder
                    yield self.copy(uid, dest_folder, uid=1)
                    yield self.setFlags(uid, flags, silent=1, uid=1 )
            
                if DEBUG:
                    print "Copied message to %s." % dest_folder

            print "Move messages complete!"
        
        except Exception as err:
            print err

        self.close()
        self.transport.loseConnection()

class DeliveryAgentFactory(protocol.ClientFactory):
    protocol = DeliveryAgentProtocol

    def __init__(self, username, password, mailbox = 'INBOX'):
        if DEBUG:
            print "delivery agent factory!"

        self.username = username
        self.password = password
        self.deferred = defer.Deferred()
        self.mailbox = mailbox

    def clientConnectionFailed(self, connector, reason):
        self.deferred.errback(reason)

class IdleClientProtocol(imap4.IMAP4Client):
    """ idle client protocol connects to IMAP server, issues idle command,
    waits for incoming messages"""

    def idle(self):
        """Sends idle command to IMAP server 

        See RFC 2177 IMAP4 IDLE command

        @rtype: C{Deferred}
        @return: a deferred whose callback is invoked with the continuation
        response if the IDLE command was succesful and whose errback
        is invoked otherwise.
        """

        #d = self.sendLine('IDLE')
        #d.addCallback(self.__cbIdle)
        #return d
        self.sendLine('I001 IDLE')

    def __cbIdle(self, (lines, last)):
        """
        Handle response from IDLE command
        
        """
        
        print "We are idling!"

    def done(self):
        
        if DEBUG:
            print "Sending DONE!"
        self.sendLine('DONE')
        
    @defer.inlineCallbacks    
    def serverGreeting(self, caps):
        
        if DEBUG:
            print "Greeting!"

        try:            
            yield self.login(self.factory.username, self.factory.password)
            if DEBUG:
                print "Logged in!"

            result = yield self.select(self.factory.mailbox)
            self.num_messages = result['EXISTS']
            if DEBUG:
                print "%s contains %d messages" % (self.factory.mailbox, self.num_messages)
                
            if DEBUG:
                print "Sending IDLE command"
            self.idle()
            time.sleep(10)
            self.done()
            
        except Exception as err:
            print  err            
            reactor.stop()
         
    #@defer.inlineCallbacks    
    def newMessages(self, exists, recent):
        print "New Message!"
        try:
            runDeliveryAgent()
        except Exception as err:
            print err
            
class IdleClientFactory(protocol.ClientFactory):
    """ idle client protocol factory creates IMAPIdleClient protocols as needed,  
    handles persistent datax"""
    
    protocol = IdleClientProtocol

    def __init__(self,  username,  password,  mailbox = 'INBOX'):
        
        if DEBUG:
            print "idle client factory"

        self.username = username
        self.password = password
        self.mailbox = mailbox
        self.ms = imap4.MessageSet()
        self.deferred = defer.Deferred()

    def clientConnectionFailed(self, connector, reason):
        self.deferred.errback(reason)


def startIdler(host, port, factory):
    if DEBUG:
        print "starting reactor"
    reactor.connectSSL(host, port, factory, ssl.ClientContextFactory())
    reactor.run()

def runDeliveryAgent():
    print "Delivery agent goes here."

if __name__ == "__main__":
    if not len(sys.argv) == 4:
        print "Usage: connectiontest.py host port username"
        sys.exit(1)

    host = sys.argv[1]
    port = int(sys.argv[2])
    username = sys.argv[3]
    password = getpass("Password: ")

    #factory = IdleClientFactory(username, password)
    #startIdler(host, port, factory)

    factory = DeliveryAgentFactory(username, password)
    reactor.connectSSL(host, port, factory, ssl.ClientContextFactory())
    reactor.run()

