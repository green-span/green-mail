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
import string, re

HOST_NAME = 'imap.googlemail.com'
MASKED_CAPABILITIES_LIST = ['XLIST','COMPRESS=DEFLATE']
CAPABILITY_MASK = "NOTHING=TO=SEE=HERE"
ROOT_BOX = 'GS'
BOX_SEP = "/"
APP_BOX = "MAIL"
CLIENT_COMMANDS = ['SELECT','SUBSCRIBE','EXAMINE','CREATE','DELETE','RENAME','LIST','LSUB','STATUS','COPY','GETQUOTAROOT','APPEND']

def trimContainer(a_string):
    if (["(","'",'"'].count(a_string[:1])):
        return a_string[1:-1]
    return a_string

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

class SimpleImapProxyClient(SimpleImapProxy):

    def __init__(self):
        self.fragment = ""

    def connectionMade(self):
        """Establishes internal proxy connection and start data flow once remote server connects"""
        self.peer.setPeer(self)
        self.peer.transport.resumeProducing()

    def dataReceived(self, data):
        print "C   P < S: %s" % data
        altered_data = self.handleData(data) 
        print "C < P   S: %s" % altered_data
        SimpleImapProxy.dataReceived(self, altered_data)
        
    def parseDataLine(self, line):
        """Parse and sometimes alter each line of data"""
        altered_line = line
        prefix = ROOT_BOX + BOX_SEP + APP_BOX + BOX_SEP 
        #NAMESPACE - Assuming Gmail known for now (must re-address this when we handle login properly)
        #CAPABILITY - Mask those in our unwanted list
        if line[:12].lower() == "* capability":
            for capability in MASKED_CAPABILITIES_LIST:
                altered_line = re.sub("(?i)%s"%capability, CAPABILITY_MASK, altered_line)
        #LIST and LSUB
        elif ["* lsub", "* list"].count(line[:6].lower()): #if list or lsub return data
            #get box name and sep
            box_name = self.getBoxNameFromList(line)
            #if box is above our view - kill line
            if box_name[:len(prefix)] != prefix:
                altered_line = ""
            else:
                new_name = box_name.replace(prefix,"",1)
                altered_line = line.replace(box_name,new_name)
        #QUOTAROOT and STATUS Responses
        elif ["* quotar", "* status"].count(line[:8].lower()):
            altered_line = line.replace(prefix,"")
        #SELECT
        #S: A812 OK [READ-WRITE] GS/MAIL/INBOX selected. (Success)
        #Should have a FETCH mode that ignores parsing
        #Return altered
        return altered_line   
        
    def getBoxNameFromList(self, line):
        """Parses mailbox name from line returned by LIST or LSUB commands"""
        box_name = None
        #Isolate mail box name part of return line by regular expression pattern match
        match = re.search(r'\* \w\w\w\w \(.*\) "." ',line)
        if match:
            box_name = trimContainer(string.replace(line,match.group(),""))
        return box_name
    
class SimpleImapProxyClientFactory(ClientFactory):

    protocol = SimpleImapProxyClient

    def setServer(self, server):
        self.server = server

    def buildProtocol(self, *args, **kw):
        new_protocol = ClientFactory.buildProtocol(self, *args, **kw)
        new_protocol.setPeer(self.server)
        return new_protocol

    def clientConnectionFailed(self, connector, reason):
        self.server.transport.loseConnection()


class SimpleImapProxyServer(SimpleImapProxy):

    clientFactory = SimpleImapProxyClientFactory
    
    def __init__(self):
        self.fragment = ""
        self.commands = {}
        self.imap_hierarchy_delimeter = "/"
        self.imap_name_prefix = ""

    def connectionMade(self):
        """Pauses data flow until remote server connects, sets up for future data flow"""
        self.transport.pauseProducing()
        client = self.clientFactory()
        client.setServer(self)
        reactor.connectSSL(self.factory.host, self.factory.port, client, ssl.ClientContextFactory())

    def dataReceived(self, data):
        print "C > P   S: %s" % data
        altered_data = self.handleData(data) 
        if altered_data:
            print "C   P > S: %s" %  altered_data
            SimpleImapProxy.dataReceived(self, altered_data)        
    
    def parseDataLine(self, line):
        """Parse and sometimes alter each line of data"""
        altered_line = line
        prefix = ROOT_BOX + BOX_SEP + APP_BOX
        command = self.parseClientCommand(line)
        #greenwash first argument
        #C: A142 SELECT INBOX
        #C: A932 EXAMINE INBOX
        #C: A004 CREATE INBOX/SUBBOX
        #C: A683 DELETE INBOX
        #C: A042 STATUS INBOX (UIDNEXT MESSAGES)
        #C: A003 GETQUOTAROOT INBOX
        #C: A003 APPEND INBOX (\Seen) {310}
        #C: A683 RENAME INBOX/SUBBOX INBOX/SPECIAL
        if ['SELECT','SUBSCRIBE','EXAMINE','CREATE','DELETE','STATUS','GETQUOTAROOT','APPEND','RENAME'].count(command):
            box_name = trimContainer(line.split(' ')[2])
            altered_line = altered_line.replace(box_name,prefix + BOX_SEP + box_name,1)
        #Greenwash second argument
        #C: A003 COPY 2:4 INBOX
        #C: A683 RENAME INBOX/SUBBOX INBOX/SPECIAL
        if ['COPY','RENAME'].count(command):
            box_name = trimContainer(line.split(' ')[3])
            altered_line = altered_line.replace(box_name,prefix + BOX_SEP + mailbox_name,1)
        #LIST and LSUB have a context parameter that should be greenwashed
        #but this must be handles a little differently than above, as it may be blank
        if ['LIST','LSUB'].count(command):
            context = trimContainer(line.split(' ')[2])
            if context:
                altered_line = altered_line.replace(box_name,prefix + BOX_SEP + box_name,1)
            else: #blank context
                quotes = line.split(' ')[2]
                altered_line = altered_line.replace(quotes,quotes[:1] + prefix + quotes[-1:],1)
        #APPEND command needs to set ignore message lines state               
        return altered_line   

    def parseClientCommand(self,line):
        """Checks if line is a known client command"""
        line_parts = line.split(' ')
        if len(line_parts) > 1:
            maybe_command = line_parts[1].upper()
            if CLIENT_COMMANDS.count(maybe_command):
                return maybe_command
        return None
    

class SimpleImapProxyServerFactory(Factory):

    protocol = SimpleImapProxyServer

    def __init__(self, host, port):
        self.host = host
        self.port = port

factory = SimpleImapProxyServerFactory(HOST_NAME,993)
reactor.listenSSL(993, factory, ssl.DefaultOpenSSLContextFactory('ssl/server.key', 'ssl/server.crt'))
#SSL key and self signed cert generated following instructions at https://help.ubuntu.com/10.04/serverguide/certificates-and-security.html
print "Proxy Started"
reactor.run()
print "Proxy Stopped"