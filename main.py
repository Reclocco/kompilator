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
# memory management
memory_idx = 1
# lista zmiennych
variables = {}
inits = {}
# lista tablic
arrays = {}
labels_val = []

# no właśnie, co ja w ogóle robie
co_ja_w_ogole_robie = 1


def begin(str):
    if co_ja_w_ogole_robie == 1:
        return "#   BEGIN " + str + "\n"
    return ""


def end(str):
    if co_ja_w_ogole_robie == 1:
        return "#   END " + str + "\n"
    return ""


######################### iksy dupiksy i numerki
# stała
def make_number(number, register):
    list = ''

    while number > 0:
        if number % 2 == 0:
            number = number / 2
            list = "SHL " + register + "\n" + list
        else:
            number -= 1
            list = "INC " + register + "\n" + list

    list = "RESET " + register + "\n" + list

    return list

# kobieta
def make_variable(name, lineno):
    global memory_idx

    if name in variables:
        raise Exception("ERROR: variable " + name + "already declared, line:" + lineno)

    memory_idx += 1
    variables[name] = memory_idx


# tablica
def make_array(name, alpha, omega, lineno):
    global memory_idx

    if name in variables:
        raise Exception("ERROR: variable " + name + "already declared, line:" + lineno)

    if alpha > omega:
        raise Exception("ERROR: table " + name + "has invalid size:" + lineno)

    memory_idx += 1
    arrays[name] = (memory_idx, alpha, omega)
    memory_idx += omega-alpha


def unmake_variable(name):
    variables.pop(name)


######################### pamięć






