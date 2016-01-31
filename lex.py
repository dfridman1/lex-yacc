# *** LEXER ***



import inspect
import sys
from functools import partial
from collections import namedtuple
import re
from utils import get_global_vars, filter_variables, by_appearance, categorize, for_all, for_any








class LexToken(object):
    def __init__(self):
        self.lineno = self.pos = 0
        self.is_error = False

    def __str__(self):
        return "LexToken(%s, %r, %d, %d)" % (self.type,
                                             self.value,
                                             self.lineno,
                                             self.pos)


class LexError(object):
    def __init__(self):
        self.lineno = self.pos = 0
        self.is_error = True

    def __str__(self):
        return "LexError(%r, %r, %d, %d)" % (self.error_msg,
                                             self.value,
                                             self.lineno,
                                             self.pos)



class LexState(object):
    def __init__(self,
                 ignore=None,
                 rules=None,
                 error=None,
                 type=None):
        self.ignore = ignore
        self.rules = [] if (rules is None) else rules
        self.error = error
        self.type = type



def get_state_name(state):
    name, _ = state
    return name


def get_state_mode(state):
    _, mode = state
    return mode


def make_state(name, mode):
    return (name, mode)




class Lexer(object):
    def __init__(self, module=None):
        info = LexerInfo(module)

        self.token_names = info.token_names
        self.states = info.states
        self.rules_index = info.rules_index

        self.current_exclusive = self._default_state_name()
        self.current_states_names = [self._default_state_name()]

        self.current_token_rules = self._get_current_token_rules()

        self.lexpos = 0
        self.lexcol = 1
        self.lineno = 1
        self.lexdata = ""

        self.num_tokens = 0


    def _get_regexp_for_rule(self, rule):
        return rule.__doc__


    def _default_state_name(self):
        return "INITIAL"


    def begin(self, state_name):
        "Begin a new state with state_name."
        lexstate = self.states.get(state_name)
        if lexstate is None:
            raise ValueError("unknown state: %s" % state_name)
        if self._exclusive_state(lexstate):
            self.current_states_names = [state_name]
            self.current_exclusive = state_name
        else:
            self.current_states_names.append(state_name)
        self.current_token_rules = self._get_current_token_rules()  # update t_rules


    def end(self, state_name):
        "End a state with state_name. Raise error if uknown state found."
        lexstate = self.states.get(state_name)
        if lexstate is None:
            raise ValueError("unknown state: %s" % state_name)
        elif self._exclusive_state(lexstate):
            raise ValueError("cannot end an exclusive state: %s" % state_name)
        try:
            self.current_states_names.remove(state_name)
            self.current_token_rules = self._get_current_token_rules()  # update t_rules
        except ValueError:
            # may want to raise an error
            pass


    def input(self, text):
        '''Get user input for lexical analysis.'''
        self.lexdata = text


    def get_token(self):
        "Return a token generator."
        while not self._finished_analysis():
            if not self._ignored():
                token, match_obj = self._apply_token_rules()
                if match_obj is not None:
                    text_matched = match_obj.group(0)
                    self.lexpos += len(text_matched)
                    self.lexcol += len(text_matched)
                    if token is not None:
                        self.num_tokens += 1
                        yield token
                else:
                    # no rule matched
                    error_token = self._apply_error_rule()
                    if error_token is not None:
                        yield error_token


    def token(self):
        "Return the next token. None, if run out of tokens."
        tokens = self.get_token()
        try:
            return next(tokens)
        except StopIteration:
            return None


    def _finished_analysis(self):
        return self.lexpos >= len(self.lexdata)


    def _apply_error_rule(self):
        error_rule = self._get_current_error_rule()
        old_lexpos = self.lexpos
        token = self._make_default_error_token()
        error_token = error_rule(token)
        if old_lexpos == self.lexpos:
            raise ValueError('''After applying %s the lexdata stayed unchanged, which results in an infinite loop.''' % error_rule.__name__)
        return error_token


    def _apply_token_rules(self):
        for rule in self.current_token_rules:
            m = re.match(rule.regexp, self.lexdata[self.lexpos:])
            if m is not None:
                token = self._make_default_token(type=self._extract_default_token_name(rule),
                                                 value=m.group(0))
                token = rule(token)
                if token is not None and token.type not in self.token_names:
                    raise ValueError("unknown token name %s found under the rule %s" % (token.type,
                                                                                         rule.__name__))
                return token, m
        return None, None
            

    def _ignored(self):
        ch = self.lexdata[self.lexpos]
        ignore_string = self._get_regexp_for_rule(self._get_current_ignore_rule())
        if ch in ignore_string:
            self.skip()
            return True
        return False


    def skip(self, n=1):
        '''Skip n characters of the input.'''
        self.lexpos += n
        self.lexcol += n


    def incLine(self, n):
        self.lineno += n
        self.lexcol = 1


    def _get_current_token_rules(self):
        res = []
        for state_name in self.current_states_names:
            lexstate = self.states[state_name]
            for rule in lexstate.rules:
                res.append(rule)
        by_appearance = lambda rule: self.rules_index[rule]
        return sorted(res, key=by_appearance)


    def _get_current_error_rule(self):
        lexstate = self.states[self.current_exclusive]
        return lexstate.error


    def _get_current_ignore_rule(self):
        lexstate = self.states[self.current_exclusive]
        return lexstate.ignore


    def _exclusive_state(self, lexstate):
        '''Return True if a LexState is exclusive.'''
        return lexstate.type == "exclusive"


    def _make_default_token(self, type=None, value=None):
        token = LexToken()
        token.lexer, token.value, token.type = self, value, type
        token.lineno, token.pos = self.lineno, self.lexcol
        return token

    def _make_default_error_token(self, error_msg=""):
        token = LexError()
        token.lexer = self
        token.error_msg = error_msg
        token.lineno, token.pos = self.lineno, self.lexcol
        token.value = self.lexdata[self.lexpos:]
        return token


    def _extract_default_token_name(self, rule):
        '''E.g: t_NUMBER => NUMBER, t_comment_begin => begin
        if 'comment' is a valid state.'''
        return rule.default_token_name



lex = Lexer  # type alias


class LexerInfo(object):
    '''LexerInfo class is responsible for extracting all information
       required for conducting lexical analysis (ie extracting tokens,
       states, token_rules). It also preprocess the info and performs
       error handling.'''
    
    def __init__(self, module=None):
        token_names, states, rules = self.get_lexer_variables(module)
        token_names, rules = token_names[-1], map(self._convert_rule, rules)
        states = states[-1] if states else []

        self._check_token_state_names(token_names, states)
        
        self.token_names = token_names
        self.states = self._convert_to_states(states)
        self._assign_rules(rules)

        self.rules_index = {rule: i for i, rule in enumerate(rules)}

        self.check_all_rules()

        self.set_rules_regexp_and_default_name_attr()


    def get_lexer_variables(self, module=None):
        frame, variables = get_global_vars(module)
        filter_rules = [lambda x: x == "tokens",
                        lambda x: x == "states",
                        lambda x: x.startswith("t_")]
        variables = sorted(filter_variables(filter_rules, variables),
                           key=partial(by_appearance, frame))
        token_names, states, t_rules = categorize(filter_rules, variables)

        if len(token_names) == 0:
            raise SyntaxError("'tokens' (a tuple of strings) must be defined")

        token_names = token_names[0] if token_names else []
        states = states[0] if states else []
        return token_names, states, t_rules


    def _check_token_state_names(self, token_names, states):
        self._check_token_names(token_names)
        self._check_states(states)


    def _check_token_names(self, names):
        if not (isinstance(names, (tuple, list)) and for_all(lambda x: isinstance(x, str), names)):
            raise SyntaxError("'tokens' must be a tuple (list) of strings")
        if len(names) != len(set(names)):
            raise SyntaxError("duplicate tokens defined")


    def _check_states(self, states):
        def valid_pair(state):
            return (isinstance(state, (list, tuple)) and
                    len(state) == 2 and
                    for_all(lambda x: isinstance(x, str), state) and
                    state[-1] in ["inclusive", "exclusive"])

        if not (isinstance(states, (tuple, list)) and for_all(valid_pair, states)):
            raise SyntaxError(("'states' must be a tuple (list) of 2 element tuples"
                               " where each pair is of the form (state_name, state_mode)"
                               " (state_mode is either 'inclusive' or 'exclusive')"))
        state_names = map(lambda (x, _): x, states)
        if self._default_state_name() in state_names:
            raise SyntaxError("%r is an implicit default state" % self._default_state_name())
        if len(state_names) != len(set(state_names)):
            raise SyntaxError("duplicate states defined")
        
    
    def check_all_rules(self):
        self.check_rules_regexps()
        self.check_error_rules()
        self.check_ignore_rules()

        
    def _convert_to_states(self, states):
        states += (make_state(self._default_state_name(), "exclusive"),)
        return {get_state_name(state): LexState(type=get_state_mode(state))
                for state in states}

    
    def set_rules_regexp_and_default_name_attr(self):
        '''Precompile rules' regexps and sets a default_token_name attribute.'''
        for lexstate in self.states.values():
            for rule in lexstate.rules:
                rule.regexp = re.compile(self._get_regexp_for_rule(rule))
                self.set_default_token_name(rule)


    def set_default_token_name(self, rule):
        prefix = "t_"
        if rule.state_name != self._default_state_name():
            prefix += rule.state_name + "_"
        default_name = rule.__name__[len(prefix):]
        rule.default_token_name = default_name
                
                
    def check_rules_regexps(self):
        for state_name, lexstate in self.states.items():
            for rule in lexstate.rules:
                regexp, n = self._get_regexp_for_rule(rule), rule.__name__
                if regexp is None:
                    raise ValueError("regexp for %r (state: %r) must be provided" % (n, state_name))
                elif regexp == "":
                    raise ValueError("empty string regexp for %r (state: %r) is disallowed" % (n, state_name))


    def check_error_rules(self):
        for state_name, lexstate in self.states.items():
            if self._exclusive_state(lexstate) and lexstate.error is None:
                if state_name == self._default_state_name():
                    n = "t_error"
                else:
                    n = "t_" + state_name + "_error"
                t = (n, state_name)
                raise ValueError("%r must be provided for an exclusive state %r" % t)


    def check_ignore_rules(self):
        for state_name, lexstate in self.states.items():
            if self._exclusive_state(lexstate) and lexstate.ignore is None:
                if state_name == self._default_state_name():
                    n = "t_ignore"
                else:
                    n = "t_" + state_name + "_ignore"
                t = (n, state_name)
                print "WARNING: %r is not implemented for an exclusive state %r" % t

            
    def _default_state_name(self):
        return "INITIAL"


    def _get_regexp_for_rule(self, rule):
        return rule.__doc__


    def _exclusive_state(self, lexstate):
        return lexstate.type == "exclusive"


    def _assign_rules(self, rules):
        for rule in rules:
            rule_name = rule.__name__
            for state_name, lexstate in self.states.items():
                if state_name == self._default_state_name(): continue
                if not self._is_prefix(state_name, rule_name):
                    continue
                rule.state_name = state_name
                if self._is_error_rule(state_name, rule_name):
                    lexstate.error = rule
                elif self._is_ignore_rule(state_name, rule_name):
                    lexstate.ignore = rule
                else:
                    lexstate.rules.append(rule)
                break
            else:
                initial_state_name = self._default_state_name()
                initial_state = self.states[initial_state_name]
                rule.state_name = self._default_state_name()
                if self._is_error_rule(initial_state_name, rule_name):
                    initial_state.error = rule
                elif self._is_ignore_rule(initial_state_name, rule_name):
                    initial_state.ignore = rule
                else:
                    initial_state.rules.append(rule)


    def _is_prefix(self, state_name, rule_name):
        prefix = "t_" + state_name + "_"
        return rule_name.startswith(prefix)


    def _is_error_rule(self, state_name, rule_name):
        if state_name == self._default_state_name():
            return rule_name == "t_error"
        else:
            return "t_" + state_name + "_error" == rule_name


    def _is_ignore_rule(self, state_name, rule_name):
        if state_name == self._default_state_name():
            return rule_name == "t_ignore"
        else:
            return "t_" + state_name + "_ignore" == rule_name


    def _convert_rule(self, rule):
        '''If rule (name, value) is a function, return it as it is,
        otherwise convert string to a func.'''
        name, value = rule
        if callable(value): return value
        f = lambda t: t
        f.__name__, f.__doc__ = name, value
        return f
