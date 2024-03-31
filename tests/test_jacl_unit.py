import pytest
from jacl import Config
from jacl.main import parse, tokenize


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
