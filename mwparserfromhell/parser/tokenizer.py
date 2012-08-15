# -*- coding: utf-8  -*-
#
# Copyright (C) 2012 Ben Kurtovic <ben.kurtovic@verizon.net>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from . import contexts
from . import tokens

__all__ = ["Tokenizer"]

class BadRoute(Exception):
    pass

class Tokenizer(object):
    START = object()
    END = object()

    def __init__(self):
        self._text = None
        self._head = 0
        self._stacks = []
        self._context = 0

    def _push(self):
        self._stacks.append([])

    def _pop(self):
        return self._stacks.pop()

    def _write(self, token, stack=None):
        if stack is None:
            stack = self._stacks[-1]
        if not stack:
            stack.append(token)
            return
        last = stack[-1]
        if isinstance(token, tokens.Text) and isinstance(last, tokens.Text):
            last.text += token.text
        else:
            stack.append(token)

    def _read(self, delta=0, wrap=False):
        index = self._head + delta
        if index < 0 and (not wrap or abs(index) > len(self._text)):
            return self.START
        if index >= len(self._text):
            return self.END
        return self._text[index]

    def _verify_context(self):
        if self._read() is self.END:
            if self._context & contexts.TEMPLATE:
                raise BadRoute()

    def _catch_stop(self, stop):
        if self._read() is self.END:
            return True
        try:
            iter(stop)
        except TypeError:
            if self._read() is stop:
                return True
        else:
            if all([self._read(i) == stop[i] for i in xrange(len(stop))]):
                self._head += len(stop) - 1
                return True
        return False

    def _parse_template(self):
        reset = self._head
        self._head += 2
        self._context |= contexts.TEMPLATE_NAME
        try:
            template = self._parse_until("}}")
        except BadRoute:
            self._head = reset
            self._write(tokens.Text(text=self._read()))
        else:
            self._write(tokens.TemplateOpen())
            self._stacks[-1] += template
            self._write(tokens.TemplateClose())

        ending = (contexts.TEMPLATE_NAME, contexts.TEMPLATE_PARAM_KEY,
                  contexts.TEMPLATE_PARAM_VALUE)
        for context in ending:
            self._context ^= context if self._context & context else 0

    def _parse_until(self, stop):
        self._push()
        while True:
            self._verify_context()
            if self._catch_stop(stop):
                return self._pop()
            if self._read(0) == "{" and self._read(1) == "{":
                self._parse_template()
            elif self._read(0) == "|" and self._context & contexts.TEMPLATE:
                if self._context & contexts.TEMPLATE_NAME:
                    self._context ^= contexts.TEMPLATE_NAME
                if self._context & contexts.TEMPLATE_PARAM_VALUE:
                    self._context ^= contexts.TEMPLATE_PARAM_VALUE
                self._context |= contexts.TEMPLATE_PARAM_KEY
                self._write(tokens.TemplateParamSeparator())
            else:
                self._write(tokens.Text(text=self._read()))
            self._head += 1

    def tokenize(self, text):
        self._text = list(text)
        return self._parse_until(stop=self.END)
