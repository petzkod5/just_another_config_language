import jacl
import pytest
from jacl.main import lex, TextView, Token, TokenType


@pytest.fixture
def jacl_basic():
    return """
    application
    {
        integer  4
        float    9.2
        bool     true
        string   test
        long     "This is a test"
    }
    """


@pytest.fixture
def single_quote():
    return """
    application
    {
        single 'this is a test'
    }
    """


@pytest.fixture
def section_inside_block_comments():
    return """
    ###
    application
    {
        variable  1
        variable2 2
    }
    ###
    """


@pytest.fixture
def unclosed_comment_block():
    return """
    ###
    application
    {
        variable 1
    }
    """


@pytest.fixture
def unclosed_double_quote():
    return """
    app
    {
        variable "this is a quote with no end
    }
    """


@pytest.fixture
def unclosed_single_quote():
    return """
    app
    {
        variable 'this is a quote with no end
    }
    """


@pytest.fixture
def inline_open_brace():
    return """
    app{

        variable 'test'
    }
    """


@pytest.fixture
def single_line_comment():
    return """
    app{
    # This is a comment inside a section
        variable 'test'
    }
    # A comment outside a section
    """


@pytest.fixture
def inline_comments():
    return """
    app {
        variable 'test' # This comment should be ignored
    }
    """


def test_basic_lex(jacl_basic):
    tokens = jacl.main.lex(TextView(jacl_basic))
    expected = [
        Token(type=TokenType.WORD, value="application"),
        Token(type=TokenType.OPEN_CURLY, value=None),
        Token(type=TokenType.WORD, value="integer"),
        Token(type=TokenType.INTEGER, value=4),
        Token(type=TokenType.WORD, value="float"),
        Token(type=TokenType.FLOAT, value=9.2),
        Token(type=TokenType.WORD, value="bool"),
        Token(type=TokenType.BOOL_TRUE, value=True),
        Token(type=TokenType.WORD, value="string"),
        Token(type=TokenType.WORD, value="test"),
        Token(type=TokenType.WORD, value="long"),
        Token(type=TokenType.WORD, value="This is a test"),
        Token(type=TokenType.CLOSE_CURLY, value=None),
    ]
    assert tokens == expected


def test_single_quote(single_quote):
    tokens = jacl.main.lex(TextView(single_quote))
    expected = [
        Token(type=TokenType.WORD, value="application"),
        Token(type=TokenType.OPEN_CURLY, value=None),
        Token(type=TokenType.WORD, value="single"),
        Token(type=TokenType.WORD, value="this is a test"),
        Token(type=TokenType.CLOSE_CURLY, value=None),
    ]
    assert tokens == expected


def test_block_comments(section_inside_block_comments):
    tokens = jacl.main.lex(TextView(section_inside_block_comments))
    assert tokens == []


def test_unclosed_block_comment_raises_error(unclosed_comment_block):
    with pytest.raises(SyntaxError) as ctx:
        jacl.main.lex(TextView(unclosed_comment_block))

    assert ctx.match("No closing comment block found")


def test_unclosed_double_quote_raises_error(unclosed_double_quote):
    with pytest.raises(SyntaxError) as ctx:
        jacl.main.lex(TextView(unclosed_double_quote))

    ctx.match("Unterminated")


def test_unclosed_single_quote_raises_error(unclosed_single_quote):
    with pytest.raises(SyntaxError) as ctx:
        jacl.main.lex(TextView(unclosed_single_quote))
    ctx.match("Unterminated")


def test_inline_open_brace(inline_open_brace):
    tokens = jacl.main.lex(TextView(inline_open_brace))
    expected = [
        Token(TokenType.WORD, "app"),
        Token(TokenType.OPEN_CURLY),
        Token(TokenType.WORD, "variable"),
        Token(TokenType.WORD, "test"),
        Token(TokenType.CLOSE_CURLY),
    ]
    assert expected == tokens


def test_single_line_comment(single_line_comment):
    tokens = jacl.main.lex(TextView(single_line_comment))
    expected = [
        Token(TokenType.WORD, "app"),
        Token(TokenType.OPEN_CURLY),
        Token(TokenType.WORD, "variable"),
        Token(TokenType.WORD, "test"),
        Token(TokenType.CLOSE_CURLY),
    ]
    assert expected == tokens


def test_inline_comment(inline_comments):
    tokens = jacl.main.lex(TextView(inline_comments))
    expected = [
        Token(TokenType.WORD, "app"),
        Token(TokenType.OPEN_CURLY),
        Token(TokenType.WORD, "variable"),
        Token(TokenType.WORD, "test"),
        Token(TokenType.CLOSE_CURLY),
    ]
    assert expected == tokens
