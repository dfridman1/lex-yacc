import yacc
from json_lex import tokens, lexer
from utils import memo
import sys



# JSON CFG

'''
   VALUE     => OBJECT | ARRAY | number | string | boolean | null
   OBJECT    => lbrace MEMBERS rbrace | lbrace rbrace
   MEMBERS   => PAIR comma MEMBERS | PAIR
   PAIR      => string colon VALUE
   ARRAY     => lbracket ELEMENTS rbracket | lbracket rbracket
   ELEMENTS  => VALUE comma ELEMENTS | VALUE
'''




def p_value(p):
    '''VALUE : OBJECT | ARRAY | number | string | boolean | null'''
    p[0] = p[1]

    

def p_object(p):
    '''OBJECT : lbrace MEMBERS rbrace
              | lbrace rbrace
    '''
    p[0] = ("object", p[2]) if len(p) == 4 else ("object", )



def p_members(p):
    '''MEMBERS : PAIR comma MEMBERS | PAIR'''
    p[0] = p[1] if len(p) == 2 else [p[1]] + [p[3]]



def p_pair(p):
    '''PAIR : string colon VALUE'''
    p[0] = ("pair", p[1], p[3])


    
def p_array(p):
    '''ARRAY : lbracket ELEMENTS rbracket
             | lbracket rbracket
    '''
    p[0] = ("elements", p[2]) if len(p) == 4 else ("elements",)
    


def p_elements(p):
    '''ELEMENTS : VALUE comma ELEMENTS | VALUE'''
    p[0] = p[1] if len(p) == 2 else [p[1]] + [p[3]]




if __name__ == "__main__":
    parser = yacc.yacc(parser='RD')
    tree = parser.parse(sys.stdin.read(), lexer)
    if tree is not None:
        print tree
    else:
        print "Parsing failed!"
