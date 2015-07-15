# *** PARSER ***



import sys
from functools import partial
from collections import defaultdict
from lex import LexToken
from utils import (get_global_vars,
                   by_appearance,
                   filter_variables,
                   categorize,
                   split,
                   memo)





EPSILON = "EPSILON_TRANSITION_DUMMY"


def is_epsilon_transition(tok_name):
    return tok_name == EPSILON




class Yacc(object):
    def __init__(self, parser="EARLEY", module=None):
        self.parser = self._get_parser(parser)(module)

    def _get_parser(self, parser_name):
        available_parsers = {"EARLEY": EarleyParser,
                             "RD": RecursiveDescentParser}
        parser = available_parsers.get(parser_name)
        if parser is not None:
            return parser
        else:
            raise ValueError("available parsers: %s" % ", ".join(available_parsers.keys()))

    def parse(self, text, lexer, tokenfunc=None):
        return self.parser.parse(text, lexer, tokenfunc=tokenfunc)



yacc = Yacc  # type alias
        




class Grammar(object):
    def __init__(self, module=None):
        info = YaccInfo(module)
        self.start_symbol = info.production_rules[0].head
        self.token_names = info.tokens

        self.grammar = defaultdict(list)
        for rule in info.production_rules:
            self.grammar[rule.head].append(rule)




FAIL = (None, None)
            
            
class RecursiveDescentParser(Grammar):
    def __init__(self, module=None):
        Grammar.__init__(self, module)
        self.nonterminals = set(self.grammar.keys())

        
    def parse(self, text, lexer, tokenfunc=None):
        self.tokenfunc = tokenfunc or (lambda token: token.value)
        lexer.input(text)
        self.tokens = filter(lambda token: not token.is_error, lexer.get_token())
        tree, i = self.parse_atom(self.start_symbol, 0)
        if i == len(self.tokens):  # all tokens consumed
            return tree

        
    @memo
    def parse_atom(self, atom, token_num):
        alternatives = self.grammar.get(atom)
        if alternatives is not None:  # if atom is a nonterminal
            for production in alternatives:
                tree, i = self.parse_sequence(production, token_num)
                if tree is not None:
                    return tree, i
            return FAIL
        else:
            if is_epsilon_transition(atom):
                return [], token_num
            elif self.token_matched(atom, token_num):
                return self.tokenfunc(self.tokens[token_num]), token_num + 1
            else:
                return FAIL


    def parse_sequence(self, production, token_num):
        result = [None]
        for atom in production.body:
            tree, token_num = self.parse_atom(atom, token_num)
            if tree is None:
                return FAIL
            result.append(tree)
        production.yield_rule(result)
        return result[0], token_num


    def token_matched(self, token_name, token_num):
        return  (token_num < len(self.tokens) and
                token_name == self.tokens[token_num].type)




    
class EarleyParser(Grammar):
    def __init__(self, module=None):
        Grammar.__init__(self, module)
        self.chart = None


    def add_to_chart(self, state, index):
        if state not in self.chart[index]:
            self.chart[index].append(state)
            return True
        return False


    def predict(self, state, index):
        res = []
        if state.after <> ():
            productions = self.grammar.get(state.after[0])
            if productions is not None:
                res = [ChartState(head=prod.head,
                                  after=prod.body,
                                  start=index,
                                  yield_rule=prod.yield_rule)
                       for prod in productions]
        return res


    def scanning(self, state, token):
        if state.after <> () and state.after[0] == self._get_token_type(token):
            return ChartState(state.head, before=state.before + (state.after[0],),
                              after=state.after[1:], start=state.start,
                              yield_rule=state.yield_rule,
                              tree=self._process_token(state.tree, token))


    def complete(self, state):
        res = []
        if state.after == ():
            states = filter(lambda s: s.after <> () and
                            state.head == s.after[0], self.chart[state.start])
            res = [ChartState(s.head,
                              s.before + (s.after[0],),
                              s.after[1:],
                              s.start,
                              self._append_to_tree(s.tree, state),
                              s.yield_rule)
                   for s in states]
        return res
        


    def _process_token(self, tree, token):
        return tree + [self.tokenfunc(token)]


    def _append_to_tree(self, tree, state):
        state.yield_rule(state.tree)
        return tree + [state.tree[0]]


    def parse(self, text, lexer, tokenfunc=None):
        self.tokenfunc = tokenfunc or (lambda token: token.value)
        lexer.input(text)
        tokens = lexer.get_token()  # token generator
        self.chart = defaultdict(list)

        for prod in self.grammar[self.start_symbol]:
            state = ChartState(head=prod.head,
                               after=prod.body,
                               yield_rule=prod.yield_rule)
            self.add_to_chart(state, 0)

        tokens = filter(lambda t: not t.is_error, tokens)

        index = -1
        for index, token in enumerate(tokens):
            self._update_chart(index, token)
        self._update_chart(index+1, self._dummy_token())

        for state in self.chart[lexer.num_tokens]:
            if self._is_goal_state(state):
                state.yield_rule(state.tree)
                return state.tree[0]
            

    def _update_chart(self, index, token):
        while True:
            changed = False
            for state in self.chart[index]:
                next_states = self.predict(state, index)
                for s in next_states:
                    changed |= self.add_to_chart(s, index)

                next_state = self.scanning(state, token)
                if next_state is not None:
                    changed |= self.add_to_chart(next_state, index+1)

                next_states = self.complete(state)
                for s in next_states:
                    changed |= self.add_to_chart(s, index)
            if not changed:
                break


    def _is_goal_state(self, state):
        return (state.head == self.start_symbol and
                state.after == () and
                state.start == 0)


    def _get_token_type(self, token):
        return token.type


    def _is_epsilon(self, char):
        return char == EPSILON


    def _skip_epsilon(self, state):
        while state.after <> () and self._is_epsilon(state.after[0]):
            eps = state.after[0]
            state.before = state.before + (eps,)
            state.after = state.after[1:]


    def _dummy_token(self):
        token = LexToken()
        token.type = None
        return token
        



class ChartState(object):
    def __init__(self,
                 head=None,
                 before=None,
                 after=None,
                 start=0,
                 tree=None,
                 yield_rule=None):
        self.head = head
        self.before = () if (before is None) else before
        self.after = () if (after is None) else after
        self.start = start
        self.tree = [None] if (tree is None) else tree  # AST is initially None
        self.yield_rule = yield_rule

        self.skip_epsilon()


    def skip_epsilon(self):
        while self.after <> () and is_epsilon_transition(self.after[0]):
            eps = self.after[0]
            self.before = self.before + (eps,)
            self.after = self.after[1:]


    def __eq__(self, other):
        return (self.head == other.head and
                self.before == other.before and
                self.after == other.after and
                self.start == other.start)


    def __ne__(self, other):
        return not self.__eq__(other)

    



class Production(object):
    def __init__(self,
                 head=None,
                 body=None,
                 yield_rule=None):
        self.head = head
        self.body = body
        self.yield_rule = yield_rule





class YaccInfo(object):

    def __init__(self, module=None):
        self.tokens, p_rules = self._get_yacc_variables(module)
        p_rules = map(self._convert_rule, p_rules)
        self.production_rules = self._create_production_rules(p_rules)


    def _get_yacc_variables(self, module):
        frame, variables = get_global_vars(module)
        filter_rules = [lambda x: x == "tokens",
                        lambda x: x.startswith("p_")]
        variables = sorted(filter_variables(filter_rules, variables),
                           key=partial(by_appearance, frame))
        tokens, production_rules = categorize(filter_rules, variables)

        if len(tokens) == 0:
            raise SyntaxError("'tokens' (a tuple of strings) must be defined")

        return tokens[-1][-1], production_rules  # tokens = [('tokens', (...))]


    def _create_production_rules(self, p_rules):
        concat = lambda x, y: x + y
        return reduce(concat, map(self._extract_production_rules, p_rules))


    def _extract_production_rules(self, p_rule):
        '''Given a p_rule function, extract production rules from it.'''
        rules = p_rule.__doc__
        nonterminals = set()
        LR = split(rules.replace('\n', ' '), ':')
        try:
            head, rhs = LR
        except ValueError:
            # 'need more than one value to unpack' (rule derives epsilon)
            head, rhs = LR[0], EPSILON
        nonterminals.add(head)
        alts = map(lambda x: tuple(split(x)), split(rhs, '|')) # alternatives
        alts = map(lambda alt: alt if alt else (EPSILON,), alts)

        # check if token_names (terminals) have common names with nonterminals
        common = list(nonterminals & set(self.tokens))
        if common:
            raise SyntaxError("%r appears in both nonterminals and tokens" % common[0])
        return [Production(head=head, body=b, yield_rule=p_rule) for b in alts]


    def _convert_rule(self, p_rule):
        '''Given a tuple (name, value), if value is a func,
        return it as it is; otherwise convert value to a function.'''
        name, value = p_rule
        if callable(value):
            value.__name__ = name
            return value
        fn = lambda tree: tree
        fn.__name__ = name
        fn.__doc__ = value
        return fn
