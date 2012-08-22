
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

from twisted.internet import defer
from twisted.cred import checkers, credentials, error as crederror
from zope.interface import implements

class CredentialsChecker(object):
    implements(checkers.ICredentialsChecker)
    
    credentialInterfaces = [credentials.IUsernamePassword,credentials.IUsernameHashedPassword]
    
    def __init__(self, passwords):
        if ALLVERBOSE or VERBOSE:
            print "CredentialsChecker.__init__"
            print passwords
        self.passwords = passwords #a dictionary mapping UID to PWD
        
    def __getattribute__(self, name):
        #this is for debugging purposes - allows print out of all attribute calls
        return_object = object.__getattribute__(self, name)
        if ALLVERBOSE or VERBOSE:
            print "CredentialsChecker.__getattribute__(%s)" % name
            print return_object
        return return_object
        
    def requestAvatarId(self, credentials):
        """
        @param credentials: something which implements one of the interfaces in
        self.credentialInterfaces.

        @return: a Deferred which will fire a string which identifies an
        avatar, an empty tuple to specify an authenticated anonymous user
        (provided as checkers.ANONYMOUS) or fire a Failure(UnauthorizedLogin).
        Alternatively, return the result itself.

        @see: L{twisted.cred.credentials}
        """
        if ALLVERBOSE or VERBOSE: print "CredentialsChecker.requestAvatarId"
        username = credentials.username
        given_password = credentials.password
        if ALLVERBOSE or VERBOSE: print username , given_password        
        if self.passwords.has_key(username):
            correct_password = self.passwords[username]
            checking = defer.maybeDeferred(credentials.checkPassword,correct_password)
            uidpwd = username + ":" + given_password
            checking.addCallback(self._checkedPassword, uidpwd)
            return checking
        else:
            raise crederror.UnauthorizedLogin("No such user")
        
    def _checkedPassword(self, matched, uidpwd):
        if ALLVERBOSE or VERBOSE: print "CredentialsChecker._checkPassword:"
        if matched:
            if ALLVERBOSE or VERBOSE: print "credentials matched"            
            return uidpwd
        else:
            raise crederror.UnauthorizedLogin("Bad Password")
        