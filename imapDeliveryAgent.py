################################################
# 
# imapDeliveryAgent.py
# usage: imapDeliverAgent.py host port username
#
#
# written by Morgan Baron 9/2012 
#
#
# TODO:
#  Fail gracefully for authentication failure
#  Base destination mailbox on +string
#  Hooks for Green-Light authentication
#
###############################################



from twisted.internet import protocol, defer
from twisted.mail import imap4
from twisted.internet import reactor, ssl
import sys, getpass

MAILBOX = 'INBOX'
DEBUG = 0

class IMAPDeliveryAgentProtocol(imap4.IMAP4Client):

    def serverGreeting(self, caps):
        if DEBUG:
            print "Greetings and Salutations!"        
 
        d_login = self.login(self.factory.username, self.factory.password)
        d_login.addCallback(self.__loggedIn)        
        d_login.chainDeferred(self.factory.deferred)
        
    def connectionMade(self):
        if DEBUG:
            print "connection made!"
        
    def __loggedIn(self, results):
        if DEBUG:
            print"We are logged in!"
        return self.select(self.factory.mailbox).addCallback(self.__selectedMailbox)

    def __selectedMailbox(self, result):
        num_messages = result['EXISTS'] 
        if DEBUG:
            print "There are %d messages in %s" % (num_messages, MAILBOX)
        return self.search(self.factory.qq, uid=0).addCallback(self.__MoveMessageToGS)

    def __MoveMessageToGS(self, result):
        if result:
            for message in result:
                self.factory.ms.add(message)
            print "Moving messages %s to GS folder" % self.factory.ms
            return self.copy(self.factory.ms, "GS/CHAT/INBOX", 0).addCallback(self.__CopyMessageResult)
        else:
            print "No messages match Query %s" % str(self.factory.qq)
            reactor.stop()

    def __CopyMessageResult(self, result):
        if DEBUG:
            print "Messages coppied to destination!"
        flags = ['\Deleted']
        return self.setFlags(self.factory.ms, flags).addCallback(self.__MoveMessageResult)
        
    def __MoveMessageResult(self, result):
        if DEBUG:
            print "Message removed from source!"
        
        print "Move messages complete!"
        self.close()
        reactor.stop()

    def connectionLost(self, reason):
        if not self.factory.deferred.called:
            self.factory.deferred.errback(reason)

class IMAPDeliveryAgentFactory(protocol.ClientFactory):
    protocol = IMAPDeliveryAgentProtocol

    if DEBUG:
        print "factory!"
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.mailbox = MAILBOX
        self.deferred = defer.Deferred()
        self.qq = imap4.Query(all=1, to="+chat@gmail.com")
        self.ms = imap4.MessageSet()
        
    def clientConnectionFailed(self, connector, reason):
        self.deferred.errback(reason)

if __name__ == "__main__":
    import sys, getpass
    if not len(sys.argv) == 4:
        print "Usage: connectiontest.py host port username"
        sys.exit(1)
        
    host = sys.argv[1]
    port = int(sys.argv[2])
    user = sys.argv[2]
    password = getpass.getpass("Password: ")

    factory = IMAPDeliveryAgentFactory(user, password)
    reactor.connectSSL(host, port, factory, ssl.ClientContextFactory())
    reactor.run()
