###############################################
# 
# imapidleclient.py
# usage: imapidleclient.py host port username
#
# author: morgan baron 9/2012 
#
#  description:
#   will notify when new messages arrive.
#   proof of conecpt, need lots of love
#
###############################################

from twisted.mail import imap4 
from twisted.internet import reactor, protocol, defer, ssl
from getpass import getpass
import sys

def GetMailboxConnection(username, password, host, port, mailbox="inbox"):
    
    f = protocol.ClientFactory()
    f.username = username
    f.password = password
    f.mailbox = mailbox
    
    class ConnectMailbox(imap4.IMAP4Client):
        @defer.inlineCallbacks
    
        def serverGreeting(self, caps):
        
            try:            
                yield self.login(self.factory.username, self.factory.password)
                print "Logged in!"
            except Exception as err:
                print "Error", err
                return

            try:
                result = yield self.select(self.factory.mailbox)
                self.num_messages = result['EXISTS']
                print "%s contains %d messages" % (self.factory.mailbox, self.num_messages)
            except Exception as err:
                print "Error suscribing to %s" % self.factory.mailbox, err
                return
            finally:
                self.sendLine("SILLYTAG IDLE")
                print "Sending IDLE command"
        
            self.factory.deferred.callback(self)
        
        def newMessages(self, exists, recent):
            
            print "New Message!"
         
    f.protocol = ConnectMailbox
    reactor.connectSSL(host, port, f, ssl.ClientContextFactory())

    f.deferred = defer.Deferred()
    return f.deferred

#@defer.inlineCallbacks    
def readyToGo(conn):
    print "I'm not finished... hint hint"
              
if __name__ == "__main__":
    if not len(sys.argv) == 4:
        print "Usage: connectiontest.py host port username"
        sys.exit(1)

    host = sys.argv[1]
    port = int(sys.argv[2])
    username = sys.argv[3]
    password = getpass("Password: ")
   
    GetMailboxConnection(username, password, host, port, "INBOX") .addCallback(
        readyToGo)

    reactor.run()
