
#|##############################################################################
#|Copyright (c) 2009, The Green-Span Project. All rights reserved. This code is
#|Open Source Free Software - redistribution and use in source and binary forms,
#|with or without modification, are permitted under the Two Clause BSD License.
#|##############################################################################
#|File Created: 2009-04-03
#|Author(s): Sean Hastings,
#|##############################################################################

VERBOSE = True

from globals import ALLVERBOSE

from cStringIO import StringIO

from twisted.mail import imap4
from zope.interface import implements

class ImapProxyMessage(object):
    implements(imap4.IMessage)
        
    def __init__(self,minfo,mailbox):
        if ALLVERBOSE or VERBOSE:
            print "ImapProxyMessage.__init__"
            print minfo
        #initialize instance variables
        self.mailbox = mailbox
        #update/initialize others from messageinfo
        self.update(minfo)
        
    def update(self,minfo):
        """update message info from dictionary of structured message parts
        
        @type minfo: C{dict}
        @param minfo: Dictionarey of message parts formated like this:
        
        {'FLAGS': ['\\Seen', '\\Draft'],
        'UID': '1',
        'RFC822': 'FCC: imap://whysean@localhost/Sent\r\nX-Identity-Key: id1\r\nMessage-ID: <49DA2F1E.8000701@gmail.com>\r\nDate: Mon, 06 Apr 2009 12:34:38 -0400\r\nFrom: Green Span Test <green.span.test@gmail.com>\r\nX-Mozilla-Draft-Info: internal/draft; vcard=0; receipt=0; uuencode=0\r\nUser-Agent: Thunderbird 2.0.0.21 (Windows/20090302)\r\nMIME-Version: 1.0\r\nTo: whysean@gmail.com\r\nSubject: test\r\nContent-Type: text/html; charset=ISO-8859-1\r\nContent-Transfer-Encoding: 7bit\r\n\r\n<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN">\r\n<html>\r\n<head>\r\n</head>\r\n<body bgcolor="#ffffff" text="#000000">\r\ntest\r\n</body>\r\n</html>\r\n\r\n'}
        }
        
        @rtype: C(dict)
        @return: Dictionary mapping header names to values        
        """
        #{'UID': '1', 'RFC822': 'FCC: imap://whysean@localhost/Sent\r\nX-Identity-Key: id1\r\nMessage-ID: <49DA2F1E.8000701@gmail.com>\r\nDate: Mon, 06 Apr 2009 12:34:38 -0400\r\nFrom: Green Span Test <green.span.test@gmail.com>\r\nX-Mozilla-Draft-Info: internal/draft; vcard=0; receipt=0; uuencode=0\r\nUser-Agent: Thunderbird 2.0.0.21 (Windows/20090302)\r\nMIME-Version: 1.0\r\nTo: whysean@gmail.com\r\nSubject: test\r\nContent-Type: text/html; charset=ISO-8859-1\r\nContent-Transfer-Encoding: 7bit\r\n\r\n<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN">\r\n<html>\r\n<head>\r\n</head>\r\n<body bgcolor="#ffffff" text="#000000">\r\ntest\r\n</body>\r\n</html>\r\n\r\n'}
        if ALLVERBOSE or VERBOSE:
            print "ImapProxyMessage.update"
            print minfo
        self.uid = int(minfo['UID'])
        self.flags = minfo['FLAGS']
        #split headers and body
        end_headers = minfo['RFC822'].find('\r\n\r\n') #first blank line indicates start of body
        self.raw_headers = minfo['RFC822'][:end_headers]
        self.body = minfo['RFC822'][(end_headers+4):]
        self.headers = self._parseHeaders(self.raw_headers)
    
    def _parseHeaders(self,raw_headers):
        """Returns parsed headers as dictionary

        @type rfc822: C{str}
        @param rfc822: The text of the message - headers are seperate by CRLF like this:
        
        'FCC: imap://whysean@localhost/Sent\r\n
        X-Identity-Key: id1\r\n
        Message-ID: <49DA2F1E.8000701@gmail.com>\r\n
        Date: Mon, 06 Apr 2009 12:34:38 -0400\r\n
        From: Green Span Test <green.span.test@gmail.com>\r\n
        X-Mozilla-Draft-Info: internal/draft; vcard=0; receipt=0; uuencode=0\r\n
        User-Agent: Thunderbird 2.0.0.21 (Windows/20090302)\r\n
        MIME-Version: 1.0\r\n
        To: whysean@gmail.com\r\n
        Subject: test\r\n
        Content-Type: text/html; charset=ISO-8859-1\r\n
        Content-Transfer-Encoding: 7bit'

        @rtype: C(dict)
        @return: Dictionary mapping header names (cast to upper case) to values
        """
        #Add standin for multiline headers (CrLf followed by space or tab)
        if ALLVERBOSE or VERBOSE:
            print "ImapProxyMessage['%s']._parseheaders" % self.uid
            print raw_headers
        raw_headers = raw_headers.replace('\r\n ','[MLSPC]').replace('\r\n\t','[MLTAB]')
        headers = {}
        lines = raw_headers.split('\r\n')
        for line in lines:
            key_end = line.find(':')
            key = line[:key_end].upper()
            value = line[key_end+1:].lstrip()
            #put multi-line header Cr+Lf+(SAPCE or TAB) back in
            headers[key] = value.replace('[MLSPC]','\r\n ').replace('[MLTAB]','\r\n\t')
        if ALLVERBOSE or VERBOSE: print headers
        return headers
                        
    def getHeaders(self, negate, *names):
        """Retrieve a group of message headers.

        @type names: C{tuple} of C{str}
        @param names: The names of the headers to retrieve or omit.

        @type negate: C{bool}
        @param negate: If True, indicates that the headers listed in C{names}
        should be omitted from the return value, rather than included.

        @rtype: C{dict}
        @return: A mapping of header field names to header field values
        """
        if ALLVERBOSE or VERBOSE:
            print "ImapProxyMessage['%s'].getHeaders" % self.uid
            print "negate = %s " % negate
            print names
        results = {}        
        for name in names:
            if self.headers.has_key(name):
                if not negate: results[name] = self.headers[name]
            else:
                if negate: results[name] = self.headers[name]
        if ALLVERBOSE or VERBOSE: print results
        return results

    def getBodyFile(self):
        """Retrieve a file object containing only the body of this message.
        """
        if ALLVERBOSE or VERBOSE:
            print "ImapProxyMessage[%s].getBodyFile" % self.uid
        return StringIO(self.body)

    def getSize(self):
        """Retrieve the total size, in octets, of this message.

        @rtype: C{int}
        """
        if ALLVERBOSE or VERBOSE:
            print "ImapProxyMessage[%s].getSize()" % self.uid
        result = len(self.raw_headers) + len(self.body) + 4
        if ALLVERBOSE or VERBOSE:
            print result
        return result
    
    def isMultipart(self):
        """Indicate whether this message has subparts.

        @rtype: C{bool}
        """
        if ALLVERBOSE or VERBOSE:
            print "ImapProxyMessage[%s].isMultipart" % self.uid
        return self.raw_headers.__contains__("multipart")

    def getSubPart(self,part):
        """Retrieve a MIME sub-message

        @type part: C{int}
        @param part: The number of the part to retrieve, indexed from 0.

        @raise IndexError: Raised if the specified part does not exist.
        @raise TypeError: Raised if this message is not multipart.

        @rtype: Any object implementing C{IMessagePart}.
        @return: The specified sub-part.
        """
        if ALLVERBOSE or VERBOSE:
            print "ImapProxyMessage[%s].getSubPart(%s)" % (self.uid, part)
        raise IndexError("subparts are not yet implimented")

    def getUID(self):
        """Retrieve the unique identifier associated with this message.
        """
        if ALLVERBOSE or VERBOSE:
            print "ImapProxyMessage[%s].getUID" % self.uid
            print self.uid
        return self.uid

    def getFlags(self):
        """Retrieve the flags associated with this message.

        @rtype: C{iterable}
        @return: The flags, represented as strings.
        """
        if ALLVERBOSE or VERBOSE:
            print "ImapProxyMessage[%s].getFlags" % self.uid
            print self.flags
        return self.flags

    def getInternalDate(self):
        """Retrieve the date internally associated with this message.

        @rtype: C{str}
        @return: An RFC822-formatted date string.
        """
        result = self.getHeader('DATE')
        if ALLVERBOSE or VERBOSE:
            print "ImapProxyMessage[%s].getInternalDate" % self.uid
            print result
        return result

    def getHeader(self,key):
        result = self.headers[key]
        if ALLVERBOSE or VERBOSE:
            print "ImapProxyMessage[%s].getHeader(%s)" % (self.uid, key)
            print result
        return result
    
#|##############################################################################
#|Test Suite
#|##############################################################################    
import unittest

class TestImapProxyMessage(unittest.TestCase):
       
    def test_parseHeaders(self):
        RFC822_RAW_DATA = """FCC: imap://whysean@localhost/Sent\r\nX-Identity-Key: id1\r\nMessage-ID: <49DA2F1E.8000701@gmail.com>\r\nDate: Mon, 06 Apr 2009 12:34:38 -0400\r\nFrom: Green Span Test <green.span.test@gmail.com>\r\nX-Mozilla-Draft-Info: internal/draft; vcard=0; receipt=0; uuencode=0\r\nUser-Agent: Thunderbird 2.0.0.21 (Windows/20090302)\r\nMIME-Version: 1.0\r\nTo: whysean@gmail.com\r\nSubject: test\r\nContent-Type: text/html; charset=ISO-8859-1\r\nContent-Transfer-Encoding: 7bit"""
        EXPECTED_RESULTS = {'FCC':'imap://whysean@localhost/Sent',
                           'X-IDENTITY-KEY':'id1',
                           'MESSAGE-ID':'<49DA2F1E.8000701@gmail.com>',
                           'DATE':'Mon, 06 Apr 2009 12:34:38 -0400',
                           'FROM':'Green Span Test <green.span.test@gmail.com>',
                           'X-MOZILLA-DRAFT-INFO':'internal/draft; vcard=0; receipt=0; uuencode=0',
                           'USER-AGENT':'Thunderbird 2.0.0.21 (Windows/20090302)',
                           'MIME-VERSION':'1.0',
                           'TO':'whysean@gmail.com',
                           'SUBJECT':'test',
                           'CONTENT-TYPE':'text/html; charset=ISO-8859-1',
                           'CONTENT-TRANSFER-ENCODING':'7bit'
                           }
        EXPECTED_BODY = """<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN">\r\n<html>\r\n<head>\r\n</head>\r\n<body bgcolor="#ffffff" text="#000000">\r\ntest\r\n</body>\r\n</html>\r\n\r\n"""
        results = ImapProxyMessage._parseHeaders(None,RFC822_RAW_DATA)
        if ALLVERBOSE or VERBOSE:
            print "TestImapProxyMessage.test_parseHeaders"
            print results
        self.assertEqual(results,EXPECTED_RESULTS)        

#|##############################################################################
#|Shell Executtion    
#|##############################################################################
import sys

if __name__=='__main__':
    unittest.main()        