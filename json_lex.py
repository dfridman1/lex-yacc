import lex
import sys



tokens = ("number",
          "string",
          "boolean",
          "null",
          "comma",
          "colon",
          "lbrace",
          "rbrace",
          "lbracket",
          "rbracket")


t_ignore = " \t"


t_null = r'null'
t_boolean = r'true|false'
t_comma = r','
t_colon = r':'
t_lbrace = r'\{'
t_rbrace = r'\}'
t_lbracket = r'\['
t_rbracket = r'\]'



def t_newline(t):
    r'\n'
    t.lexer.lineno += 1



def t_string(t):
    r'"(?:\\.|[^"])*"'
    t.value = t.value[1:-1]
    return t



def t_number(t):
    r'[0-9]+(?:[.][0-9]+)?'
    try:
        t.value = int(t.value)
    except ValueError:
        t.value = float(t.value)
    return t



def t_error(t):
    t.lexer.skip()  # skip 1 char (default)
    t.value = t.value[0]
    t.error_msg = "unknown char"
    return t



lexer = lex.lex()



if __name__ == "__main__":
    lexer.input(sys.stdin.read())
    while True:
        token = lexer.token()
        if token is None:
            break
        print token
