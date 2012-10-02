################################################
# 
# imapDeliveryAgent.py
# usage: imapDeliverAgent.py host port username
#
#
# written by morgan baron 9/2012 
# 
# 
#
###############################################

from twisted.internet import protocol, defer
from twisted.mail import imap4
from twisted.internet import reactor, ssl
import sys, getpass

MAILBOX = 'INBOX'
DEBUG = 1

class IMAPDeliveryAgentProtocol(imap4.IMAP4Client):


    def connectionMade(self):
        if DEBUG:
            print "connection made!"

    @defer.inlineCallbacks
    def serverGreeting(self, caps):
        if DEBUG:
            print "Greetings and Salutations!"        
 
        try:
            yield self.login(self.factory.username, self.factory.password)
            if DEBUG:
                print "Logged in!"
 
            result = yield self.select(self.factory.mailbox)
            if DEBUG:
                print "%s mailbox selected." % self.factory.mailbox
 
            dest =  "GS/CHAT/INBOX"
            yield self.copy(self.factory.uid, dest, 0)
            if DEBUG:
                print "Copied message to %s." % dest
 
            flags = ['\Deleted']
            yield self.setFlags(self.factory.uid, flags)
            if DEBUG:
                print "Set flag on message"

            print "Move messages complete!"
        
        except Exception as err:
            print err


#        self.close()
        reactor.stop()

class IMAPDeliveryAgentFactory(protocol.ClientFactory):
    protocol = IMAPDeliveryAgentProtocol

    if DEBUG:
        print "factory!"
    def __init__(self, username, password, uid, mailbox = 'inbox'):
        self.username = username
        self.password = password
        self.mailbox = MAILBOX
        self.deferred = defer.Deferred()
        self.mailbox = mailbox
        self.uid = uid

    def clientConnectionFailed(self, connector, reason):
        self.deferred.errback(reason)

if __name__ == "__main__":
    import sys, getpass
    if not len(sys.argv) == 5:
        print "Usage: connectiontest.py host port username uid"
        sys.exit(1)
        
    host = sys.argv[1]
    port = int(sys.argv[2])
    user = sys.argv[3]
    uid = sys.argv[4]
    password = getpass.getpass("Password: ")

    factory = IMAPDeliveryAgentFactory(user, password, uid)
    reactor.connectSSL(host, port, factory, ssl.ClientContextFactory())
    reactor.run()
