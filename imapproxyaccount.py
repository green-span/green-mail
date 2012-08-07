
#|##############################################################################
#|Copyright (c) 2009, The Green-Span Project. All rights reserved. This code is
#|Open Source Free Software - redistribution and use in source and binary forms,
#|with or without modification, are permitted under the Two Clause BSD License.
#|##############################################################################
#|File Created: 2009-04-02
#|Author(s): Sean Hastings,
#|##############################################################################

VERBOSE = True

from globals import ALLVERBOSE

from twisted.mail import imap4
from zope.interface import implements
import os

from imapproxymailbox import ImapProxyMailbox

class ImapProxyAccount(object):
    implements(imap4.IAccount)
    
    def __init__(self, addresspwd, proxy):
        if ALLVERBOSE or VERBOSE: print "ImapProxyAccount.__init__(%s)" % addresspwd
        #initialize local object variables
        self.connected = False #becomes True when server connection is established
        self.server = None #upstream refference to server - instanced from cache or by deffered method (see firstConnect)
        self.proxy = proxy #downsream reference to proxy
        #Client side oppinion of IMAP protocol state - server side opinion at self.server.selected
        self.selected = None #starts with no mailkbox selected

    def firstConnect(self, protocol):
        """Calback function when server connection first succeeds"""
        if ALLVERBOSE or VERBOSE: print "ImapProxyAccount.firstConnect - WOOHOO! PROXY CONNECTED THROUGH!"
        self.server.connected = True
        self.server.protocol = protocol
        return self.getSubscribed()
    
    def connectError(self):
        """Callback function if server connection fails"""
        if ALLVERBOSE or VERBOSE: print "ImapProxyAccount.connectError"
        print >> sys.stderr, "Error:", error.getErrorMessage()
        
    def getSubscribed(self):
        """gets subscribed mailboxes from server - should do this at first connect"""
        if ALLVERBOSE or VERBOSE: print "ImapProxyAccount.getSubscribed()"
        d = self.server.protocol.lsub("","*")
        d.addCallback(self.__getSubscribed_cb)
        return d

    def __getSubscribed_cb(self,results):
        """LSUB returned successfully - add all to subscribed list"""
        if ALLVERBOSE or VERBOSE:
            print "ImapProxyAccount.__getSubscribed_cb"
            print results
        subscribed_list = []
        for boxinfo in results:
            name = boxinfo[2] 
            box = self._getBox(boxinfo) #creates box and caches it locally
            subscribed_list.append(name)
        self.server.subscribed = subscribed_list
    
    def addMailbox(self,name, mbox = None):
        """Add a new mailbox to this account

        @type name: C{str}
        @param name: The name associated with this mailbox.  It may not
        contain multiple hierarchical parts.

        @type mbox: An object implementing C{IMailbox}
        @param mbox: The mailbox to associate with this name.  If C{None},
        a suitable default is created and used.

        @rtype: C{Deferred} or C{bool}
        @return: A true value if the creation succeeds, or a deferred whose
        callback will be invoked when the creation succeeds.

        @raise MailboxException: Raised if this mailbox cannot be added for
        some reason.  This may also be raised asynchronously, if a C{Deferred}
        is returned.
        """
        if ALLVERBOSE or VERBOSE: print "ImapProxyAccount.addMailbox"
        raise imap4.MailboxException("Permision denied - addMailbox function not yet implimented")
        
    def create(self,path):
        """Create a new mailbox from the given hierarchical name.

        @type path: C{str}
        @param path: The full hierarchical name of a new mailbox to create.
        If any of the inferior hierarchical names to this one do not exist,
        they are created as well.

        @rtype: C{Deferred} or C{bool}
        @return: A true value if the creation succeeds, or a deferred whose
        callback will be invoked when the creation succeeds.

        @raise MailboxException: Raised if this mailbox cannot be added.
        This may also be raised asynchronously, if a C{Deferred} is
        returned.
        """
        if ALLVERBOSE or VERBOSE: print "ImapProxyAccount.create(%s)" % path
        #raise exception if mailbox exists
        if self.server.mailboxCache.has_key(path):
            raise imap4.MailboxException("Mailbox '%s' already exists" % path)
        d = self.server.protocol.create(path)
        d.addCallback(self.__create_cb,path)
        d.addErrback(self.__create_err,path)
        return d  #returns Deferred
 
    def __create_cb(self, result, path):
        "deferred CREATE cmd succeeds - return True"
        if ALLVERBOSE or VERBOSE:
            print "ImapProxyAccount.__create_cb('%s')" % path
            print result
        return True
        
    def __create_err(self, result, path):
        "deferred CREATE cmd failed - return False"
        if ALLVERBOSE or VERBOSE:
            print "ImapProxyAccount.__create_err('%s')" % path
            print result
        raise imap4.MailboxException("Server could not create mailbox")
    
    def select(self,name, rw = True):
        """Acquire a mailbox, given its name.

        @type name: C{str}
        @param name: The mailbox to acquire

        @type rw: C{bool}
        @param rw: If a true value, request a read-write version of this
        mailbox.  If a false value, request a read-only version.

        @rtype: Any object implementing C{IMailbox} or C{Deferred}
        @return: The mailbox object, or a C{Deferred} whose callback will
        be invoked with the mailbox object.  None may be returned if the
        specified mailbox may not be selected for any reason.
        """
        if ALLVERBOSE or VERBOSE: print "ImapProxyAccount.select(%s)" % name
        if rw:
            d = self.server.protocol.select(name)
            d.addCallback(self.__select_cb,name,rw)
        else: #inspect command used for non read write look at mailbox
            d = self.server.protocol.examine(name)
            d.addCallback(self.__select_cb,name,rw)
        return d
    
    def __select_cb(self,boxinfo,path,rw):
        "Return Selected box and register it as the selected box in the account"
        if ALLVERBOSE or VERBOSE:
            print "ImapProxyAccount.__select_cb('%s')" % path
            print boxinfo
        boxinfo['PATH'] = path #adds path value to boxinfo for mailbox object creation/storgage
        box = self._getBox(boxinfo)
        #set selected on server if read write version requested/selected
        if rw: self.server.selected = path
        return box

    def delete(self,name):
        """Delete the mailbox with the specified name.

        @type name: C{str}
        @param name: The mailbox to delete.

        @rtype: C{Deferred} or C{bool}
        @return: A true value if the mailbox is successfully deleted, or a
        C{Deferred} whose callback will be invoked when the deletion
        completes.

        @raise MailboxException: Raised if this mailbox cannot be deleted.
        This may also be raised asynchronously, if a C{Deferred} is returned.
        """
        if ALLVERBOSE or VERBOSE: print "ImapProxyAccount.delete('%s')" % name
        d = self.server.protocol.delete(name)
        d.addCallback(self.__delete_cb,name)
        d.addErrback(self.__delete_err,name)
        return d  #returns Deferred

    def __delete_cb(self,result,name):
        if ALLVERBOSE or VERBOSE:
            print "ImapProxyAccount.delete_cb('%s')" % name
            print result
        #remove proxy references
        if self.server.mailboxCache.has_key(name): del self.maiboxCache[name]
        for i in range(self.server.subscribed.count(name)): self.server.subscribed.count.remove(name)
        if self.server.selected == name: self.server.selected = None
        if self.selected == name: self.selected = None
        return True
    
    
    def __delete_err(self,reason,name):
        if ALLVERBOSE or VERBOSE:
            print "ImapProxyAccount.__delete_err('%s')" % name
            print reason
        raise imap4.MailboxException("Unable to delete mailbox: %s" % name)

    def rename(self,oldname, newname):
        """Rename a mailbox

        @type oldname: C{str}
        @param oldname: The current name of the mailbox to rename.

        @type newname: C{str}
        @param newname: The new name to associate with the mailbox.

        @rtype: C{Deferred} or C{bool}
        @return: A true value if the mailbox is successfully renamed, or a
        C{Deferred} whose callback will be invoked when the rename operation
        is completed.

        @raise MailboxException: Raised if this mailbox cannot be
        renamed.  This may also be raised asynchronously, if a C{Deferred}
        is returned.
        """
        if ALLVERBOSE or VERBOSE: print "ImapProxyAccount.rename('%s','%s')" % (oldname, newname)
        d = self.server.protocol.rename(oldname,newname)
        d.addCallback(self.__rename_cb,oldname,newname)
        d.addErrback(self.__rename_err,oldname,newname)
        return d  #returns Deferred

    def __rename_cb(self,result,oldname,newname):
        if ALLVERBOSE or VERBOSE:
            print "ImapProxyAccount.rename_cb('%s','%s')" % (oldname,newname)
            print result
        #remove proxy references
        if self.server.mailboxCache.has_key(oldname):
            self.server.mailboxCache[newname] = self.maiboxCache[oldname]
            del self.server.maiboxCache[oldname]
            self.server.mailboxCache[newname].rename(newname)
        for i in range(self.server.subscribed.count(oldname)):
            self.server.subscribed.remove(oldname)
            self.server.subscribed.append(newname)
        if self.selected == oldname: self.selected = newname
        if self.server.selected == oldname: self.server.selected = newname
        return True
     
    def __renameFailed(self,reason,oldname,newname):
        if ALLVERBOSE or VERBOSE:
            print "ImapProxyAccount.__delete_err('%s','%s')" % (oldname, newname)
            print reason
        except_string = "Unable to rename mailbox %s to %s" % (oldname, newname)
        raise imap4.MailboxException(except_string)

    def isSubscribed(self,name):
        """Check the subscription status of a mailbox

        @type name: C{str}
        @param name: The name of the mailbox to check

        @rtype: C{Deferred} or C{bool}
        @return: A true value if the given mailbox is currently subscribed
        to, a false value otherwise.  A C{Deferred} may also be returned
        whose callback will be invoked with one of these values.
        """
        #Currently just checks subscriptions in memory with no call to server
        if ALLVERBOSE or VERBOSE: print "ImapProxyAccount.isSubscribed(%s)" % name
        result = self.server.subscribed.count(name)
        if ALLVERBOSE or VERBOSE:
            print self.server.subscribed
            if result: print "SUBSCRIBED = TRUE"
            else: print "SUBSCRIBED = FALSE"
        if result: return True
        else: return False

    """ Deffered version of is_subscribed
        #though specified in docs - deffered is never called back
        #Currently just checks subscriptions in memory with no call to server
        if ALLVERBOSE or VERBOSE: print "ImapProxyAccount.isSubscribed(%s)" % name
        d = self.server.protocol.lsub("",name)
        d.addCallback(self.__isSubscribed_cb,name)
        d.addErrback(self.__isSubscribed_err,name)
        return d
    """
    
    def __isSubscribed_cb(self,results,name):
        """LSUB returned successfully - if specified box found - update/create it and return true"""
        if ALLVERBOSE or VERBOSE:
            print "ImapProxyAccount.isSubscribed(%s)" % name
            results
        #results come in as a list of lists - each row contains several mailbox parameters
        #boxinfo[2] is the mailbox name/path
        for boxinfo in results:
            result_name = boxinfo[2]
            if result_name == name:
                dummy = self._getBox(boxinfo) #creates box and caches it locally
                if ALLVERBOSE or VERBOSE: print "TRUE"
                return True
        if ALLVERBOSE or VERBOSE: print "FALSE"
        return False        

    def __isSubscribed_err(self,results,name):
        """LSUB failed - print results for debugging purposes - return False"""
        if ALLVERBOSE or VERBOSE:
            print "ImapProxyAccount.isSubscribed_err(%s)" % name
            results
        return False        
    
    def subscribe(self,name):
        """Subscribe to a mailbox

        @type name: C{str}
        @param name: The name of the mailbox to subscribe to

        @rtype: C{Deferred} or C{bool}
        @return: A true value if the mailbox is subscribed to successfully,
        or a Deferred whose callback will be invoked with this value when
        the subscription is successful.

        @raise MailboxException: Raised if this mailbox cannot be
        subscribed to.  This may also be raised asynchronously, if a
        C{Deferred} is returned.
        """
        if ALLVERBOSE or VERBOSE: print "ImapProxyAccount.subscribe(%s)" % name
        d = self.server.protocol.subscribe(name)
        d.addCallback(self.__subscribe_cb,name)
        d.addErrback(self.__subscribe_err,name)
        return d
    
    def __subscribe_cb(self,result,name):
        "deferred SUBSCRIBE cmd succeeds - records proxy subscription - returns False" 
        if ALLVERBOSE or VERBOSE:
            print "ImapProxyAccount.__subscribe_cb('%s')" % name
            print result
        if not self.server.subscribed.count(name): self.server.subscribed.append(name)
        if ALLVERBOSE or VERBOSE: print self.server.subscribed
        return True

    def __subscribe_err(self,result,name):
        "deferred SUBSCRIBE cmd fails - makes sure proxy shows not subscribed - returns False" 
        if ALLVERBOSE or VERBOSE:
            print "ImapProxyAccount.__subscribe_err('%s')" % name
            print result
        for i in range(self.server.subscribed.count(name)):
            self.server.subscribed.remove(name)
        raise imap4.MailboxException("Subrcribe failed for mailbox: %s" % name)

    def unsubscribe(self,name):
        """Unsubscribe from a mailbox

        @type name: C{str}
        @param name: The name of the mailbox to unsubscribe from

        @rtype: C{Deferred} or C{bool}
        @return: A true value if the mailbox is unsubscribed from successfully,
        or a Deferred whose callback will be invoked with this value when
        the unsubscription is successful.

        @raise MailboxException: Raised if this mailbox cannot be
        unsubscribed from.  This may also be raised asynchronously, if a
        C{Deferred} is returned.
        """
        if ALLVERBOSE or VERBOSE: print "ImapProxyAccount.unsubscribe"
        #unsubscribe from proxy cache
        for i in range(self.server.subscribed.count(name)):
            self.server.subscribed.remove(name)
        #unsubscribe from server
        d = self.server.protocol.unsubscribe(name)
        d.addCallback(self.__unsubscribe_cb,name)
        d.addErrback(self.__unsubscribe_err,name)
        return d

    def __unsubscribe_cb(self,result,name):
        "deffered UNSUBSCRIBE cmd succeeds - remove from proxy subscribed list - return True"
        if ALLVERBOSE or VERBOSE:
            print "ImapProxyAccount.__unsubscribe_cb('%s')" % name
            print result
        return True

    def __unsubscribe_err(self,result,name):
        "deffered UNSUBSCRIBE cmd fails - raise exception"
        if ALLVERBOSE or VERBOSE:
            print "ImapProxyAccount.__unsubscribe_err('%s')" % name
            print result
        #raise exception with server results
        raise imap4.MailboxException("Unsubscribe failed for mailbox '%s'" % name)
    
    def listMailboxes(self,ref, wildcard):
        """List all the mailboxes that meet a certain criteria

        @type ref: C{str}
        @param ref: The context in which to apply the wildcard

        @type wildcard: C{str}
        @param wildcard: An expression against which to match mailbox names.
        '*' matches any number of characters in a mailbox name, and '%'
        matches similarly, but will not match across hierarchical boundaries.

        @rtype: C{list} of C{tuple}
        @return: A list of C{(mailboxName, mailboxObject)} which meet the
        given criteria.  C{mailboxObject} should implement either
        C{IMailboxInfo} or C{IMailbox}.  A Deferred may also be returned.
        """
        if ALLVERBOSE or VERBOSE:
            print "ImapProxyAccount.listMailboxes('%s','%s')" % (ref, wildcard)
        d = self.server.protocol.list(ref,wildcard)
        d.addCallback(self.__listMailboxes_cb,ref,wildcard)
        return d
    
    def __listMailboxes_cb(self, results, ref, wildcard):
        "returns list of two_tuples (maibox name,proxy mailbox object)"
        if ALLVERBOSE or VERBOSE:
            print "ImapProxyAccount.__listMailboxes_cb('%s','%s')" % (ref,wildcard)
            print results
        #results come in as a list of lists - each row contains several mailbox parameters
        #boxinfo[2] is the mailbox name/path
        return_list = []
        for boxinfo in results:
            name = boxinfo[2] 
            box = self._getBox(boxinfo) #creates box and caches it locally
            two_tuple = (name,box)
            return_list.append(two_tuple)
        return return_list
   
    def _getBox(self,boxinfo):
        """
        Returns box from cache OR creates it + adds it to cache + returns it
        If boxinfo is a string - box of given path/name is returned from cache.
        If boxinfo is a tupple or dict with attributes and box doesn't exist, it
        is created, cached, and returned - if it exists it is updated and returned.
        """
        if ALLVERBOSE or VERBOSE: print "ImapProxyAccount._getBox"  
        if isinstance(boxinfo,str): #box name/path only as str
            if ALLVERBOSE or VERBOSE: print boxinfo
            return self.server.mailboxCache[boxinfo]
        if isinstance(boxinfo,tuple): #partial info as tupple from LIST command
            boxname = boxinfo[2] #path string
        elif isinstance(boxinfo,dict): #full info as dict from SELECT command
            boxname = boxinfo['PATH']
        else: #unknown type
            raise TypeError("unknown mailbox info type")
        if ALLVERBOSE or VERBOSE:
            print boxname
            print boxinfo
        #If new box create - if old box update - then return box object
        if not self.server.mailboxCache.has_key(boxname):
            self.server.mailboxCache[boxname] = ImapProxyMailbox(boxinfo,self.server)
        else:
            self.server.mailboxCache[boxname].updateInfo(boxinfo)
        return self.server.mailboxCache[boxname]
