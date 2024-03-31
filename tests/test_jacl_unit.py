import pytest
from jacl import Config
from jacl.main import parse, tokenize, Section, Variable, SyntaxError


@pytest.fixture
def basic_config_text():
    return """
    section1
    {
        variable1  value1
        variable2  value2
        ss1
        {
            subvar1  subvalue1
            subvar2  subvalue2
        }
    }
    

    # Also a comment Here
    # And Here
    # And... here
    section2
    {
        ss1
        {
            s2ss1  v1
            s2ss2  v2
            ss2
            {
                s1ss2  v3
                s2ss2  v4
            }
        }
        # This is a comment shouldn't cause an issue









        Variable1                              Value2
    }
    """


@pytest.fixture
def config_w_list_text():
    return """
    section1
    {
        listname  1
        listname  2
        listname  3
        listname  4
        listname  5
        listname  6
        listname  7
    }
    """


@pytest.fixture
def config_w_multiline_comment():
    return """
    ###




    This
    is a multiline
    comment block










    ###
    

    # This is a single line comment
    # Another Single Line Comment

    section1
    {
        # This is a comment inside a section
        ###
            This is a comment

            block inside a section




            This should be valid

        ###
        variable1  var1
    }
    """


@pytest.fixture
def config_with_inline_comments():
    return """
    section1
    {
        variable1   1   # This is an inline comment

        subsection # This is an inline comment for a subsection
        {
            variable2  2
        }
    }
    """


@pytest.fixture
def config_with_only_comments():
    return """
    # This is a comment

    ###


    A Comment Block




    ###


    # Another Comment


    ### A block

    ###
    """


@pytest.fixture
def config_with_multiple_toplevel_same_sections():
    return """
    section1
    {
        var1    1
    }
    section1
    {
        var1    2
    }
    """


@pytest.fixture
def config_missing_variable_value():
    return """
    section1
    {
        var1
    }
    """


def test_basic_config(basic_config_text):
    result = parse(tokenize(basic_config_text))

    assert "section1" in result.todict().keys()
    assert "section2" in result.todict().keys()

    assert "variable1" in result.section1.todict().keys()
    assert "variable2" in result.section1.todict().keys()
    assert "ss1" in result.section1.todict().keys()

    assert result.section1.variable1 == "value1"
    assert result.section1.variable2 == "value2"

    assert "subvar1" in result.section1.ss1.todict().keys()
    assert "subvar2" in result.section1.ss1.todict().keys()

    assert result.section1.ss1.subvar1 == "subvalue1"
    assert result.section1.ss1.subvar2 == "subvalue2"

    # Section 2
    assert "ss1" in result.section2.todict().keys()
    assert "Variable1" in result.section2.todict().keys()

    assert result.section2.Variable1 == "Value2"

    assert "s2ss1" in result.section2.ss1.todict().keys()
    assert "s2ss2" in result.section2.ss1.todict().keys()
    assert "ss2" in result.section2.ss1.todict().keys()

    assert result.section2.ss1.s2ss1 == "v1"
    assert result.section2.ss1.s2ss2 == "v2"

    assert "s1ss2" in result.section2.ss1.ss2.todict().keys()
    assert "s2ss2" in result.section2.ss1.ss2.todict().keys()

    assert result.section2.ss1.ss2.s1ss2 == "v3"
    assert result.section2.ss1.ss2.s2ss2 == "v4"


def test_config_with_list(config_w_list_text):
    result = parse(tokenize(config_w_list_text))

    assert isinstance(result.section1.listname, list)
    assert len(result.section1.listname) == 7
    for i in range(1, 7):
        assert result.section1.listname[i - 1] == str(i)


def test_multiline_comments(config_w_multiline_comment):
    result = parse(tokenize(config_w_multiline_comment))

    section = Section(
        name="section1", variables=[Variable(name="variable1", value="var1")]
    )
    config = Config()
    config.sections.append(section)

    assert result == config


def test_inline_comments(config_with_inline_comments):
    result = parse(tokenize(config_with_inline_comments))
    expected = Config(
        sections=[
            Section(
                name="section1",
                variables=[Variable(name="variable1", value="1")],
                subsections=[
                    Section(
                        name="subsection",
                        variables=[Variable(name="variable2", value="2")],
                    )
                ],
            ),
        ]
    )
    assert result == expected


def test_empty_config():
    result = parse(tokenize(""))
    assert isinstance(result, Config)
    assert result == Config()


def test_config_only_comments(config_with_only_comments):
    result = parse(tokenize(config_with_only_comments))
    assert isinstance(result, Config)
    assert result == Config()


def test_multiple_toplevel_sections_same_name(
    config_with_multiple_toplevel_same_sections,
):
    with pytest.raises(SyntaxError) as context:
        parse(tokenize(config_with_multiple_toplevel_same_sections))


def test_missing_variable_value(config_missing_variable_value):
    with pytest.raises(SyntaxError) as context:
        parse(tokenize(config_missing_variable_value))
