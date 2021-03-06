#
# [The "BSD license"]
#  Copyright (c) 2012 Terence Parr
#  Copyright (c) 2012 Sam Harwell
#  All rights reserved.
#
# Copyright (C) 2015 OLogN Technologies AG
#
#  Redistribution and use in source and binary forms, with or without
#  modification, are permitted provided that the following conditions
#  are met:
#
#  1. Redistributions of source code must retain the above copyright
#     notice, this list of conditions and the following disclaimer.
#  2. Redistributions in binary form must reproduce the above copyright
#     notice, this list of conditions and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#  3. The name of the author may not be used to endorse or promote products
#     derived from this software without specific prior written permission.
#
#  THIS SOFTWARE IS PROVIDED BY THE AUTHOR ``AS IS'' AND ANY EXPRESS OR
#  IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES
#  OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
#  IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY DIRECT, INDIRECT,
#  INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT
#  NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
#  DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
#  THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
#  (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF
#  THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#

from io import StringIO

from antlr4.Token import Token


#
# Useful for rewriting out a buffered input token stream after doing some
# augmentation or other manipulations on it.
#
# <p>
# You can insert stuff, replace, and delete chunks. Note that the operations
# are done lazily--only if you convert the buffer to a {@link String} with
# {@link TokenStream#getText()}. This is very efficient because you are not
# moving data around all the time. As the buffer of tokens is converted to
# strings, the {@link #getText()} method(s) scan the input token stream and
# check to see if there is an operation at the current index. If so, the
# operation is done and then normal {@link String} rendering continues on the
# buffer. This is like having multiple Turing machine instruction streams
# (programs) operating on a single input tape. :)</p>
#
# <p>
# This rewriter makes no modifications to the token stream. It does not ask the
# stream to fill itself up nor does it advance the input cursor. The token
# stream {@link TokenStream#index()} will return the same value before and
# after any {@link #getText()} call.</p>
#
# <p>
# The rewriter only works on tokens that you have in the buffer and ignores the
# current input cursor. If you are buffering tokens on-demand, calling
# {@link #getText()} halfway through the input will only do rewrites for those
# tokens in the first half of the file.</p>
#
# <p>
# Since the operations are done lazily at {@link #getText}-time, operations do
# not screw up the token index values. That is, an insert operation at token
# index {@code i} does not change the index values for tokens
# {@code i}+1..n-1.</p>
#
# <p>
# Because operations never actually alter the buffer, you may always get the
# original token stream back without undoing anything. Since the instructions
# are queued up, you can easily simulate transactions and roll back any changes
# if there is an error just by removing instructions. For example,</p>
#
# <pre>
# CharStream input = new ANTLRFileStream("input");
# TLexer lex = new TLexer(input);
# CommonTokenStream tokens = new CommonTokenStream(lex);
# T parser = new T(tokens);
# TokenStreamRewriter rewriter = new TokenStreamRewriter(tokens);
# parser.startRule();
# </pre>
#
# <p>
# Then in the rules, you can execute (assuming rewriter is visible):</p>
#
# <pre>
# Token t,u;
# ...
# rewriter.insertAfter(t, "text to put after t");}
# rewriter.insertAfter(u, "text after u");}
# System.out.println(rewriter.getText());
# </pre>
#
# <p>
# You can also have multiple "instruction streams" and get multiple rewrites
# from a single pass over the input. Just name the instruction streams and use
# that name again when printing the buffer. This could be useful for generating
# a C file and also its header file--all from the same buffer:</p>
#
# <pre>
# rewriter.insertAfter("pass1", t, "text to put after t");}
# rewriter.insertAfter("pass2", u, "text after u");}
# System.out.println(rewriter.getText("pass1"));
# System.out.println(rewriter.getText("pass2"));
# </pre>
#
# <p>
# If you don't use named rewrite streams, a "default" stream is used as the
# first example shows.</p>
#
class TokenStreamRewriter(object):

    class RewriteOperation(object):
        '''
        Define the rewrite operation hierarchy
        '''
        pass

    class InsertBeforeOp(RewriteOperation):

        def __init__(self, index, text):
            self.index = index
            self.text = text

        # Override
        def execute(self, buf, tokens):
            buf.write(self.text)
            if tokens.get(self.index).type != Token.EOF:
                buf.write(tokens.get(self.index).text)

            return self.index + 1

        def __str__(self):
            '''
            String representation
            '''
            return "I.%s.'%s'" % (self.index, self.text)

    # I'm going to try replacing range from x..y with (y-x)+1 ReplaceOp
    # instructions.
    #
    class ReplaceOp(RewriteOperation):

        def __init__(self, _from, to, text):
            self.index = _from
            self.text = text
            self.lastIndex = to

        # Override
        def execute(self, buf, tokens):
            # pylint: disable=unused-argument
            if self.text is not None:
                buf.write(self.text)

            return self.lastIndex + 1

        def __str__(self):
            '''
            String representation
            '''
            if self.index == self.lastIndex:
                return "R.%s.'%s'" % (self.index, self.text)
            else:
                return "R.%s-%s.'%s'" % (self.index, self.lastIndex, self.text)

    def __init__(self, tokens):
        self.tokens = tokens
        self.rewrites = []

    def _add_op(self, op):
        self.rewrites.append(op)

    def _get_token_size(self):
        return len(self.tokens.tokens)

    def insertAfterToken(self, t, text):
        self.insertAfter(t.tokenIndex, text)

    def insertAfter(self, index, text):
        # to insert after, just insert before next index (even if past end)
        self.insertBefore(index + 1, text)

    def insertBeforeToken(self, t, text):
        self.insertBefore(t.tokenIndex, text)

    def insertBefore(self, index, text):
        op = TokenStreamRewriter.InsertBeforeOp(index, text)
        self._add_op(op)

    def replace(self, _from, to, text):
        if _from > to or _from < 0 or to < 0 or to >= self._get_token_size():
            raise RuntimeError(
                "replace: range invalid: %d..%d(size=%d)" % (
                    _from, to, self._get_token_size()))

        op = TokenStreamRewriter.ReplaceOp(_from, to, text)
        self._add_op(op)

    def replaceToken(self, tk, text):
        self.replace(tk.tokenIndex, tk.tokenIndex, text)

    def replaceTokens(self, _from, to, text):
        self.replace(_from.tokenIndex, to.tokenIndex, text)

    def delete(self, _from, to):
        self.replace(_from, to, None)

    def deleteTokens(self, _from, to):
        self.replaceTokens(_from, to, None)

    def getText(self):
        '''
        Return the text from the original tokens altered per the
        instructions given to this rewriter in programName.
        '''
        return self._getIntervalText(0, self._get_token_size() - 1)

    def getIntervalText(self, start, stop):
        '''
        Use tokens instead of plain indexes
        '''
        return self._getIntervalText(start.tokenIndex, stop.tokenIndex)

    def _getIntervalText(self, start, stop):
        '''
        Return the text associated with the tokens in the interval from the
        original token stream but with the alterations given to this rewriter.
        The interval refers to the indexes in the original token stream.
        We do not alter the token stream in any way, so the indexes
        and intervals are still consistent. Includes any operations done
        to the first and last token in the interval. So, if you did an
        insertBefore on the first token, you would get that insertion.
        The same is true if you do an insertAfter the stop token.
        '''

        # ensure start/end are in range
        if stop > self._get_token_size() - 1:
            stop = self._get_token_size() - 1
        if start < 0:
            start = 0

        if len(self.rewrites) == 0:
            interval = (start, stop)
            return self.tokens.getText(interval)  # no instructions to execute

        buf = StringIO()

        # First, optimize instruction stream
        _reduceToSingleOperationPerIndex(self.rewrites)

        indexToOp = {}
        for op in self.rewrites:
            if op is not None:
                # should only be one op per index
                assert op.index not in indexToOp
                indexToOp[op.index] = op

        # Walk buffer, executing instructions and emitting tokens
        i = start
        while i <= stop and i < self._get_token_size():
            if i in indexToOp:
                op = indexToOp[i]
                del indexToOp[i]  # remove so any left have index size-1
                # execute operation and skip
                i = op.execute(buf, self.tokens)
            else:
                # no operation at that index, just dump token
                t = self.tokens.get(i)
                if t.type != Token.EOF:
                    buf.write(t.text)
                i += 1  # move to next token

        # include stuff after end if it's last index in buffer
        # So, if they did an insertAfter(lastValidIndex, "foo"), include
        # foo if end==lastValidIndex.
        if stop == self._get_token_size() - 1:
            # Scan any remaining operations after last token
            # should be included (they will be inserts).
            for op in indexToOp.values():
                if op.index >= self._get_token_size() - 1:
                    buf.write(op.text)

        return buf.getvalue()


def _reduceToSingleOperationPerIndex(rewrites):
    '''
    We need to combine operations and report invalid operations (like
    overlapping replaces that are not completed nested). Inserts to
    same index need to be combined etc...  Here are the cases:

    I.i.u I.j.v                                leave alone, nonoverlapping
    I.i.u I.i.v                                combine: Iiuv

    R.i-j.u R.x-y.v    | i-j in x-y            delete first R
    R.i-j.u R.i-j.v                            delete first R
    R.i-j.u R.x-y.v    | x-y in i-j            ERROR
    R.i-j.u R.x-y.v    | boundaries overlap    ERROR

    Delete special case of replace (text==null):
    D.i-j.u D.x-y.v    | boundaries overlap    combine to max(min)..max(right)

    I.i.u R.x-y.v | i in (x+1)-y            delete I (since insert before
                                                we're not deleting i)
    I.i.u R.x-y.v | i not in (x+1)-y        leave alone, nonoverlapping
    R.x-y.v I.i.u | i in x-y                ERROR
    R.x-y.v I.x.u                             R.x-y.uv (combine, delete I)
    R.x-y.v I.i.u | i not in x-y            leave alone, nonoverlapping

    I.i.u = insert u before op @ index i
    R.x-y.u = replace x-y indexed tokens with u

    First we need to examine replaces. For any replace op:

    1. wipe out any insertions before op within that range.
    2. Drop any replace op before that is contained completely within
        that range.
    3. Throw exception upon boundary overlap with any previous replace.

     Then we can deal with inserts:

    1. for any inserts to same index, combine even if not adjacent.
    2. for any prior replace with same left boundary, combine this
        insert with replace and delete this replace.
    3. throw exception if index in same range as previous replace

    Don't actually delete; make op null in list. Easier to walk list.
    Later we can throw as we add to index &rarr; op map.

    Note that I.2 R.2-2 will wipe out I.2 even though, technically, the
    inserted stuff would be before the replace range. But, if you
    add tokens in front of a method body '{' and then delete the method
    body, I think the stuff before the '{' you added should disappear too.

    Return a map from token index to operation.
    '''
    # pylint: disable=too-many-branches

    # System.out.println("rewrites="+rewrites);

    # WALK REPLACES
    for i in _getReplaceOps(rewrites, len(rewrites)):

        rop = rewrites[i]
        # Wipe prior inserts within range
        for iopi in _getInsertBeforeOps(rewrites, i):
            iop = rewrites[iopi]
            if iop.index == rop.index:
                # E.g., insert before 2, delete 2..2; update replace
                # text to include insert before, kill insert
                rop.text = iop.text + \
                    (rop.text if rop.text is not None else "")
                rewrites[iopi] = None

            elif iop.index > rop.index and iop.index <= rop.lastIndex:
                # delete insert as it's a no-op.
                rewrites[iopi] = None

        # Drop any prior replaces contained within
        for prevRopi in _getReplaceOps(rewrites, i):
            prevRop = rewrites[prevRopi]
            if (prevRop.index >= rop.index and
                    prevRop.lastIndex <= rop.lastIndex):
                # delete replace as it's a no-op.
                rewrites[prevRopi] = None
                continue

            # throw exception unless disjoint or identical
            disjoint = (
                prevRop.lastIndex < rop.index or
                prevRop.index > rop.lastIndex)

            same = (
                prevRop.index == rop.index and
                prevRop.lastIndex == rop.lastIndex)

            # Delete special case of replace (text==null):
            # D.i-j.u D.x-y.v | boundaries overlap    combine to
            # max(min)..max(right)
            if prevRop.text is None and rop.text is None and not disjoint:
                # System.out.println("overlapping deletes: "+prevRop+", "+rop);
                # kill first delete
                rop.index = min(prevRop.index, rop.index)
                rop.lastIndex = max(prevRop.lastIndex, rop.lastIndex)
                # print "new rop " + rop
                rewrites[prevRopi] = None

            elif not disjoint and not same:
                raise RuntimeError(
                    "replace op boundaries of %s overlap with previous %s" % (
                        rop, prevRop))

    # WALK INSERTS
    for i in _getInsertBeforeOps(rewrites, len(rewrites)):
        iop = rewrites[i]
        # combine current insert with prior if any at same index
        for prevIopi in _getInsertBeforeOps(rewrites, i):
            prevIop = rewrites[prevIopi]
            if prevIop.index == iop.index:  # combine objects
                # convert to strings...we're in process of toString'ing
                # whole token buffer so no lazy eval issue with any
                # templates
                iop.text = _catOpText(prevIop.text, iop.text)
                # delete redundant prior insert
                rewrites[prevIopi] = None

        # look for replaces where iop.index is in range; error
        for ropi in _getReplaceOps(rewrites, i):
            rop = rewrites[ropi]
            if iop.index == rop.index:
                rop.text = _catOpText(iop.text, rop.text)
                rewrites[i] = None  # delete current insert
                continue

            if iop.index >= rop.index and iop.index <= rop.lastIndex:
                raise RuntimeError(
                    "insert op %s within boundaries of previous %s" % (
                        iop, rop))

    # System.out.println("rewrites after="+rewrites);
    result = []
    for op in rewrites:
        if op is not None:
            result.append(op)

    return result


def _catOpText(a, b):
    x = a if a is not None else ""
    y = b if b is not None else ""

    return x + y

# Get all operations before an index of a particular kind


def _getReplaceOps(rewrites, before):
    return _getKindOfOps(rewrites, TokenStreamRewriter.ReplaceOp, before)


def _getInsertBeforeOps(rewrites, before):
    return _getKindOfOps(rewrites, TokenStreamRewriter.InsertBeforeOp,
                         before)


def _getKindOfOps(rewrites, kind, before):
    ops = []
    for i in range(0, min(before, len(rewrites))):
        op = rewrites[i]
        # pylint: disable=unidiomatic-typecheck
        if op is not None and type(op) == kind:  # ignore deleted
            ops.append(i)

    return ops
