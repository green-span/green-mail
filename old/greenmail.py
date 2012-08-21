#!/usr/bin/env python
#coding:utf-8

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

"""
This file contains code for the central GreenMail Object, as well as an 
executable script that may be used to launch a greenmail daemon.

GreenMail is intended to eventually encapsulate the following functionality:
1. IMAP proxy - for the purposes of masking non-email messages (and designated folders)
   from connected imap clients.
2. SMTP proxy - to register outgoing email addresses in known/trusted contacts list.
3. POP proxy - as IMAP proxy above while allowing POP from mail server INBOX  
4. IMAP persistance engine - allowing connected green-span apps to store/retrieve MIME
   ecoded data to/from special folders in the users connected IMAP server
5. Trust Engine - interpreting a robust set of stored rules (including calls to
   registered helper apps) concerning message delivery based on sender trust ranking
6. Message cue - arranging messages in various mailboxes - and alerting connected
   client applications of new message arival

Version = 0.0.1  
    A. Parses valid logins from config file (NOTE - will eventually be seperate
        config and password files.)
    B. Spawns IMAP proxy server.
    C. Saves reference to IMAP proxy server.

Version = 0.0.0  New File - does nothing

"""

from twisted.internet import reactor

from imapproxyserver import ImapProxyServer

def parseLogins(password_file):
    password_dict = {}
    if ALLVERBOSE or VERBOSE:
        print "parseLogins:"
        print password_file
    for line in password_file:
        if ALLVERBOSE or VERBOSE: print line
        if line and line.count(':'): #line contains 'uid:pwd' pair
            uid, pwd = line.strip().split(':')
            if ALLVERBOSE or VERBOSE: print uid, pwd
            password_dict[uid] = pwd
    return password_dict      

class GreenMail:
    
    def __init__(self,config_file):
        "Initialize GreenMail Singleton from config and start components"
        #Get lognis into form of dict {'uid@host':'password',}
        logins = parseLogins(config_file)
        #Create ImapProxyAgent
        imap_proxy = ImapProxyServer(logins)
        #Preserve references
        self.imap_proxy = imap_proxy
        self.logins = logins
        

#|##############################################################################
#|Test Suite
#|##############################################################################    
import unittest
from cStringIO import StringIO

good_logins_file = """test1@test.com:password1
                      test2@test.com:password2
                      test3@test.com:password3"""

good_logins = {'test1@test.com':'password1',
               'test2@test.com':'password2',
               'test3@test.com':'password3'}

class TestGreenMail(unittest.TestCase):
       
    def test_parseLogins(self):
        f = StringIO(good_logins_file) #Wraps test data in file-like object
        logins = parseLogins(f)
        self.assertEqual(logins,good_logins)
        
#|##############################################################################
#|Shell Execution    
#|##############################################################################
import sys

if __name__ == "__main__":
    "Execute Green-Mail from Shell"
    if not len(sys.argv) == 2:
        print "Usage: %s ConfigFile" % __file__
        sys.exit(1)
    config_file_name = sys.argv[1]
    #Create Instance of GreenMail object
    dummy = GreenMail(file(config_file_name))
    #Start Twisted Event Engine
    print "Green-Mail Started"
    reactor.run()
    print "Green-Mail Stopped"

        