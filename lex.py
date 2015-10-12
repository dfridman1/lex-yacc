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
IgnoreMethod = namedtuple("IgnoreMethod", ["name", "state", "pattern", "oneof", "type"])
ErrorMethod  = namedtuple("ErrorMethod", ["state", "type"])

TokenType  = 0
IgnoreType = 1
ErrorType  = 2







class Lexer(object):

    INITIAL = "INITIAL_STATE"

    def __init__(self, module=None):
        self._text = None
        self._cursorPos = self._lineno = self._numTokens = self._numTokensLeft = 0
        self._currentStateName = Lexer.INITIAL
        self._statesStack = [self._currentStateName]
        self._warnings = []
        self._errors = []
        self._states = _LexerInfo(module).getStates()
        self._currentState = self._getCurrentLexState()


        
    @staticmethod
    def LexerApi(states=None):
        if states is None: states = []
        states = states + [Lexer.INITIAL]

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
    def Ignore(name=None, state=_INITIAL, pattern=None, oneof=""):

        def ignoreDecorator(f):
            pat = re.compile(pattern) if pattern is not None else None
            setattr(f, LEXER_METHOD, IgnoreMethod(name=name,
                                                  state=state,
                                                  pattern=pat,
                                                  oneof=oneof,
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



    def beginState(self, stateName):
        self._currentStateName = stateName
        self._currentState = self._getCurrentLexState()



    def pushState(self, stateName):
        if stateName != self._statesStack[-1]:
            self._statesStack.append(stateName)
            self._currentStateName = stateName
            self._currentState = self._getCurrentLexState()



    def popState(self):
        if len(self._statesStack) > 1:
            self._statesStack.pop()
            self._currentStateName = self._statesStack[-1]
            self._currentState = self._getCurrentLexState()



    def _getNextToken(self):
        while not self._inputConsumed():
            lexState = self._currentState

            numCharsIgnored = lexState.applyIgnoreRules(self._text, self._cursorPos)
            if numCharsIgnored > 0:
                self._cursorPos += numCharsIgnored
                continue

            lexToken = self._createDefaultLexToken()
            lexToken, numCharsMatched = lexState.applyTokenRules(self._text,
                                                                 self._cursorPos,
                                                                 lexToken)

            if numCharsMatched > 0:
                self._cursorPos += numCharsMatched
                if lexToken is not None:
                    lexToken.setLineno(self._lineno)
                    yield lexToken
                continue

            oldCursor = self._cursorPos
            lexError = self._createDefaultLexError()
            lexError = lexState.applyErrorRule(lexError)
            if oldCursor >= self._cursorPos:
                # raise error (infine loop)
                return


    def token(self):
        generator = self._getNextToken()
        try:
            return next(generator)
        except StopIteration:
            return None



    def _createDefaultLexError(self):
        lexError = LexError(lineno=self._lineno,
                            lexpos=self._cursorPos,
                            value=self._text[self._cursorPos:],
                            error_msg="Error")
        lexError.setParentLexer(self)
        return lexError



    def _createDefaultLexToken(self):
        lexToken = LexToken(lineno=self._lineno,
                            lexpos=self._cursorPos)
        lexToken.setParentLexer(self)
        return lexToken



    def _getCurrentLexState(self):
        return self._states[self._currentStateName]



    def _inputConsumed(self):
        return self._cursorPos >= len(self._text)



    def skip(self, n=1):
        self._cursorPos += n



    def setLineno(self, lineno):
        self._lineno = lineno


    def getLineno(self):
        return self._lineno




class LexItem(object):

    def setValue(self, value):
        self.value = value
        return self


    def setLexpos(self, lexpos):
        self.lexpos = lexpos
        return self


    def setLineno(self, lineno):
        self.lineno = lineno
        return self
    
    def setParentLexer(self, lexer):
        self.lexer = lexer
        return self


    def getParentLexer(self):
        return getattr(self, "lexer", None)
        



class LexToken(LexItem):

    def __init__(self,
                 type=None,
                 value=None,
                 lexpos=None,
                 lineno=None):
        self.type = type
        self.value = value
        self.lexpos = lexpos
        self.lineno = lineno

        

    def __str__(self):
        return "LexToken(%s, %r, %d, %d)" % (self.type,
                                             self.value,
                                             self.lexpos,
                                             self.lineno)


    def setType(self, type):
        self.type = type
        return self
    
    



class LexError(LexItem):

    def __init__(self,
                 error_msg=None,
                 value=None,
                 lineno=None,
                 lexpos=None):
        self.error_msg = error_msg
        self.value = value
        self.lineno = lineno
        self.lexpos = lexpos



    def __str__(self):
        return "LexError(%r, %r, %r, %r)" % (self.error_msg,
                                             self.value,
                                             self.lineno,
                                             self.lexpos)



    def setErrorMessage(self, message):
        self.error_msg = message


        



    
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

    def applyErrorRule(self, lexError):
        lexError = self._errorRule(lexError)
        if isinstance(lexError, LexError):
            return lexError

    def applyIgnoreRules(self, text, startPos):
        for ignoreRule in self._ignoreRules:
            ignoreRuleInfo = getattr(ignoreRule, LEXER_METHOD)
            patternToMatch = ignoreRuleInfo.pattern
            if patternToMatch is not None:
                match = patternToMatch.match(text, startPos)
                if match is not None:
                    ignoreRule(match.group(0))
                    return match.end() - match.start()
            oneofPattern = ignoreRuleInfo.oneof
            if text[startPos] in oneofPattern:
                ignoreRule(text[startPos])
                return 1
        return 0

    def applyTokenRules(self, text, startPos, lexToken):
        for tokenRule in self._tokenRules:
            ruleInfo = getattr(tokenRule, LEXER_METHOD)
            patternToMatch = ruleInfo.pattern
            match = patternToMatch.match(text, startPos)
            if match is not None:
                textMatched = match.group(0)
                lexToken.setValue(textMatched).setLexpos(startPos).setType(ruleInfo.name)
                lexToken = tokenRule(lexToken)
                if isinstance(lexToken, LexToken):
                    return lexToken, len(textMatched)
                else:
                    return None, len(textMatched)
        return None, 0


        
    
class _LexerInfo(object):

    def __init__(self, module=None):
        module, variables = utils.get_global_vars(module)
        lexerClass = _LexerInfo._findLexerClass(variables)

        if lexerClass is None: return

        stateNames  = _LexerInfo._extractLexerStateNames(lexerClass)
        lexerMethods = _LexerInfo._extractLexerMethods(lexerClass)

        self._states = _LexerInfo._buildStatesDict(stateNames, lexerMethods, lexerClass)


        
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
    def _buildStatesDict(stateNames, lexerMethods, userProvidedClass):
        states = { stateName : _LexState(stateName) for stateName in stateNames }
        userClassInstance = userProvidedClass()

        def _applyMethodPartially(classInstance, method):
            return getattr(classInstance, method.__name__)
        
        for method in lexerMethods:
            methodInfo = getattr(method, LEXER_METHOD)
            method = _applyMethodPartially(userClassInstance, method)
            if methodInfo.type == TokenType:
                states[methodInfo.state].addTokenRule(method)
            elif methodInfo.type == IgnoreType:
                states[methodInfo.state].addIgnoreRule(method)
            else:
                states[methodInfo.state].setErrorRule(method)

        return states
