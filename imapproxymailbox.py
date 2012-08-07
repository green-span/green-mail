
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

import types

from twisted.mail import imap4
from zope.interface import implements

from imapproxymessage import ImapProxyMessage

class ImapProxyMailbox(object):
    implements(imap4.IMailbox)
    
    def __init__(self,boxinfo,server):
        if ALLVERBOSE or VERBOSE:
            print "ImapProxyMailbox.__init__"
            print boxinfo
        #initialize instance variables
        self.server = server
        self.listeners = []
        self.flags = []
        self.path = None
        self.exists = None
        self.read_write = None
        self.uid_next = None
        self.uid_validity = None
        self.recent = None
        #update from passed boxinfo
        self.updateInfo(boxinfo)
        #initialize message storage
        self.message_list = []
        self.lost_message_list = []
        self.message_dict = {}
        
    def updateInfo(self,boxinfo):
        if ALLVERBOSE or VERBOSE:
            print "ImapProxyMailbox.updateInfo"
            print boxinfo
        if isinstance(boxinfo,tuple):
            self.path = boxinfo[2]
            self.hierarchy_delimiter = boxinfo[1]
            self.setFlags(boxinfo[0])
        elif isinstance(boxinfo,dict):
            """Example of mailbox properties dictionary format:
               {'EXISTS': 0,
                'PERMANENTFLAGS': ('\\Answered', '\\Flagged', '\\Draft', '\\Deleted', '\\Seen', '\\*'),
                'READ-WRITE': 1,
                'UIDNEXT': 2,
                'FLAGS': ('\\Answered', '\\Flagged', '\\Draft', '\\Deleted', '\\Seen'), 'PATH': 'INBOX',
                'UIDVALIDITY': 618071116,
                'RECENT': 0
                }
            """
            self.path = boxinfo.get('PATH')
            self.setFlags(boxinfo.get('FLAGS'))
            self.setPFlags(boxinfo.get('PERMANENTFLAGS'))
            self.exists = boxinfo.get('EXISTS')
            self.read_write = boxinfo.get('READ-WRITE')
            self.uid_next = boxinfo.get('UIDNEXT')
            self.uid_validity = boxinfo.get('UIDVALIDITY')
            self.recent = boxinfo.get('RECENT')
            self.unseen = boxinfo.get('UNSEEN')
                                          
    def getUIDValidity(self):
        """Return the unique validity identifier for this mailbox.

        @rtype: C{int}
        """
        if ALLVERBOSE or VERBOSE:
            print "ImapProxyMailbox[%s].getUIDValidity()" % self.path
            print self.uid_validity
        return self.uid_validity

    def getUIDNext(self):
        """Return the likely UID for the next message added to this mailbox.

        @rtype: C{int}
        """
        return self.uid_next

    def getUID(self,message):
        """Return the UID of a message in the mailbox

        @type message: C{int}
        @param message: The message sequence number

        @rtype: C{int}
        @return: The UID of the message.
        """
        if ALLVERBOSE or VERBOSE:
            print "ImapProxyMailbox[%s].getUIDValidity('%s')" % (self.path,message)
        try:
            self.message_list[message].getUID()
        except:
            raise imap4.MailboxException("Could not get uid for message" % message)

    def getMessageCount(self):
        """Return the number of messages in this mailbox.

        @rtype: C{int}
        """
        if ALLVERBOSE or VERBOSE:
            print "ImapProxyMailbox[%s].getmessageCount()" % self.path
            print self.exists
        return self.exists

    def getRecentCount(self):
        """Return the number of messages with the 'Recent' flag.

        @rtype: C{int}
        """
        if ALLVERBOSE or VERBOSE:
            print "ImapProxyMailbox[%s].getRecentCount()" % self.path
            print self.recent
        return self.recent

    def getUnseenCount(self):
        """Return the number of messages with the 'Unseen' flag.

        @rtype: C{int}
        """
        if ALLVERBOSE or VERBOSE:
            print "ImapProxyMailbox[%s].getRecentCount()" % self.path
            print self.unseen
        return self.unseen

    def isWriteable(self):
        """Get the read/write status of the mailbox.

        @rtype: C{int}
        @return: A true value if write permission is allowed, a false value otherwise.
        """
        """
        Not sure when or why an IMAP box would not be writable - Sean TODO - look
        into this. A wrapper class that hides write functions would be the way to
        go if good reason for non-writeable box presents itself.
        For now will just always have writable boxes 
        """
        writable = (self.server.selected == self.path)
        if ALLVERBOSE or VERBOSE:
            print "ImapProxyMailbox[%s].isWriteable()" % self.path
            print writable
        return writable
    
    def destroy(self):
        """Called before this mailbox is deleted, permanently.

        If necessary, all resources held by this mailbox should be cleaned
        up here.  This function _must_ set the \\Noselect flag on this
        mailbox.
        """
        if ALLVERBOSE or VERBOSE:
            print "ImapProxyMailbox[%s].isWriteable()" % self.path
        self.flags.append("\\Noselect") #ok, it does that...

    def requestStatus(self,names):
        """Return status information about this mailbox.

        Mailboxes which do not intend to do any special processing to
        generate the return value, C{statusRequestHelper} can be used
        to build the dictionary by calling the other interface methods
        which return the data for each name.

        @type names: Any iterable
        @param names: The status names to return information regarding.
        The possible values for each name are: MESSAGES, RECENT, UIDNEXT,
        UIDVALIDITY, UNSEEN.

        @rtype: C{dict} or C{Deferred}
        @return: A dictionary containing status information about the
        requested names is returned.  If the process of looking this
        information up would be costly, a deferred whose callback will
        eventually be passed this dictionary is returned instead.
        """
        if ALLVERBOSE or VERBOSE:
            print "ImapProxyMailbox[%s].requestStatus" % self.path
        d = self.server.protocol.examine(self.path)
        d.addCallback(self.__requestStatus_cb,names)
        d.addErrback(self.__requestStatus_err,self.path)
        return d
    
    def __requestStatus_cb(self,results,request):
        """
        EXAMINE cmd succeeds - format and return dict of requested info.
        results names: 'FLAGS','EXISTS','RECENT','UNSEEN','PERMANENTFLAGS','UIDVALIDITY'
        request names: 'MESSAGES', 'RECENT', 'UIDNEXT', 'UIDVALIDITY', 'UNSEEN'.
        Most keys are the same but results['MESSAGES'] should be results['EXISTS'].
        Returns all results info (request is moot - calling code can access what it needs
        from all available values returned in dict)
        """
        if ALLVERBOSE or VERBOSE:
            print "ImapProxyMailbox[%s].__requestStatus_cb" % self.path
            print results
        #take this oportunity to update local box info
        self.updateInfo(results)
        #add in the one key value that is different name and return all values
        results['MESSAGES'] = results['EXISTS']
        return results
    
    def __requestStatus_err(self,results,path):
        "EXAMINE cmd fails - raise exception"
        if ALLVERBOSE or VERBOSE:
            print "ImapProxyMailbox[%s].__requestStatus_err" % self.path
            print results
        raise imap4.MailboxException("Could not get status for mailbox %s" % path)
  
    def addListener(self,listener):
        """Add a mailbox change listener

        @type listener: Any object which implements C{IMailboxListener}
        @param listener: An object to add to the set of those which will
        be notified when the contents of this mailbox change.
        """
        #Sean TODO (Is this for a subscribed box situation?)
        if ALLVERBOSE or VERBOSE: print "ImapProxyMailbox[%s].addListener()" % self.path
        if not self.listeners.count(listener):
            self.listeners.append(listener)
        return True
    
    def removeListener(self,listener):
        """Remove a mailbox change listener

        @type listener: Any object previously added to and not removed from
        this mailbox as a listener.
        @param listener: The object to remove from the set of listeners.

        @raise ValueError: Raised when the given object is not a listener for
        this mailbox.
        """
        if ALLVERBOSE or VERBOSE:
            print "ImapProxyMailbox[%s].removeListener" % self.path
        if not self.listeners.count(listener):
            err_str = "Specified lister was not registered"
            if ALLVERBOSE or VERBOSE: print err_str            
            raise ValueError(err_str)        
        self.listeners.remove(listener)
        return True

    def addMessage(self,message, flags = (), date = None):
        """Add the given message to this mailbox.

        @type message: A file-like object
        @param message: The RFC822 formatted message

        @type flags: Any iterable of C{str}
        @param flags: The flags to associate with this message

        @type date: C{str}
        @param date: If specified, the date to associate with this
        message.

        @rtype: C{Deferred}
        @return: A deferred whose callback is invoked with the message
        id if the message is added successfully and whose errback is
        invoked otherwise.

        @raise ReadOnlyMailbox: Raised if this Mailbox is not open for
        read-write.
        """
        if ALLVERBOSE or VERBOSE:
            print "ImapProxyMailbox[%s].addMessage" %self.path
            print message
            print flags
            print date
        d = self.server.protocol.append(self.path, message, flags, date)
        d.addCallback(self.__addMessage_cb,message,flags,date)
        d.addErrback(self.__addMessage_err,message,flags,date)
        return d
    
    def __addMessage_cb(self,results,message,flags,date):
        "APPEND cmd succeeds - add message to local message cache"
        if ALLVERBOSE or VERBOSE:
            print "ImapProxyMailbox[%s].__addMessage_cb" %self.path
            print results
        #result does not give UID or sequence. Can not really add this message to cache...
        #??? maybe mark box as needing refresh poll or some such???
        return True

    def __addMessage_err(self,results,message,flags,date):
        "APPEND cmd fails - raise exception"
        if ALLVERBOSE or VERBOSE:
            print "ImapProxyMailbox[%s].__addMessage_err" %self.path
            print results
        raise imap4.ReadOnlyMailbox("Message could not be added to mailbox:%s"%self.path)
    
    def expunge(self):
        """Remove all messages flagged \\Deleted. ALSO closes (deselects) mailbox 

        @rtype: C{list} or C{Deferred}
        @return: The list of message sequence numbers which were deleted,
        or a C{Deferred} whose callback will be invoked with such a list.

        @raise ReadOnlyMailbox: Raised if this Mailbox is not open for
        read-write.
        """
        if ALLVERBOSE or VERBOSE:
            print "ImapProxyMailbox[%s].expunge" % self.path
        #Check that mailbox is selected
        if not (self.server.selected == self.path):
            raise imap4.ReadOnlyMailbox("Mailbox '%s' is not selected" % self.path)
        #Select this box if not already selected on server.
        if self.server.selected != self.path:
            d = self.server.protocol.select(self.path)
            d.addCallback(self.do_expunge)
        else:  #Do expunge now
            d = self.do_expunge()
        return d
    
    def do_expunge(self,results=None): 
        d = self.server.protocol.expunge()
        d.addCallback(self.__expunge_cb)
        d.addErrback(self.__expunge_err)
        return d
    
    def __expunge_cb(self,results):
        if ALLVERBOSE or VERBOSE:
            print "ImapProxyMailbox[%s].__expunge_cb" %self.path
            print results
        #Deselect mailbox
        self.server.selected = None
        #Remove expunged messages
        for id in results:
            del fred[id]
        return results

    def __expunge_err(self,results):
        if ALLVERBOSE or VERBOSE:
            print "ImapProxyMailbox[%s].__expunge_err" %self.path
            print results
        raise imap4.ReadOnlyMailbox("Mailbox:[%s] could not be expunged"%self.path)
       
    def fetch(self,messages, uid):
        """Retrieve one or more messages.

        @type messages: C{MessageSet}
        @param messages: The identifiers of messages to retrieve information
        about

        @type uid: C{bool}
        @param uid: If true, the IDs specified in the query are UIDs;
        otherwise they are message sequence IDs.

        @rtype: C{list} or C{Deferred}
        @return: A list (or other iterable) of two-tuples of message sequence
        numbers and implementors of C{IMessage} or a C{Deferred} whose callback
        will be invoked with such a list.
        """
        if ALLVERBOSE or VERBOSE:
            print "ImapProxyMailbox[%s].fetch" % self.path
            print messages
            print uid
        #select mailbox if nescessary then do command
        if self.server.selected != self.path:
            d = self.server.protocol.select(self.path)
            d.addCallback(self.do_fetch,messages,uid)
        else: #do command immediately
            d = self.do_fetch(None,messages,uid)
        return d

    def do_fetch(self,results,messages,uid):
        d = self.server.protocol._fetch(messages, useUID=uid, rfc822=1, flags=1)
        d.addCallback(self.__fetch_cb)
        d.addErrback(self.__fetch_err)
        return d

    def __fetch_cb(self,results):
        """FETCH cmd succeedend on server - Retrieve one or more messages.

        @type results: C{dict}
        @param reuslts: Dictionary contianing various entries of various types
        recording various message attributes of one or more messages

        @type uid: C{bool}
        @param uid: If true, the IDs specified in the query are UIDs;
        otherwise they are message sequence IDs.

        @rtype: C{list}
        @return: A list (or other iterable) of two-tuples of message sequence
        numbers and implementors of C{IMessage}
        """
        if ALLVERBOSE or VERBOSE:
            print "ImapProxyMailbox[%s].__fetch_cb" % self.path
            print results
        parsed_results = self.__parseFetchResults(results)
        #map server response to required return list of tuples
        two_tupple_list = []
        for seq_num in parsed_results.keys():
            minfo = parsed_results[seq_num]
            newmessage = self._getMessage(seq_num,minfo) #retrieve or create new message object
            two_tupple = (seq_num,newmessage)
            two_tupple_list.append(two_tupple)
        return two_tupple_list

    def _getMessage(self,seq_num,minfo):
        """
        Returns message from cache OR creates it + adds it to cache + returns it.
        If messageinfo contains known uid - message is updated and returned from cache.
        If uid is unknown, message is created, cached, and returned.
        Cache uses both a list preserving message order and a dictionary keyed by UID.
        """
        uid = int(minfo['UID'])
        try: #check if message in known - if so update it
            message = self.message_dict[uid]
            message.update(minfo)
            self._resequenceOld(seq_num,message)
        except KeyError: #messege is unkown - create and add it
            message = ImapProxyMessage(minfo,self)
            self.message_dict[uid] = message
            self._sequenceNew(seq_num,message)
        return message
     
    def _resequenceOld(self,seq_num,message):
        """Moves known message to new position in sequence"""
        try: #Remove message from lost_list
            self.lost_message_list.remove(message)          
        except: #not lost, empty current slot
            pos = self.message_list.index(message) + 1
            if pos == seq_num:
                return #all is as it should be
            #remove message from message_list
            if pos < len(self.message_list):
                self.message_list[pos-1] = None
            else: #is last item in list - remove it
                self.message_list.pop()
        #message is gone from list - put it back in
        self._sequenceNew(seq_num,message)

    def _sequenceNew(self,seq_num,message):
        """Inserts new message to a position in the message list"""
        #if list not big enough - pad to right before and append
        length = len(self.message_list)
        if seq_num > length:
            for i in range(seq_num - len(self.message_list)):
                self.message_list.append(None)
            self.message_list.append(message)
        #else check position - if filled - fill it, bumping existing to lost_list
        else:
            existing = self.message_list[seq_num - 1]
            if existing: self.lost_message_list.append(existing)
            self.message_list[seq_num-1] = message
            
    def __parseFetchResults(self, (lines, last)):
        """Coppied this from imap4.IMAP4Server.__cbfetch becasue _fetch needed to
        be called directly with custom set of attributes, and then this function
        which cleans the results was needed, but, as a private function, was not
        directly avaialble. 
        """
        if ALLVERBOSE or VERBOSE:
            print "ImapProxyMailbox[%s].__parseFetchResults" %self.path
        flags = {}
        for line in lines:
            parts = line.split(None, 2)
            if len(parts) == 3:
                if parts[1] == 'FETCH':
                    try:
                        id = int(parts[0])
                    except ValueError:
                        raise Exception("IllegalServerResponse:%s" % line)
                    else:
                        data = imap4.parseNestedParens(parts[2])
                        while len(data) == 1 and isinstance(data, types.ListType):
                            data = data[0]
                        while data:
                            if len(data) < 2:
                                raise Exception("Not enough arguments")
                            flags.setdefault(id, {})[data[0]] = data[1]
                            del data[:2]
                else:
                    print '(2)Ignoring ', parts
            else:
                print '(3)Ignoring ', parts
        if ALLVERBOSE or VERBOSE:
            print flags
        return flags

    def __fetch_err(self,results):
        if ALLVERBOSE or VERBOSE:
            print "ImapProxyMailbox[%s].__fetch_err" %self.path
            print results
        raise imap4.ReadOnlyMailbox("Could not fetch messages from Mailbox:[%s]"%self.path)


    def store(self,messages, flags, mode, uid):
        """Set the flags of one or more messages.

        @type messages: A MessageSet object with the list of messages requested
        @param messages: The identifiers of the messages to set the flags of.

        @type flags: sequence of C{str}
        @param flags: The flags to set, unset, or add.

        @type mode: -1, 0, or 1
        @param mode: If mode is -1, these flags should be removed from the
        specified messages.  If mode is 1, these flags should be added to
        the specified messages.  If mode is 0, all existing flags should be
        cleared and these flags should be added.

        @type uid: C{bool}
        @param uid: If true, the IDs specified in the query are UIDs;
        otherwise they are message sequence IDs.

        @rtype: C{dict} or C{Deferred}
        @return: A C{dict} mapping message sequence numbers to sequences of C{str}
        representing the flags set on the message after this operation has
        been performed, or a C{Deferred} whose callback will be invoked with
        such a C{dict}.

        @raise ReadOnlyMailbox: Raised if this mailbox is not open for
        read-write.
        """    
        if ALLVERBOSE or VERBOSE:
            print "ImapProxyMailbox[%s].store" %self.path
            print messages
            print flags
            print mode
            print uid
        #select mailbox if nescessary then do command
        if self.server.selected != self.path:
            d = self.server.protocol.select(self.path)
            d.addCallback(self.do_store,messages, flags, mode, uid)
        else: #do command immediately
            d = self.do_store(None,messages, flags, mode, uid)
        return d
    
    def do_store(self,results,messages, flags, mode, uid):
        d = self.server.protocol.setFlags(messages, flags, mode, uid)
        d.addCallback(self.__store_cb,messages,flags,mode,uid)
        d.addErrback(self.__store_err)
        return d
    
    def __store_cb(self,results,messages,flags,mode,uid):
        if ALLVERBOSE or VERBOSE:
            print "ImapProxyMailbox[%s].__store_cb" %self.path
            print results
        #TODO - update flags on messages in local cache
        #TODO map server response to required return dictionary
        return {}

    def __store_err(self,results):
        if ALLVERBOSE or VERBOSE:
            print "ImapProxyMailbox[%s].__store_err" %self.path
            print results
        raise imap4.ReadOnlyMailbox("Could not store flags on messages in Mailbox:[%s]"%self.path)
                
    def getHierarchicalDelimiter(self):
        "Returns the mailbox's hierarchy delimiter. For example: The '/' in 'Old Mail/Stalkers/Hermaphrodites'"
        if ALLVERBOSE or VERBOSE:
            print "ImapProxyMailbox.getHierarchicalDelimiter"
            print self.hierarchy_delimiter
        return self.hierarchy_delimiter

    def getFlags(self):
        "Return list of supported flags"
        if ALLVERBOSE or VERBOSE:
            print "ImapProxyMailbox[%s].getFlags" % self.path
            print self.flags
        return self.flags

    def getPFlags(self):
        "Return list of supported flags"
        if ALLVERBOSE or VERBOSE:
            print "ImapProxyMailbox[%s].getPFlags" % self.path
            print self.pflags
        return self.pflags
    
    def setPFlags(self,new_flags):
        self.pflags = self.__parseFlags(new_flags)
        
    def setFlags(self,new_flags):
        self.flags = self.__parseFlags(new_flags)
        
    def __parseFlags(self,new_flags):
        "set flags in list"
        if ALLVERBOSE or VERBOSE:
            print "ImapProxyMailbox.__parseFlags"
            print new_flags
        flag_list = []
        for flag in new_flags:
            self.flags.append(flag)
        return flag_list
