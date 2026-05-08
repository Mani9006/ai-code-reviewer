"""Sample Python code for testing the code review tool.

This module intentionally contains various code quality issues
for demonstration and testing purposes.
"""

import os
import sys
from typing import Optional
import random
import hashlib

# Hardcoded credentials (security issue)
DATABASE_PASSWORD = "super_secret_password_123"
API_KEY = "sk-abcdefghijklmnopqrstuvwxyz1234567890ABCD"
AWS_ACCESS_KEY = "AKIAIOSFODNN7EXAMPLE"

# Debug mode enabled (security issue)
DEBUG = True


def VeryComplexFunction(a, b, c, d, e, f, g, h):
    """A function with many issues."""
    result = 0
    if a > 0:
        if b > 0:
            if c > 0:
                if d > 0:
                    if e > 0:
                        if f > 0:
                            if g > 0:
                                if h > 0:
                                    result = a + b + c + d + e + f + g + h
                                elif h < 0:
                                    result = a - b
                                else:
                                    result = c * d
                            elif g < 0:
                                result = e / f if f != 0 else 0
                            else:
                                result = 0
                        elif e < 0:
                            result = a * b * c
                        else:
                            for i in range(10):
                                for j in range(10):
                                    result += i * j
                    else:
                        result = 42
                elif d < 0:
                    try:
                        result = a / b
                    except:
                        pass
                else:
                    result = 0
            else:
                result = -1
        else:
            while result < 100:
                result += 1
    return result


def no_docstring(x, y):
    return x + y


def str_compare(name):
    """Compare string using 'is'."""
    if name is "admin":
        return True
    return False


class bad_class_name:
    def __init__(self, name, age, email, phone, address, city, country):
        self.name = name
        self.age = age
        self.email = email
        self.phone = phone
        self.address = address
        self.city = city
        self.country = country

    def method_a(self):
        return self.name

    def method_b(self):
        return self.age

    def method_c(self):
        return self.email

    def method_d(self):
        return self.phone

    def method_e(self):
        return self.address

    def method_f(self):
        return self.city

    def method_g(self):
        return self.country

    def type_check(self, x):
        if type(x) is dict:
            return True
        return False

    def manual_counter(self, items):
        i = 0
        for item in items:
            print(item)
            i += 1
        return i


class data_container:
    """A class that could be a dataclass."""

    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z


def eval_usage(data):
    """Use eval - security risk."""
    return eval(data)


def weak_hash(password):
    """Use weak hash algorithm."""
    return hashlib.md5(password.encode()).hexdigest()


def insecure_random():
    """Use insecure random for security."""
    return random.randint(1, 100)


def sql_query(user_id):
    """Build SQL with string concatenation."""
    return "SELECT * FROM users WHERE id = " + str(user_id)


def long_function_with_no_docstring(arg1, arg2, arg3, arg4, arg5, arg6):
    x1 = arg1 + 1
    x2 = arg2 + 2
    x3 = arg3 + 3
    x4 = arg4 + 4
    x5 = arg5 + 5
    x6 = arg6 + 6
    y1 = x1 * 2
    y2 = x2 * 2
    y3 = x3 * 2
    y4 = x4 * 2
    y5 = x5 * 2
    y6 = x6 * 2
    z1 = y1 + y2
    z2 = y3 + y4
    z3 = y5 + y6
    total = z1 + z2 + z3
    return total


x = 1
x = 2
x = 3


def list(items):
    """Shadow built-in."""
    return items


def file_read_no_context(path):
    """Open file without context manager."""
    f = open(path)
    data = f.read()
    f.close()
    return data


# TODO: Refactor this code to use proper configuration management
# FIXME: Remove hardcoded credentials before production
# HACK: Temporary workaround for the authentication issue
