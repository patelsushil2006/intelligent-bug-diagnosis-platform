from backend.code_corrector import auto_fix_code


def test_c_missing_parenthesis():
    code = 'printf("%d\\n", a + b;'
    corrected = auto_fix_code(code, "c")
    assert corrected == 'printf("%d\\n", a + b);'


def test_valid_code_is_not_changed():
    code = 'printf("%d\\n", a + b);'
    corrected = auto_fix_code(code, "c")
    assert corrected is None


def test_python_is_not_changed():
    code = "print(a + b"
    corrected = auto_fix_code(code, "python")
    assert corrected is None