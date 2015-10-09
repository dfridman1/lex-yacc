# *** LEXER ***



from collections import namedtuple, defaultdict
import inspect
import re
import utils





_INITIAL = "INITIAL_STATE"
_LEXER_CLASS_ID = "LEXER_CLASS_ID"
_STATES_ATTR = "_states"

LEXER_METHOD = "LEXER_METHOD"

TokenMethod  = namedtuple("TokenMethod", ["name", "state", "order", "pattern", "type"])
IgnoreMethod = namedtuple("IgnoreMethod", ["state", "pattern", "type"])
ErrorMethod  = namedtuple("ErrorMethod", ["state", "type"])

TokenType  = 0
IgnoreType = 1
ErrorType  = 2







class Lexer(object):

    def __init__(self, module=None):
        self._text = None
        self._cursorPos = self._lineno = self._numTokens = self._numTokensLeft = 0
        self._currentStateName = _INITIAL
        self._warnings = []
        self._errors = []
        self._states = _LexerInfo(module).getStates()


        
    @staticmethod
    def LexerApi(states=None):
        if states is None: states = []
        states = states + [_INITIAL]

        def classDecorator(cls):
            setattr(cls, _LEXER_CLASS_ID, True)
            setattr(cls, _STATES_ATTR, states)
            return cls

        return classDecorator


    
    @staticmethod
    def Token(name=None, state=_INITIAL, order=0, pattern=None):

        def tokenDecorator(f):
            setattr(f, LEXER_METHOD, TokenMethod(name=name,
                                                 state=state,
                                                 order=order,
                                                 pattern=re.compile(pattern),
                                                 type=TokenType))
            return f

        return tokenDecorator


    @staticmethod
    def Ignore(state=_INITIAL, pattern=None):

        def ignoreDecorator(f):
            setattr(f, LEXER_METHOD, IgnoreMethod(state=state,
                                                  pattern=re.compile(pattern),
                                                  type=IgnoreType))
            return f

        return ignoreDecorator

    

    @staticmethod
    def Error(state=_INITIAL):

        def errorDecorator(f):
            setattr(f, LEXER_METHOD, ErrorMethod(state=state,
                                                 type=ErrorType))
            return f

        return errorDecorator

    

    def input(self, text):
        self._text = text


        
    def numTokens(self):
        return self._numTokens


    
    def numTokensLeft(self):
        return self._numTokensLeft

    

    def token(self):
        pass




    
class _LexState(object):

    def __init__(self, stateName):
        self._errorRule = None
        self._ignoreRules = []
        self._tokenRules = []
        self._stateName = stateName

    def setErrorRule(self, rule):
        self._errorRule = rule

    def addIgnoreRule(self, rule):
        self._ignoreRules.append(rule)

    def addTokenRule(self, rule):
        self._tokenRules.append(None)
        ruleOrder = getattr(rule, LEXER_METHOD).order

        j = len(self._tokenRules) - 2
        while j >= 0 and getattr(self._tokenRules[j], LEXER_METHOD).order > ruleOrder:
            self._tokenRules[j+1] = self._tokenRules[j]
            j -= 1

        self._tokenRules[j+1] = rule





        
    
class _LexerInfo(object):

    def __init__(self, module=None):
        module, variables = utils.get_global_vars(module)
        lexerClass = _LexerInfo._findLexerClass(variables)

        if lexerClass is None: return

        stateNames  = _LexerInfo._extractLexerStateNames(lexerClass)
        lexerMethods = _LexerInfo._extractLexerMethods(lexerClass)

        self._states = _LexerInfo._buildStatesDict(stateNames, lexerMethods)


        


        
        
    @staticmethod
    def _findLexerClass(globalVars):
        for (objName, obj) in globalVars:
            if inspect.isclass(obj) and getattr(obj, _LEXER_CLASS_ID, None):
                return obj
        return None

    def getStates(self):
        return self._states


    
    @staticmethod
    def _extractLexerMethods(lexerClass):
        methods = map(lambda x: x[1],
                      inspect.getmembers(lexerClass, predicate=_LexerInfo._isLexerMethod))
        return methods


    
    @staticmethod
    def _extractLexerStateNames(lexerClass):
        return getattr(lexerClass, _STATES_ATTR, None)


    
    @staticmethod
    def _isLexerMethod(val):
        return inspect.ismethod(val) and hasattr(val, LEXER_METHOD)


    
    @staticmethod
    def _buildStatesDict(stateNames, lexerMethods):
        states = { stateName : _LexState(stateName) for stateName in stateNames }

        for method in lexerMethods:
            methodInfo = getattr(method, LEXER_METHOD)
            if methodInfo.type == TokenType:
                states[methodInfo.state].addTokenRule(method)
            elif methodInfo.type == IgnoreType:
                states[methodInfo.state].addIgnoreRule(method)
            else:
                states[methodInfo.state].setErrorRule(method)

        return states
