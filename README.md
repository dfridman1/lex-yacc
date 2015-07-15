# Lex - Yacc

This repo contains an implementation of tools for lexical (tokenizing) and syntax
analyses (parsing and AST construction). Below follow short overviews of lexer
and parser.



#### Lex Overview
The token names must be specified in a tuple named 'tokens'. 

User can optionally specify possible states in a tuple; each state is itself a
2-element tuple consisting of a state name and its type ('exclusive'/'inclusive').
NOTE: the state ("INITIAL", "exclusive") is implicitly defined. If the state is
inclusive, then all of the token rules defined for this state will be added
to the rules of the active states; whereas, if the state is exclusive, then it
will be the only active state.


Token rules can be defined in 2 ways: either by defining a global function
or a global variable with regex value. The naming of the token rules must conform
to the following:
- t_TOKENNAME (for the INITIAL state)
- t_STATENAME_TOKENNAME (for all other states)

NOTE: if the token name (part after prefix 't_') for the INITIAL state is not
present in the tuple 'tokens' AND the token rule (function) return value is not
None, then an error is raised.

For example, suppose we have:

    tokens = ("INT", "STRING")

    # version 1
    def t_INT(t):
        r'[0-9]+'
        t.value = int(t.value)
        return t
    
    # version 2
    def t_INT_INVALID(t):
        r'[0-9]+'
        t.value = int(t.value)
        return t

Then the version 1 is valid since token 'INT' exists, whereas version 2 is
invalid because token name 'INT_INVALID' is undefined. This problem can be
overcome by explicitly setting token type. For example,

    def t_INT_VALID(t):
        r'[0-9]+'
        t.value = int(t.value)
        t.type = 'INT'
        return t
    
If we use a global variable to define a token rule, ie

    t_int = r'[0-9]+'
    
then under the hood it will be transformed to the following:

    def t_int(t):
        r'[0-9]+'
        return t
        
The implicit argument 't' to the token rule is an instance of the class LexToken,
which has the following attributes:
* type (token name)
* value (lexeme matched)
* lexpos (index in the input string (0-based))
* lineno (line number)
* lexer (reference to the current lexer)

When the function is invoked, 'value' attribute is automatically set to the
lexeme matched, 'type' is set to the part of function name after prefix
't_STATENAME' (or 't_' for 'INITIAL' state), lexpos is set to the start index
in the input string and lexer is set to the current lexer. Attribute 'lineno'
is also automatically set to the value of 'lineno' of lexer itself, which has
to be managed by the user. It can be achieved this way:

    def t_newline(t):
        r'\n'
        t.lexer.lineno += 1
        
        
Suppose we have the following:
    
    tokens = ('INT', 'STRING')
    states = (('COMMENTS', 'exlusive'),)
    
and we want to enter a 'COMMENTS' state when we see '/\*' and exit it on '\*/'.
We can accomplish this:

    def t_COMMENTS_comment(t):
        r'\/\*'
        t.lexer.begin('COMMENTS')
        
    def t_COMMENTS_commentend(t):
        r'\*\/'
        t.lexer.end('COMMENTS')
        
A special token rule is reserved for each state - 't_STATENAME_error' ('t_error' 
for 'INITIAL' state). In this case the implicit parameter is an instance of 
LexError, which has the same attributes as LexToken, but instead of 'type' it 
has 'error_msg'. Also the 'value' is set to the value of the
input_string[lexpos:]. Example usage:

    def t_error(t):
        print "invalid char: %r" % t.value[0]
        t.lexer.skip(1)  # 1 char advance in input to avoid infinite loop
        return t
        
        
Characters to be ignored can be specified in 't_STATENAME_ignore' ('t_ignore' for
'INITIAL' state) Hence, if we want to ignore whitespace, we can do the following:
    
    t_ignore = r' \t'  # the name t_ignore' is arbitary
    
    
To initialize a lexer:
    
    import lex
    
    lexer = lex.lex()
    lexer.input("input string")
    while True:
        token = lexer.token()
        if token is None:
            break
        # otherwise, do something with token

An example of using a lexer for tokenizing JSON formatted strings, see
[json_lex.py](./json_lex.py).



#### Yacc Overview

Our parser will need an object created by the lexer (ie, lex.lex()). Suppose
we have the specification for the lexer in a file 'mylexer.py'.

Let's consider a simple language of function definitions conforming to the
following CFG (context-free grammar):

    DEF            => string lparen ARGS_LIST rparen equal EXP_SUM
    ARGS_LIST      => NONEMPTY_LIST | epsilon
    NONEMPTY_LIST  => string comma NONEMPTY_LIST | string
    EXP_SUM        => EXP
    EXP            => EXP plus string | string
    
"myfunc(x, y, z) = x + z" is a valid sentence of the grammar. In our specification
all lower-case symbols are terminals (tokens defined in 'mylexer.py'), whereas
upper-case symbols constitute non-terminals (case distinction is irrelevant -
here it is used for convinience only).

A production rule must be defined as a function with a name starting with 'p_'.
Different productions for the same nonterminal may be defined within the same
function (alternatives must be separated by ' | ') or as separate functions.
Epsilon is represented as an empty string, ie 'LIST : ' (empty list) or
'LIST : ARG comma LIST |'.

The production rules for the above grammar may look like:

    import yacc
    from mylexer.py import lexer, tokens  # NOTE: tokens must be imported

    def p_func_def(p):
        'DEF : string lparen ARGS_LIST rparen equal EXP'
        # p[1] = string (function name)
        # p[3] = ARGS_LIST
        # p[6] = EXP (body of the function)
        p[0] = ('function', p[1], p[3], p[6])
        
    def p_args_list(p):
        '''ARGS_LIST : NONEMPTY_LIST
                     | '''
        p[0] = ('args', []) if len(p) == 1 else ('args', p[1])
        
    def p_args_nonempty(p):
        'NONEMPTY_LIST : string comma NONEMPTY_LIST'
        p[0] = [p[1]] + p[3]
        
    def p_args_nonempty_one(p):
        'NONEMPTY_LIST : string'
        p[0] = [p[1]]
        
    def p_exp_sum(p):
        'EXP_SUM : EXP'
        p[0] = ('sum', p[1])
        
    def p_exp(p):
        'EXP : EXP plus string | string'
        if len(p) == 2:
            p[0] = [p[1]]
        else:
            p[0] = p[1] + [p[3]]
            

To run a parser:
    
    parser = yacc.yacc()
    text_to_parse = "myfunc(x, y, z) = x + z"
    tree = parser.parse(text_to_parse, lexer)
    if tree is not None:
        print tree
    else:
        print "Parsing failed!"
        
    
The result AST is ('function', 'myfunc', ('args', ['x', 'y', 'z']), ('sum', ['x', 'z'])).

NOTE: 'parse method' from above takes a key argument 'tokenfunc'. By default, 'tokenfunc' is
    
    tokenfunc = lambda lextoken: lextoken.value
    
A more sophisticated example (JSON parsing) of using yacc is in [json_yacc.py](./json_yacc.py).
