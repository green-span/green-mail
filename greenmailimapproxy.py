#|##############################################################################
#|Copyright (c) 2012, The Green-Span Project. All rights reserved. This code is
#|Open Source Free Software - redistribution and use in source and binary forms,
#|with or without modification, are permitted under the Two Clause BSD License.
#|##############################################################################
#|File Created: 2012-08-15
#|Author(s): Sean Hastings,
#|##############################################################################

VERBOSE = True

from twisted.internet import ssl, reactor
from twisted.internet.protocol import ClientFactory, Factory, Protocol
from twisted.python import log
import string, re

HOST_NAME = 'imap.googlemail.com'
MASKED_CAPABILITIES_LIST = ['XLIST','COMPRESS=DEFLATE']
CAPABILITY_MASK = "NOTHING=TO=SEE=HERE"
ROOT = ""
GS = "GS"
APP = "MAIL"
SEP = "/"
CLIENT_COMMANDS = ['LOGIN','SELECT','SUBSCRIBE','EXAMINE','CREATE','DELETE','RENAME','LIST','LSUB','STATUS','COPY','GETQUOTAROOT','APPEND']

def trimContainer(a_string):
    """Removes quotes,braces,parens, or brackets from both sides of a string"""
    if (["(","'",'"',"{","["].count(a_string[:1])):
        return a_string[1:-1]
    return a_string

class GreenMailImapProxy(Protocol):

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

class GreenMailImapProxyClient(GreenMailImapProxy):

    def __init__(self):
        self.fragment = ""

    def connectionMade(self):
        """Establishes internal proxy connection and start data flow once remote server connects"""
        self.peer.setPeer(self)
        self.peer.transport.resumeProducing()

    def dataReceived(self, data):
        if VERBOSE: print "C   P < S: %s" % data
        altered_data = self.handleData(data)
        if altered_data:
            if VERBOSE: print "C < P   S: %s" % altered_data
            GreenMailImapProxy.dataReceived(self, altered_data)
        
    def parseDataLine(self, line):
        """Parse and sometimes alter each line of data"""
        #Check for end of any commands or for a FETCH still in progress
        command = self.peer.command
        if command:
            length = len(self.peer.command[0])+len(self.peer.command[1]) + 4
            if command and line[:length].upper() == (self.peer.command[0] + " OK " + self.peer.command[1]):
                command == None
            elif command and line[:length].upper() == (self.peer.command[0] + " NO " + self.peer.command[1]):
                    command == None
            elif command and line[:length + 1].upper() == (self.peer.command[0] + " BAD " + self.peer.command[1]):
                command == None
            elif command[1] == "FETCH": return line #skip parse of lines durring FETCH Command
        #Parse commands and greenwash accordingly
        altered_line = line
        prefix = self.peer.root + self.peer.gs + self.peer.sep + self.peer.app + self.peer.sep 
        #NAMESPACE - Get BOX ROOT and SEP from return
        #S: * NAMESPACE (("" "/")) NIL NIL
        if line[:11].lower() == "* namespace":
            self.parseRootAndSep(line)
        #CAPABILITY - Mask those in our unwanted list
        elif line[:12].lower() == "* capability":
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
            match_string = match.group()
            self.peer.sep = match_string[-3:-2] #Set server box seperator character
            box_name = trimContainer(string.replace(line,match.group(),""))
        return box_name
    
    def parseRootAndSep(self, line):
        """Gets ROOT level and hierarchy seperator from NAMESPACE command"""
        #S: * NAMESPACE (("" "/")) NIL NIL
        match = re.search(r'\(\(.*\)\)',line)
        if match:
            namespace = match.group()[2:-2]
            split = string.split(namespace,'" "',1)
            self.peer.root = split[0][1:]
            self.peer.sep = split[1][:-1]
            #add seperator to end if root is not ""
            if self.peer.root: self.peer.root += self.peer.sep 
        return

class GreenMailImapProxyClientFactory(ClientFactory):

    protocol = GreenMailImapProxyClient

    def setServer(self, server):
        self.server = server

    def buildProtocol(self, *args, **kw):
        new_protocol = ClientFactory.buildProtocol(self, *args, **kw)
        new_protocol.setPeer(self.server)
        return new_protocol

    def clientConnectionFailed(self, connector, reason):
        self.server.transport.loseConnection()


class GreenMailImapProxyServer(GreenMailImapProxy):

    clientFactory = GreenMailImapProxyClientFactory
    
    def __init__(self):
        self.fragment = ""
        self.command = None
        self.authenticated = False
        self.root = ROOT
        self.gs = GS
        self.app = APP
        self.sep = SEP

    def connectionMade(self):
        """Pauses data flow until remote server connects, sets up for future data flow"""
        self.transport.pauseProducing()
        client = self.clientFactory()
        client.setServer(self)
        reactor.connectSSL(self.factory.host, self.factory.port, client, ssl.ClientContextFactory())

    def dataReceived(self, data):
        """Overide for handling data sent from client"""
        if VERBOSE: print "C > P   S: %s" % data
        altered_data = self.handleData(data) 
        if altered_data:
            if VERBOSE: print "C   P > S: %s" %  altered_data
            GreenMailImapProxy.dataReceived(self, altered_data)        
    
    def parseDataLine(self, line):
        """Parse and sometimes alter each line of data"""
        #skip parse durring APPEND command
        if self.command and self.command[1] == "APPEND": return line
        #Parse line and green wash accordingly
        altered_line = line
        line_parts = line.split(' ')
        prefix = self.root +self.gs + self.sep + self.app
        #identify command
        command = None
        if len(line_parts) > 1 and CLIENT_COMMANDS.count(line_parts[1].upper()):
            command = line_parts[1].upper()
            self.command = [line_parts[0].upper(), command] #record command number and command
        #Commands needing greenwash of first argument
        #C: A142 SELECT INBOX
        #C: A932 EXAMINE INBOX
        #C: A004 CREATE INBOX/SUBBOX
        #C: A683 DELETE INBOX
        #C: A042 STATUS INBOX (UIDNEXT MESSAGES)
        #C: A003 GETQUOTAROOT INBOX
        #C: A003 APPEND INBOX (\Seen) {310}
        #C: A683 RENAME INBOX/SUBBOX INBOX/SPECIAL
        if ['SELECT','SUBSCRIBE','EXAMINE','CREATE','DELETE','STATUS','GETQUOTAROOT','APPEND','RENAME'].count(command):
            box_name = trimContainer(line_parts[2])
            altered_line = altered_line.replace(box_name,prefix + self.sep + box_name,1)
        #Commands needing greenwash of second argument (Note "RENAM" does both first and second)
        if ['COPY','RENAME'].count(command):
            box_name = trimContainer(line_parts[3])
            altered_line = altered_line.replace(box_name,prefix + self.sep + mailbox_name,1)
        #LIST and LSUB also have a context parameter that should be greenwashed
        #but this must be handles a little differently than above, as it is often blank
        if ['LIST','LSUB'].count(command):
            context = trimContainer(line_parts[2])
            if context:
                altered_line = altered_line.replace(box_name,prefix + self.sep + box_name,1)
            else: #blank context
                quotes = line_parts[2]
                altered_line = altered_line.replace(quotes,quotes[:1] + prefix + quotes[-1:],1)
        #LOGIN get APP info and remove it from login string for pass to server
        #C: a001 LOGIN "whysean+voip@gmail.com" "Sean'sBestPassword"
        if command == "LOGIN":
            match = re.search(r'\+.*@',line)
            if match:
                self.app = match.group()[1:-1].upper()
                altered_line = altered_line.replace(match.group()[:-1],"",1)
        #Return possibly altered client data line
        return altered_line


class GreenMailImapProxyServerFactory(Factory):

    protocol = GreenMailImapProxyServer

    def __init__(self, host, port):
        self.host = host
        self.port = port

#Execute from shell
if __name__ == "__main__":
    factory = GreenMailImapProxyServerFactory(HOST_NAME,993)
    reactor.listenSSL(993, factory, ssl.DefaultOpenSSLContextFactory('ssl/server.key', 'ssl/server.crt'))
    #SSL key and self signed cert generated following instructions at https://help.ubuntu.com/10.04/serverguide/certificates-and-security.html
    print "Proxy Started"
    reactor.run()
    print "Proxy Stopped"
