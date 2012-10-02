###############################################
# 
# imapidleclient.py
# usage: imapidleclient.py host port username
#
#  author: morgan baron 9/2012 
#
#  description:
#   will notify when new messages arrive.
#   proof of conecpt, need lots of love
#
#  requires python version > 2.4 for inlinecallbacks
#
###############################################

from twisted.mail import imap4
from twisted.internet import reactor, protocol, defer, ssl
from getpass import getpass
import sys

DEBUG = 1


class IMAPIdleClientProtocol(imap4.IMAP4Client):
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

        cmd = 'IDLE'
        #resp = ('idling',)
        #d = self.sendCommand(imap4.Command(cmd, wantResponse=resp))
        d = self.sendCommand(imap4.Command(cmd))
        d.addCallback(self.__cbIdle)
        return d

    def __cbIdle(self, (lines, last)):
        """
        Handle response from IDLE command
        
        """
        
        print "We are idling!"

    @defer.inlineCallbacks    
    def serverGreeting(self, caps):
        
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
            yield self.idle()
        
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
            

        # check if recent message is blah+green.mail.....@
        # use greenmaildeliveryagent to move message to appropriate mailbox
          
class IMAPIdleClientFactory(protocol.ClientFactory):
    """ idle client protocol factory creates IMAPIdleClient protocols as needed,  
    handles persistent datax"""
    
    protocol = IMAPIdleClientProtocol

    def __init__(self,  username,  password,  mailbox = 'INBOX'):
        self.username = username
        self.password = password
        self.mailbox = mailbox
        self.ms = imap4.MessageSet()
        self.deferred = defer.Deferred()

    def clientConnectionFailed(self, connector, reason):
        self.deferred.errback(reason)

def startIdler(host, port, factory):
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

    factory = IMAPIdleClientFactory(username, password)
    startIdler(host, port, factory)
#reactor.connectSSL(host, port, factory, ssl.ClientContextFactory())
    #reactor.run()

def test():
    host = 'imap.googlemail.com'
    port = 993
    username = 'green.mail.tester'
    password = 'test.password'
    factory = IMAPIdleClientFactory(username, password)
    startIdler(host, port, factory)
