import sys
import ply.yacc as yacc
from lekser import tokens
import re

######################### wszystko co mam :(
# GET x
# PUT x
#
# LOAD x y
# STORE x y
#
# ADD x y
# SUB x y
# RESET x
# INC x
# DEC x
# SHR x
# SHL x
#
# JUMP j
# JZERO x j
# JODD x j
#
# HALT

######################### misc
# typy: VAR, ARR, NUM

######################### założenia
# rejestry:
#   A: głowny domyślny      DLA KOMEND
#   B: głowny pomocniczy    DLA KOMEND
#   C: roboczy
#   D: roboczy
#   E: pętle
#   F: pętle

# memory management
memory_idx = 10
# lista zmiennych
variables = {}
is_initiated = {}
is_iterator = {}
variables["number1"] = 0
# lista tablic
arrays = {}
# lista skoków
labels = []

# no właśnie, co ja w ogóle robie
co_ja_w_ogole_robie = 0


def debug_start(comment):
    if co_ja_w_ogole_robie == 1:
        return "#BEGIN " + comment + "\n"
    return ""


def debug_end(comment):
    if co_ja_w_ogole_robie == 1:
        return "#END " + comment + "\n"
    return ""


######################### iksy dupiksy i numerki
# stała
def make_number(number, register):
    my_code = ''

    while number > 0:
        if number % 2 == 0:
            number = number / 2
            my_code = "SHL " + register + "\n" + my_code
        else:
            number -= 1
            my_code = "INC " + register + "\n" + my_code

    my_code = "RESET " + register + "\n" + my_code
    return my_code


# kobieta
def make_variable(name, lineno):
    global memory_idx

    if name in variables:
        raise Exception("ERROR: variable " + name + " already declared, line: " + lineno)

    memory_idx += 1
    variables[name] = memory_idx


def make_temp_variable():
    global memory_idx
    temp_id = "&TEMP" + str(memory_idx)
    is_iterator[temp_id] = True
    make_variable(temp_id, -1)
    is_initiated[temp_id] = True

    return temp_id


def make_iterator(name, lineno):
    global memory_idx

    is_iterator[name] = True
    make_variable(name, lineno)
    is_initiated[name] = True

    return name


# tablica
def make_array(name, alpha, omega, lineno):
    global memory_idx

    if name in variables:
        raise Exception("ERROR: variable " + name + " already declared, line: " + lineno)

    if alpha > omega:
        raise Exception("ERROR: table " + name + " has invalid size, line: " + lineno)

    memory_idx += 1
    arrays[name] = (memory_idx, alpha, omega)
    memory_idx += omega - alpha + 1


# unmaykr
def unmake_variable(name):
    variables.pop(name)


######################### pamięć
# bezpiecznik
def fuse_array_address(name, lineno):
    if name not in arrays:
        if name in variables:
            raise Exception("Error: invalid use of variable " + name + ' in line: ' + lineno)
        else:
            raise Exception("Error: name " + name + ' not declared, in line: ' + lineno)


def fuse_variable_address(name, lineno):
    if name not in variables:
        if name in arrays:
            raise Exception("Error: invalid use of array " + name + ' in line: ' + lineno)
        else:
            raise Exception("Error: name " + name + ' not declared, in line: ' + lineno)


def fuse_variable_initialization(name, lineno):
    if name not in is_initiated:
        raise Exception("Error: variable " + name + ' not declared, in line: ' + lineno)


def fuse_iterator_assign(name, lineno):
    if name in is_iterator:
        raise Exception("Error: variable " + name + ' is iterator, in line: ' + lineno)


def p_error(p):
    raise Exception("Error: name " + str(p.value) + " not recognized, in line " + str(p.lineno))



# znajdź zmienna
def get_variable_idx(name, lineno):
    if name in variables:
        return variables[name]
    else:
        raise Exception("ERROR: variable " + name + "not found, line:" + lineno)


# znajdź tablice
def get_array_idx(name, lineno):
    if name in arrays:
        return arrays[name]
    else:
        raise Exception("ERROR: array " + name + "not found, line:" + lineno)


# ładuj zmienna albo liczbe do rejestru
def get_to_reg(x, register, lineno):
    if x[0] == "var":
        fuse_variable_initialization(x[1], lineno)

    elif x[0] == "num":
        return debug_start("LOAD_CONST") + \
               make_number(x[1], register) + \
               debug_end("LOAD_CONST")

    return debug_start("LOAD_VAR") + \
           get_address(x, lineno) + \
           "LOAD " + register + " a\n" + \
           debug_end("LOAD_VAR")


# znajdź adres zmiennej albo tablicy
def get_address(var, lineno):
    if var[0] == "var":
        fuse_variable_address(var[1], lineno)

        return debug_start("LOAD_VAR_ADDR") + \
               make_number(variables[var[1]], "a") + \
               debug_end("LOAD_VAR_ADDR")

    elif var[0] == "arr":
        fuse_array_address(var[1], lineno)
        arr_idx = var[2]
        mem_start, arr_alpha, arr_omega = arrays[var[1]]

        return debug_start("LOAD_ARR_ADDR") + \
               get_to_reg(arr_idx, "a", lineno) + \
               make_number(arr_alpha, "c") + \
               make_number(mem_start, "d") + \
               "SUB a c" + "\n" + "ADD a d" + "\n" + \
               debug_end("LOAD_TAB_ADDR")


######################### program
# main
def p_program(p):
    '''program : DECLARE declarations BEGIN commands END'''
    p[0] = labels_to_jumps(p[4]) + "HALT"


def p_program_no_declare(p):
    '''program : BEGIN commands END'''
    p[0] = labels_to_jumps(p[2]) + "HALT"


# var pierwsze w deklaracjach
def p_declare_first_var(p):
    '''declarations : ID'''
    name = p[1]
    line = str(p.lineno(1))

    make_variable(name, line)


# arr pierwsze w deklaracjach
def p_declare_first_arr(p):
    '''declarations : ID LBR NUM COLON NUM RBR'''
    name = p[1]
    alpha = p[3]
    omega = p[5]
    line = str(p.lineno(1))

    make_array(name, alpha, omega, line)


# deklaracja var
def p_declare_var(p):
    '''declarations : declarations COMMA ID'''
    name = p[3]
    line = str(p.lineno(3))

    make_variable(name, line)


# deklaracja arr
def p_declare_arr(p):
    '''declarations : declarations COMMA ID LBR NUM COLON NUM RBR'''
    name = p[3]
    alpha = p[5]
    omega = p[7]
    line = str(p.lineno(3))

    make_array(name, alpha, omega, line)


############ zmienne i niezmienne
def p_value_number(p):
    '''value : NUM'''
    p[0] = ("num", p[1])


# tab albo var
def p_value_identifier(p):
    '''value : identifier'''
    p[0] = (p[1])


# var
def p_idenifier_var_id(p):
    '''identifier : ID'''
    p[0] = ("var", p[1])


# arr(num)
def p_indentifier_arr_id_num(p):
    '''identifier : ID LBR NUM RBR'''
    p[0] = ("arr", p[1], ("num", p[3]))


# arr(var)
def p_identifier_arr_id_var(p):
    '''identifier : ID LBR ID RBR'''
    p[0] = ("arr", p[1], ("var", p[3]))


############ oznakowie gdzie skakać
def prepare_labels(how_many):
    global labels

    my_labels = []
    my_jumps = []

    for i in range(how_many):
        labels.append(0)
        # do późniejszych odwołań
        label_idx = str(len(labels) - 1)
        my_labels.append("#LABEL" + label_idx + "#")
        my_jumps.append("#JUMP" + label_idx + "#")

    return [my_labels, my_jumps]


def labels_to_jumps(my_code):
    global labels
    cleaned_up_pre = []
    cleaned_up_post = ""

    curr_line = 0
    for line in my_code.split("\n"):
        labeled_line = re.search("#LABEL[0-9]+#", line)

        if labeled_line:
            label_id = int(labeled_line.group()[6:-1])
            labels[label_id] = curr_line
            # line = re.sub("#LABEL[0-9]+#", "", line)

        cleaned_up_pre.append(line)
        curr_line += 1

    curr_line = 0
    first = True
    for line in cleaned_up_pre:
        jump_line = re.search("#JUMP[0-9]+#", line)

        if jump_line:
            jump_id = int(jump_line.group()[5:-1])
            jump_where = labels[jump_id]
            line = re.sub("#JUMP[0-9]+#",
                          str(jump_where - curr_line), line)

        if first:
            cleaned_up_post += line
        else:
            cleaned_up_post += "\n" + line

        first = False
        curr_line += 1

    cleaned_up_post = re.sub("#LABEL[0-9]+#", "", cleaned_up_post)

    return cleaned_up_post


############ S -> SA, S -> A, KOMENDY nigdy stop
# S -> SA
def p_command_devour(p):
    '''commands : commands command'''
    p[0] = p[1] + p[2]


# S -> A
def p_command_last(p):
    '''commands : command'''
    p[0] = p[1]


############ w rejestrze A zapisuje adres do jakiej zmiennej przypisuje, w rejestrze B przypisywaną wartość
def p_command_assign(p):
    '''command : identifier ASSIGN expression SEMICOLON'''
    var = p[1]
    value = p[3]
    line = str(p.lineno(1))
    fuse_iterator_assign(var[1], line)
    p[0] = debug_start("ASSIGN") + value + get_address(var, line) + \
           "STORE b a\n" + debug_end("ASSIGN")

    is_initiated[var[1]] = True


# czytanie
def p_command_read(p):
    '''command : READ identifier SEMICOLON'''
    name = p[2]
    line = str(p.lineno(2))
    is_initiated[name[1]] = True
    p[0] = debug_start("READ") + get_address(name, line) + \
           "GET a\n" + debug_end("READ")


# pisanie
def p_command_write(p):
    '''command : WRITE identifier SEMICOLON'''
    name = p[2]
    line = str(p.lineno(2))
    fuse_variable_initialization(name[1], line)
    p[0] = debug_start("WRITE") + get_address(name, line) + \
           "PUT a\n" + debug_end("WRITE")


def p_command_write_num(p):
    '''command : WRITE NUM SEMICOLON'''
    number = p[2]
    p[0] = debug_start("WRITE") + make_number(number, "b") + \
           "RESET a\n" + "STORE b a\n" + \
           "PUT a\n" + debug_end("WRITE")


############ działania
def p_expression_value(p):
    '''expression : value'''
    number = p[1]
    line = str(p.lineno(1))
    p[0] = debug_start("EXPRESSION_VALUE") + get_to_reg(number, "b", line) + \
           debug_end("EXPRESSION_VALUE")


# NIE UŻYWAMY REJESTRU A
def p_expression_plus(p):
    '''expression : value PLUS value'''
    number_1 = p[1]
    number_2 = p[3]
    line = str(p.lineno(1))
    p[0] = debug_start("ADDING") + get_to_reg(number_1, "b", line) + \
           get_to_reg(number_2, "c", line) + "ADD b c\n" + debug_end("ADDING")


# NIE UŻYWAMY REJESTRU A
def p_expression_minus(p):
    '''expression : value MINUS value'''
    number_1 = p[1]
    number_2 = p[3]
    line = str(p.lineno(1))
    p[0] = debug_start("SUBTRACTING") + get_to_reg(number_1, "b", line) + \
           get_to_reg(number_2, "c", line) + "SUB b c\n" + \
           debug_end("SUBTRACTING")


# NIE UŻYWAMY REJESTRU A
# def p_expression_mult(p):
#     '''expression : value MULT value'''
#     number_1 = p[1]
#     number_2 = p[3]
#     line = str(p.lineno(1))
#
#     p[0] = debug_start("MULTIPLYING") + "RESET b\n" + \
#            get_to_reg(number_2, "e", line) + get_to_reg(number_1, "f", line) + \
#            "JZERO e 4\n" + "ADD b f\n" + "DEC e\n" + \
#            "JUMP -3\n" + debug_end("MULTIPLYING")


def p_expression_mult(p):
    '''expression : value MULT value'''
    number_1 = p[1]
    number_2 = p[3]
    line = str(p.lineno(1))

    p[0] = debug_start("MULTIPLYING") + \
            get_to_reg(number_1, "b", line) + \
            get_to_reg(number_2, "c", line) + \
            "RESET d\n" + \
            "JZERO b 6\n" + \
            "JODD b 2\n" + \
            "ADD d c\n" + \
            "SHR a\n" + \
            "SHL b\n" + \
            "JUMP -5\n" + debug_end("MULTIPLYING")


# DIVISOR/SCALED DIVISOR-   a
# DIVIDEND-                 b
# REMAIN-                   c
# RESULT-                   d
# MULTIPLE-                 e
# CALC CHECK-               f
def p_expression_div(p):
    '''expression : value DIV value'''
    number_1 = p[1]
    number_2 = p[3]
    line = str(p.lineno(1))

    p[0] = debug_start("DIVISION") + \
        get_to_reg(number_1, "b", line) + \
        get_to_reg(number_2, "a", line) + \
        "RESET d\n" + \
        "JZERO a 23\n" + \
        "RESET c\n" + \
        "ADD c b\n" + \
        "RESET e\n" + \
        "INC e\n" + \
        "RESET f\n" + \
        "ADD f b\n" + \
        "SUB f a\n" + \
        "JZERO f 4\n" + \
        "SHL a\n" + \
        "SHL e\n" + \
        "JUMP -6\n" + \
        "RESET f\n" + \
        "INC f\n" + \
        "ADD f c\n" + \
        "SUB f a\n" + \
        "JZERO f 3\n" + \
        "SUB c a\n" + \
        "ADD d e\n" + \
        "SHR a\n" + \
        "SHR e\n" + \
        "JZERO e 2\n" + \
        "JUMP -10" + \
        "RESET b\n" + \
        "ADD b d\n" + debug_end("MODULO")


# NIE UŻYWAMY REJESTRU A
def p_expression_mod(p):
    '''expression : value MOD value'''
    number_1 = p[1]
    number_2 = p[3]
    line = str(p.lineno(1))

    p[0] = debug_start("MODULO") + \
           get_to_reg(number_1, "b", line) + \
           get_to_reg(number_2, "a", line) + \
           "RESET d\n" + \
           "JZERO a 23\n" + \
           "RESET c\n" + \
           "ADD c b\n" + \
           "RESET e\n" + \
           "INC e\n" + \
           "RESET f\n" + \
           "ADD f b\n" + \
           "SUB f a\n" + \
           "JZERO f 4\n" + \
           "SHL a\n" + \
           "SHL e\n" + \
           "JUMP -6\n" + \
           "RESET f\n" + \
           "INC f\n" + \
           "ADD f c\n" + \
           "SUB f a\n" + \
           "JZERO f 3\n" + \
           "SUB c a\n" + \
           "ADD d e\n" + \
           "SHR a\n" + \
           "SHR e\n" + \
           "JZERO e 2\n" + \
           "JUMP -10" + \
           "RESET b\n" + \
           "ADD b c\n" + debug_end("MODUO")


# WARUNKI
def p_condition_eq(p):
    '''condition : value EQ value'''
    number_1 = p[1]
    number_2 = p[3]
    line = str(p.lineno(1))
    code_labels, code_jumps = prepare_labels(2)

    p[0] = (debug_start("EQUALS") + \
            get_to_reg(number_1, "b", line) + \
            get_to_reg(number_2, "c", line) + \
            "RESET d\n" + "ADD d b\n" + "SUB d c\n" + \
            "JZERO d 2\n" + "JUMP " + code_jumps[1] + "\n" + \
            "ADD d c\n" + "SUB d b\n" + "JZERO d 2\n" + \
            "JUMP " + code_jumps[1] + "\n" + debug_end("EQUALS"),
            code_labels[1])


def p_condition_neq(p):
    '''condition : value NEQ value'''
    number_1 = p[1]
    number_2 = p[3]
    line = str(p.lineno(1))
    code_labels, code_jumps = prepare_labels(2)

    p[0] = (debug_start("NOT EQUALS") + \
            get_to_reg(number_1, "b", line) + \
            get_to_reg(number_2, "c", line) + \
            "RESET d\n" + "ADD d b\n" + "SUB d c\n" + \
            "JZERO d 2\n" + "JUMP 4\n" + "ADD d c\n" +
            "SUB d b\n" + "JZERO d " + code_jumps[1] + "\n" +
            debug_end("NOT EQUALS"), code_labels[1])


def p_condition_lt(p):
    '''condition : value LT value'''
    number_1 = p[1]
    number_2 = p[3]
    line = str(p.lineno(1))
    code_labels, code_jumps = prepare_labels(2)

    p[0] = (debug_start("LESS THAN") + \
            get_to_reg(number_1, "b", line) + \
            get_to_reg(number_2, "c", line) + \
            "RESET d\n" + "ADD d c\n" + "SUB d b\n" + \
            "JZERO d " + code_jumps[1] + "\n" +
            debug_end("LESS THAN"), code_labels[1])


def p_condition_gt(p):
    '''condition : value GT value'''
    number_1 = p[1]
    number_2 = p[3]
    line = str(p.lineno(1))
    code_labels, code_jumps = prepare_labels(2)

    p[0] = (debug_start("GREATER THAN") + \
            get_to_reg(number_1, "b", line) + \
            get_to_reg(number_2, "c", line) + \
            "RESET d\n" + "ADD d b\n" + "SUB d c\n" + \
            "JZERO d " + code_jumps[1] + "\n" +
            debug_end("GREATER THAN"), code_labels[1])


def p_condition_leq(p):
    '''condition : value LEQ value'''
    number_1 = p[1]
    number_2 = p[3]
    line = str(p.lineno(1))
    code_labels, code_jumps = prepare_labels(2)

    p[0] = (debug_start("LESS EQ THAN") + \
            get_to_reg(number_1, "b", line) + \
            get_to_reg(number_2, "c", line) + \
            "RESET d\n" + "ADD d c\n" + "SUB d b\n" + \
            "JZERO d 2\n" + "JUMP 5\n" + "ADD d b\n" + \
            "SUB d c\n" + "JZERO d 2\n" + "JUMP " + code_jumps[1] + "\n" + \
            debug_end("LESS EQ THAN"), code_labels[1])


def p_condition_geq(p):
    '''condition : value GEQ value'''
    number_1 = p[1]
    number_2 = p[3]
    line = str(p.lineno(1))
    code_labels, code_jumps = prepare_labels(2)

    p[0] = (debug_start("LESS EQ THAN") + \
            get_to_reg(number_1, "b", line) + \
            get_to_reg(number_2, "c", line) + \
            "RESET d\n" + "ADD d b\n" + "SUB d c\n" + \
            "JZERO d 2\n" + "JUMP 5\n" + "ADD d c\n" + \
            "SUB d b\n" + "JZERO d 2\n" + "JUMP " + code_jumps[1] + "\n" + \
            debug_end("LESS EQ THAN"), code_labels[1])


# PETLE
def p_command_if(p):
    '''command : IF condition THEN commands ENDIF'''
    condition = p[2]
    commands = p[4]
    p[0] = debug_start("IF") + condition[0] + \
        commands + condition[1] + debug_end("IF")


def p_command_if_else(p):
    '''command : IF condition THEN commands ELSE commands ENDIF'''
    condition = p[2]
    commands_if = p[4]
    commands_else = p[6]
    code_label, code_jump = prepare_labels(1)

    p[0] = debug_start("IF_ELSE") + condition[0] + \
        commands_if + "JUMP " + code_jump[0] + "\n" + condition[1] + \
        commands_else + code_label[0] + debug_end("IF_ELSE")


def p_command_while(p):
    '''command : WHILE condition DO commands ENDWHILE'''
    condition = p[2]
    commands = p[4]
    loop_label, loop_jump = prepare_labels(1)
    p[0] = debug_start("WHILE") + loop_label[0] + \
           condition[0] + commands + "JUMP " + \
           loop_jump[0] + "\n" + condition[1] + \
           debug_end("WHILE")


def p_command_repeat(p):
    '''command : REPEAT commands UNTIL condition SEMICOLON'''
    condition = p[4]
    commands = p[2]
    loop_label, loop_jump = prepare_labels(1)
    p[0] = debug_start("REPEAT") + loop_label[0] + \
           commands + condition[0] + "JUMP 2\n" + \
           condition[1] + "JUMP " + loop_jump[0] + "\n" + \
           debug_end("REPEAT")


def p_iterator(p):
    '''iterator : ID'''
    id = p[1]
    line = str(p.lineno(1))
    make_iterator(id, line)
    p[0] = id
    is_initiated[id] = True


def p_command_for_to(p):
    '''command : FOR iterator FROM value TO value DO commands ENDFOR'''
    code_labels, code_jumps = prepare_labels(3)
    for_end_var = make_temp_variable()
    iterator = p[2]
    for_start = p[4]
    for_end = p[6]
    commands = p[8]
    line = str(p.lineno(1))

    p[0] = debug_start("FOR") + get_to_reg(for_end, "e", line) + \
        get_address(("var", for_end_var), line) + "STORE e a\n" + \
        get_to_reg(for_start, "f", line) + \
        get_address(("var", iterator), line) + "STORE f a\n" + \
        code_labels[1] + get_to_reg(("var", for_end_var), "e", line) + \
        get_to_reg(("var", iterator), "f", line) + \
        "SUB e f\n" + "JZERO e 2\n" + "JUMP " + code_jumps[2] + "\n" + \
        get_to_reg(("var", iterator), "f", line) + \
        get_to_reg(("var", for_end_var), "e", line) + \
        "SUB f e\n" + "JZERO f 2\n" + \
        "JUMP " + code_jumps[0] + "\n" + code_labels[2] + commands + \
        get_to_reg(("var", iterator), "f", line) + \
        "INC f\n" + get_address(("var", iterator), line) + "STORE f a\n" + \
        "JUMP " + code_jumps[1] + "\n" + \
        code_labels[0] + debug_end("FOR")

    unmake_variable(iterator)



def p_command_for_downto(p):
    '''command : FOR iterator FROM value DOWNTO value DO commands ENDFOR'''
    code_labels, code_jumps = prepare_labels(4)
    for_end_var = make_temp_variable()
    iterator = p[2]
    for_start = p[4]
    for_end = p[6]
    commands = p[8]
    line = str(p.lineno(1))

    p[0] = debug_start("FOR_DOWN") + get_to_reg(for_end, "e", line) + \
           get_address(("var", for_end_var), line) + "STORE e a\n" + \
           get_to_reg(for_start, "f", line) + \
           get_address(("var", iterator), line) + "STORE f a\n" + \
           code_labels[1] + get_to_reg(("var", for_end_var), "e", line) + \
           get_to_reg(("var", iterator), "f", line) + \
           "SUB f e\n" + "JZERO f 2\n" + \
           "JUMP " + code_jumps[2] + "\n" + \
           get_to_reg(("var", iterator), "f", line) + \
           get_to_reg(("var", for_end_var), "e", line) + \
           "SUB e f\n" + "JZERO e 2\n" + \
           "JUMP " + code_jumps[0] + "\n" + code_labels[2] + commands + \
           get_to_reg(("var", iterator), "f", line) + \
           "JZERO f " + code_jumps[0] + "\n" + "DEC f\n" + get_address(("var", iterator), line) + "STORE f a\n" + \
           "JUMP " + code_jumps[1] + "\n" + \
           code_labels[0] + debug_end("FOR_DOWN")

    unmake_variable(iterator)


parser = yacc.yacc()
f = open(sys.argv[1], "r")
try:
    # print("A")
    parsed = parser.parse(f.read(), tracking=True)
    fw = open(sys.argv[2], "w")
    fw.write(parsed)
except Exception as e:
    print(e)
    exit()
