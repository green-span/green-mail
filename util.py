from pyparsing import Forward, Literal, oneOf, OneOrMore, Optional, ParserElement, Regex, ZeroOrMore

_rfc2822 = None
def rfc2822():
    global _rfc2822
    if _rfc2822 is None:
        ParserElement.setDefaultWhitespaceChars("")
        
        CRLF = Literal("\r\n")
        ATEXT = Regex("[a-zA-Z0-9!#$%&'*+\-/=\?^_`{|}~]")
        TEXT = Regex("[\x01-\x09\x0b\x0c\x0e-\x7f]")
        QTEXT = Regex("[\x01-\x08\x0b\x0c\x0d-\x1f\x21\x23-\x5b\x5d-\x7f]")
        LOWASCII = Regex("[\x00-\x7f]")
        DTEXT = Regex("[\x01-\x08\x0b\x0c\x0e-\x1f\x21-\x5a\x5e-\x7f]")
        WSP = Regex("[\x20\x09]")
        CTEXT = Regex("[\x01-\x08\x0b\x0c\x0e-\x1f\x21-\x27\x2a-\x5b\x5d-\x7f]")

        obsQp = r"\\" + LOWASCII
        quotedPair = (r"\\" + TEXT) | obsQp

        obsFWS = OneOrMore(WSP) + ZeroOrMore(CRLF + OneOrMore(WSP))
        FWS = (Optional(ZeroOrMore(WSP) + CRLF) + OneOrMore(WSP)) | obsFWS
        comment = Forward()
        ccontent = CTEXT | quotedPair | comment
        comment << "(" + ZeroOrMore(Optional(FWS) + ccontent) + Optional(FWS) + ")"
        CFWS = ZeroOrMore(Optional(FWS) + comment) + ((Optional(FWS) + comment) | FWS)

        atom = Optional(CFWS) + OneOrMore(ATEXT) + Optional(CFWS)
        dotAtomText = OneOrMore(ATEXT) + ZeroOrMore("." + OneOrMore(ATEXT))
        dotAtom = Optional(CFWS) + dotAtomText + Optional(CFWS)

        qcontent = QTEXT | quotedPair
        quotedString = Optional(CFWS) + '"' + ZeroOrMore(Optional(FWS) + qcontent) + Optional(FWS) + '"'

        word = atom | quotedString
        obsLocalPart = word + ZeroOrMore("." + word)

        localPart = dotAtom | quotedString | obsLocalPart

        dcontent = DTEXT | quotedPair
        domainLiteral = Optional(CFWS) + "[" + ZeroOrMore(Optional(FWS) + dcontent) + Optional(FWS) + "]" + Optional(CFWS)

        obsDomain = atom + ZeroOrMore("." + atom)

        domain = dotAtom | domainLiteral | obsDomain

        addrSpec = localPart + "@" + domain
        _rfc2822 = addrSpec
    return _rfc2822


def validateAddress(addr):
    try:
        parsed = rfc2822().parseString(addr)
        if parsed is not None:
            return True
    except:
        return False

