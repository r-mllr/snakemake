# -*- coding: utf-8 -*-

import tokenize
import textwrap
from itertools import chain


__author__ = "Johannes Köster"


dd = textwrap.dedent


def is_newline(token, newline_tokens=set((tokenize.NEWLINE, tokenize.NL))):
    return token.type in newline_tokens


def is_indent(token):
    return token.type == tokenize.INDENT


def is_dedent(token):
    return token.type == tokenize.DEDENT


def is_greater(token):
    return token.type == tokenize.OP and token.string == ">"


def is_name(token):
    return token.type == tokenize.NAME


def is_colon(token):
    return token.string == ":"


def is_comment(token):
    return token.type == tokenize.COMMENT


def is_string(token):
    return token.type == tokenize.STRING


def lineno(token):
    return token.start[0]


class StopAutomaton(Exception):

    def __init__(self, token):
        self.token = token


class TokenAutomaton:

    subautomata = dict()

    def __init__(self, tokenizer, base_indent=0):
        self.tokenizer = tokenizer
        self.state = None
        self.base_indent = base_indent
        self.indent = 0
        self.lasttoken = None

    def indentation(self, token):
        if is_indent(token) or is_dedent(token):
            self.indent = token.end[1] - self.base_indent

    def consume(self):
        
        for token in self.tokenizer:
            self.indentation(token)
            for t, orig in self.state(token):
                if self.lasttoken == "\n" and not t.isspace():
                    yield " " * (self.base_indent + self.indent), orig
                yield t, orig
                self.lasttoken = t

    def error(self, msg, token):
        raise SyntaxError(msg,
            (self.tokenizer.path, lineno(token), None, None))

    def subautomaton(self, automaton, *args, **kwargs):
        return self.subautomata[automaton](
            self.tokenizer,
            *args,
            base_indent= self.base_indent + self.indent,
            **kwargs)


class KeywordState(TokenAutomaton):

    def __init__(self, tokenizer, base_indent=0):
        super().__init__(tokenizer, base_indent=base_indent)
        self.line = 0
        self.state = self.colon

    @property
    def keyword(self):
        return self.__class__.__name__.lower()

    def end(self):
        yield ")"

    def colon(self, token):
        if is_colon(token):
            self.state = self.block
            for t in self.start():
                yield t, token
        else:
            self.error(
                "Colon expected after keyword {}.".format(self.keyword),
                token)

    def block(self, token):
        if self.line and self.indent <= 0:
            for t in self.end():
                yield t, token
            yield "\n", token
            raise StopAutomaton(token)

        if is_newline(token):
            self.line += 1
            yield token.string, token
        elif is_indent(token) or is_dedent(token):
            yield self.yield_indent(token)
        else:
            for t in self.block_content(token):
                yield t

    def yield_indent(self, token):
        return token.string, token

    def block_content(self, token):
        yield token.string, token


class GlobalKeywordState(KeywordState):

    def start(self):
        yield "workflow.{keyword}(".format(keyword=self.keyword)


class RuleKeywordState(KeywordState):

    def __init__(self, tokenizer, base_indent=0, rulename=None):
        super().__init__(tokenizer, base_indent=base_indent)
        self.rulename = rulename

    def start(self):
        yield "\n"
        yield "@workflow.{keyword}(".format(keyword=self.keyword)


# Global keyword states


class Include(GlobalKeywordState):
    pass


class Workdir(GlobalKeywordState):
    pass


class Ruleorder(GlobalKeywordState):

    def block_content(self, token):
        if is_greater(token):
            yield ",", token
        elif is_name(token):
            yield '"{}"'.format(token.string), token
        else:
            self.error('Expected a descending order of rule names, '
                'e.g. rule1 > rule2 > rule3 ...', token)


# Rule keyword states


class Input(RuleKeywordState):
    pass


class Output(RuleKeywordState):
    pass


class Params(RuleKeywordState):
    pass


class Threads(RuleKeywordState):
    pass


class Priority(RuleKeywordState):
    pass


class Version(RuleKeywordState):
    pass


class Log(RuleKeywordState):
    pass


class Message(RuleKeywordState):
    pass


class Run(RuleKeywordState):

    def __init__(self, tokenizer, rulename, base_indent=0):
        super().__init__(tokenizer, base_indent=base_indent)
        self.rulename = rulename

    def start(self):
        yield "@workflow.run"
        yield "\n"
        yield ("def __{rulename}(input, output, params, wildcards, threads, "
            "log):".format(rulename=self.rulename))

    def end(self):
        yield ""


class Shell(Run):

    def __init__(self, tokenizer, rulename, base_indent=0):
        super().__init__(tokenizer, rulename, base_indent=base_indent)
        self.shellcmd = list()

    def start(self):
        yield "@workflow.shellcmd("

    def end(self):
        yield ")"
        yield "\n"
        for t in super().start():
            yield t
        yield "\n"
        yield "\t"
        yield "shell("
        for t in self.shellcmd:
            yield t
        yield ")"
        for t in super().end():
            yield t

    def block_content(self, token):
        self.shellcmd.append(token.string)
        yield token.string, token


class Rule(GlobalKeywordState):
    subautomata = dict(
        input=Input,
        output=Output,
        params=Params,
        threads=Threads,
        priority=Priority,
        version=Version,
        log=Log,
        message=Message,
        run=Run,
        shell=Shell)

    def __init__(self, tokenizer, base_indent=0):
        super().__init__(tokenizer, base_indent=base_indent)
        self.state = self.name
        self.rulename = None
        self.lineno = None
        self.run = False

    def start(self):
        yield ("@workflow.rule(name='{rulename}', lineno={lineno}, "
            "snakefile='{snakefile}')".format(
                rulename=self.rulename,
                lineno=self.lineno,
                snakefile=self.tokenizer.path))

    def end(self):
        if not self.run:
            for t in self.subautomaton("run", rulename=self.rulename).start():
                yield t
            yield "\n"
            yield "\t"
            yield "pass"

    def name(self, token):
        if is_name(token):
            self.rulename = token.string
        elif is_colon(token):
            self.lineno = lineno(token)
            self.state = self.block
            for t in self.start():
                yield t, token
        else:
            self.error("Expected name or colon after rule keyword.", token)

    def block_content(self, token):
        if is_name(token):
            try:
                if token.string == "run" or token.string == "shell":
                    self.run = True
                for t in self.subautomaton(
                    token.string,
                    rulename=self.rulename).consume():
                    yield t
            except KeyError:
                self.error("Unexpected keyword {} in "
                    "rule definition".format(token.string), token)
            except StopAutomaton as e:
                self.indentation(e.token)
                for t in self.block(e.token):
                    yield t
        elif is_comment(token):
            yield token.string, token
        elif is_string(token):
            yield "\n", token
            yield "@workflow.docstring({})".format(token.string), token
        else:
            self.error("Expecting rule keyword, comment or docstrings "
                "inside a rule definition.", token)

class Python(TokenAutomaton):

    subautomata = dict(
        include=Include,
        workdir=Workdir,
        ruleorder=Ruleorder,
        rule=Rule)

    def __init__(self, tokenizer, base_indent=0):
        super().__init__(tokenizer, base_indent=base_indent)
        self.state = self.python

    def python(self, token):
        try:
            for t in self.subautomaton(token.string).consume():
                yield t
        except KeyError:
            yield token.string, token
        except StopAutomaton as e:
            self.indentation(e.token)
            for t in self.python(e.token):
                yield t


class Tokenizer:

    def __init__(self, path):
        self.path = path
        self.file = open(self.path)
        self.tokens = tokenize.generate_tokens(self.file.readline)

    def __next__(self):
        return next(self.tokens)

    def __iter__(self):
        return self

    def __exit__(self):
        self.file.close()


def format_tokens(tokens):
    t_ = None
    for t in tokens:
        if t_ and not t.isspace() and not t_.isspace():
            yield " "
        yield t
        t_ = t

def parse(path):
    tokenizer = Tokenizer(path)
    automaton = Python(tokenizer)
    linemap = dict()
    compilation = list()
    lines = 1
    for t, orig_token in automaton.consume():
        l = lineno(orig_token)
        linemap.update(
            dict((i, l) for i in range(lines, lines + t.count("\n"))))
        lines += t.count("\n")
        compilation.append(t)
    print(compilation)
    compilation = "".join(format_tokens(compilation))
    print(compilation)
    return compilation, linemap