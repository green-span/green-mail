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

#Default connection parameters
HOST = 'imap.googlemail.com'
PORT = 993

#Default IMAP folder structure
ROOT = "" #Assumed root of user mailboxes until otherwise discovered
SEP = "/" #Assumed mailbox name seperator until otherwise discovered
GS = "+" #Top level box name
APP = "MAIL" #Default App if none specified

#Hacks that fix problem of client(s) (Thunderbird) assuming knowledge of Gmail imap folders
FROM_CLIENT_REPLACE_SPECIAL = [("[Gmail]^^",""),("[Gmail]^",""),("[Gmail]","")]
FROM_SERVER_REPLACE_SPECIAL = [("NO [ALREADYEXISTS]","OK [ALREADYEXISTS]"),]

#Capabilities not currently supported will be replaced with MASK
MASKED_CAPABILITIES_LIST = ['XLIST','COMPRESS=DEFLATE']
MASK = "NOTHING=TO=SEE=HERE"

#Sensitive data (like user password) will be masked in _VERBOSE printout
PASS_MASK = "XXXXXXXX"

#Client Commands that the proxy needs to know about
CLIENT_COMMANDS = ['APPEND','CAPABILITY','CHECK','COPY','CREATE','DELETE','EXAMINE','FETCH','GETQUOTAROOT','ID','IDLE','LIST','LOGIN','LSUB','NAMESPACE','NOOP','RENAME','SELECT','STATUS','SUBSCRIBE','UID','UNSUBSCRIBE']

#Commands that need their parameters changed in passing through the proxy
CHANGE_FIRST_PARAM = ['APPEND','CREATE','DELETE','EXAMINE','GETQUOTAROOT','RENAME','SELECT','STATUS','SUBSCRIBE','UNSUBSCRIBE']
CHANGE_SECOND_PARAM = ['COPY','RENAME','LIST','LSUB']
#LIST and LSUB also have a first "context" parameter that maybe should be greenwashed
#but it is often blank and seems to have different meanings based on second parameter
#this is something to look at again later...

#Command tag suffix used when slipping in an extra command from client
SNEAK_COMMAND_TAG_SUFFIX = "A"

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
    """This half of the proxy recieves data from an IMAP server and sometimes alters it
    before passing it along to the real connected client."""

    def __init__(self):
        self.fragment = ""
        self.logged_in = False

    def connectionMade(self):
        """Establishes internal proxy connection and start data flow once remote server connects"""
        self.peer.setPeer(self)
        self.peer.transport.resumeProducing()

    def dataReceived(self, data):
        if _VERBOSE: print "C   P < S: %s" % data
        altered_data = self.handleData(data)
        if altered_data:
            if _VERBOSE: print "C < P   S: %s" % altered_data
            GreenMailImapProxy.dataReceived(self, altered_data)
        
    def parseDataLine(self, line):
        """Parse and sometimes alter each line of data"""
        #Check for end of any commands in progress or for an ongoing FETCH to ignore message data
        command = self.peer.command
        if command:
            length = len(self.peer.command[0])
            if line[:length + 3].upper() == (self.peer.command[0] + " OK"):
                #Record successful login state
                if command[1] == "LOGIN" : self.logged_in = True
                command == None
            elif line[:length + 3].upper() == (self.peer.command[0] + " NO"):
                command == None
            elif line[:length + 4].upper() == (self.peer.command[0] + " BAD"):
                command == None
            elif command[1] == "FETCH": return line #skips parsing of FETCH message lines
        #Hide real server return data from inserted commands unknown to real client
        sneak_tag = self.peer.sneak_command_tag
        if sneak_tag:
            length = len(sneak_tag)
            if line[:length + 1] == (sneak_tag + " "):
                return ""
        #Parse commands and greenwash accordingly
        altered_line = self._specialReplace(line)
        prefix = self.peer.root + self.peer.gs + self.peer.sep + self.peer.app + self.peer.sep 
        #NAMESPACE - Get ROOT and SEP from return
        if line[:11].lower() == "* namespace":
            self.parseRootAndSep(line)
        #CAPABILITY - Mask capabilities we do not want to support (at least for now)
        elif line[:12].lower() == "* capability":
            for capability in MASKED_CAPABILITIES_LIST:
                altered_line = re.sub("(?i)%s"%capability, MASK, altered_line)
        #LIST and LSUB - change response box name's
        elif ["* lsub", "* list"].count(line[:6].lower()): #if list or lsub return data
            #get box name and sep
            box_name = self.getBoxNameFromList(line)
            if box_name[:len(prefix)] != prefix:
                altered_line = ""
            else:
                new_name = box_name.replace(prefix,"",1)
                altered_line = line.replace(box_name,new_name)
        #QUOTAROOT and STATUS  - change response box name's
        elif ["* quotar", "* status"].count(line[:8].lower()):
            altered_line = line.replace(prefix,"")
        #Return altered data line
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
    
    def _specialReplace(self,line):
        """Rewrite on specific server responses"""
        new_line = line
        for item in FROM_SERVER_REPLACE_SPECIAL: #each item a tupple of form (SEARCH_STRING,REPLACE_STRING)
            new_line = new_line.replace(item[0],item[1])
        return new_line

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
    """This half of the proxy recieves data from an IMAP client and sometimes alters it
        before passing it along to the real connected server."""    

    clientFactory = GreenMailImapProxyClientFactory
    
    def __init__(self):
        self.fragment = ""
        self.command = None
        self.authenticated = False
        self.root = ROOT
        self.gs = GS
        self.app = APP
        self.sep = SEP
        self.sneak_command_tag = None
        self.inbox_created = False

    def connectionMade(self):
        """Pauses data flow until remote server connects, sets up for future data flow"""
        self.transport.pauseProducing()
        client = self.clientFactory()
        client.setServer(self)
        reactor.connectSSL(self.factory.host, self.factory.port, client, ssl.ClientContextFactory())

    def dataReceived(self, data):
        """Overide for handling data sent from client"""
        altered_data = self.handleData(data) 
        if _VERBOSE: print "C > P   S: %s" % self.hideSensitive(data)
        if altered_data:
            if _VERBOSE: print "C   P > S: %s" %  self.hideSensitive(altered_data)
            GreenMailImapProxy.dataReceived(self, altered_data)
            
    def hideSensitive(self, data):
        """Replaces user password data and such with PASS_MASK"""
        if self.command and self.command[1] == "LOGIN":
            return re.sub('"\S*"','"' + PASS_MASK[::-1] + '"',data[::-1],1)[::-1]
        return data
            
    
    def parseDataLine(self, line):
        """Parse and sometimes alter each line of data"""
        #skip parse of message lines durring APPEND command
        if self.command and self.command[1].upper() == "APPEND": return line
        #Parse line and green wash accordingly
        altered_line = self._specialReplace(line)
        line_parts = self._specialSplit(altered_line)
        prefix = self.root +self.gs + self.sep + self.app
        #identify command
        command = None
        if len(line_parts) > 1 and CLIENT_COMMANDS.count(line_parts[1].upper()):
            command = line_parts[1].upper()
            #Swap UID command for sub-command
            if command == "UID": command = line_parts[2].upper()            
            self.command = [line_parts[0].upper(), command] #record command number and command
        #Commands needing greenwash of first argument
        if CHANGE_FIRST_PARAM.count(command):
            box_name = trimContainer(line_parts[2])
            altered_line = altered_line.replace(box_name,prefix + self.sep + box_name,1)
        #Commands needing greenwash of second argument (Note "RENAME" does both first and second parameters)
        if CHANGE_SECOND_PARAM.count(command):
            box_name = trimContainer(line_parts[3])
            altered_line = altered_line.replace(box_name,prefix + self.sep + box_name,1)
        #LOGIN get APP info, remove it from login string sent to real server
        if command == "LOGIN":
            match = re.search(r'\+.*@',line)
            if match:
                self.app = match.group()[1:-1].upper()
                altered_line = altered_line.replace(match.group()[:-1],"",1)
        #Sneak in command to try to create INBOX for app once logged in
        if command and self.peer.logged_in and not self.inbox_created:
            self.sneak_command_tag = line_parts[0] + SNEAK_COMMAND_TAG_SUFFIX
            altered_line = self.sneak_command_tag + ' CREATE "' + prefix + self.sep + 'INBOX"' + '\r\n' + altered_line
            self.inbox_created = True
        #Return possibly altered client data line
        return altered_line
    
    def _specialReplace(self,line):
        """Replaces special info that client may "know" about the server - E.G. Gmail box names"""
        new_line = line
        for item in FROM_CLIENT_REPLACE_SPECIAL: #each item a tupple of form (SEARCH_STRING,REPLACE_STRING)
            new_line = new_line.replace(item[0],item[1])
        return new_line
    
    def _specialSplit(self,line):
        """Splits string into tuple at spaces, excepting spaces in quoted text"""
        parts = []
        current = ""
        quotes = ""
        for character in line:
            if character == '\r': #carriage retun
                parts.append(current)
                current = ""
            if quotes:
                current += character                
                if character == quotes:
                    quotes = ""
                    parts.append(current)
                    current = ""
            else:
                if character != " ":
                    current += character
                elif current:
                    parts.append(current)
                    current = ""
                if ['"',"'"].count(character): quotes = character
        if current: parts.append(current)
        return parts
        

class GreenMailImapProxyServerFactory(Factory):

    protocol = GreenMailImapProxyServer

    def __init__(self, host, port):
        self.host = host
        self.port = port


#Execute from shell
import sys, getopt

def main(argv):
    host = HOST
    port = PORT
    global _VERBOSE

    try:                                
        opts, args = getopt.getopt(argv, "hvH:P:", ["help", "verbose", "host=", "port="])
    except getopt.GetoptError:          
        usage(sys.argv[0])                         
        sys.exit(2)                     
    for opt, arg in opts:
        if opt in ("-h", "--help"):
            usage(sys.argv[0])
            sys.exit()
        elif opt in ("-v", "--verbose"):
            _VERBOSE = True
        elif opt in ("-H", "--host"):
            host = arg
        elif opt in ("-P", "--port"):
            port = arg

    factory = GreenMailImapProxyServerFactory(host,port)
    reactor.listenSSL(port, factory, ssl.DefaultOpenSSLContextFactory('ssl/server.key', 'ssl/server.crt'))
    #SSL key and self signed cert generated following instructions at https://help.ubuntu.com/10.04/serverguide/certificates-and-security.html
    print "Proxy Started"
    reactor.run()
    print "Proxy Stopped"

def usage(command):
    print "usage: %s [-h|--help] [-v|--verbose] [-H=|--host=<host_name>] [-P=|--port=<port>]" % command

if __name__ == "__main__":
    main(sys.argv[1:])
