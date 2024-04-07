from __future__ import annotations

import logging
import logging.config
import os
import sys
from enum import auto, Enum
from pathlib import Path
from pprint import pprint
from typing import Any, Union

from attrs import asdict, define, field

__all__ = ["loads"]

log = logging.getLogger("jacl")
logging.config.dictConfig(
    {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {"simple": {"format": "%(levelname)s: %(message)s"}},
        "handlers": {
            "stdout": {
                "class": "logging.StreamHandler",
                "formatter": "simple",
                "stream": "ext://sys.stdout",
            }
        },
        "loggers": {"root": {"level": "DEBUG", "handlers": ["stdout"]}},
    }
)


@define
class Variable:
    name: str
    value: Any


@define
class Section:
    name: str
    variables: list[Variable] = field(factory=list)
    subsections: list[Section] = field(factory=list)

    def add(self, value: Variable | Section):
        """Add a variable or section to current section"""
        if isinstance(value, Variable):
            matching_variables = [v for v in self.variables if v.name == value.name]
            assert len(matching_variables) <= 1  # This should never be more than 1

            if len(matching_variables) == 1:
                matching_variable_idx = self.variables.index(matching_variables[0])
                v = self.variables.pop(matching_variable_idx)
                if isinstance(v.value, list):
                    v.value.append(value.value)
                    self.variables.append(v)
                else:
                    v.value = [v.value]
                    v.value.append(value.value)
                    self.variables.append(v)

            else:
                self.variables.append(value)
        elif isinstance(value, Section):
            matching_subsections = [s for s in self.subsections if s.name == value.name]
            assert len(matching_subsections) <= 1  # This should never be more than 1

            if len(matching_subsections) == 1:
                matching_section_idx = self.subsections.index(matching_subsections[0])
                s = self.subsections.pop(matching_section_idx)
                for var in value.variables:
                    s.add(var)
                for sec in value.subsections:
                    s.add(sec)
                self.subsections.append(s)
            else:
                self.subsections.append(value)
        else:
            raise ValueError(f"Can not append item of type {type(value)} to section.")

    def __getitem__(self, key: str) -> Section | Variable:
        for s in self.subsections:
            if key == s.name:
                return s

        for v in self.variables:
            if key == v.name:
                return v.value

        raise KeyError(f"Unknown section value {key}")

    def __getattribute__(self, name: str, /) -> Any:
        try:
            return super().__getattribute__(name)
        except AttributeError:
            return self.__getitem__(name)


@define
class JACL:
    _sections: list[Section] = field(factory=list)

    def add(self, section: Section) -> None:
        """Add a new section to JACL Configuration Object"""
        matching_sections = [s for s in self._sections if s.name == section.name]
        assert len(matching_sections) <= 1  # This should never be > 1

        if len(matching_sections) == 1:
            raise NameError(
                f"Section: {section.name} already exists! Top-Level JACL Sections may not occur twice"
            )
        else:
            self._sections.append(section)

    def __str__(self) -> str:
        return str(asdict(self))

    def __repr__(self) -> str:
        return self.__str__()

    def __getitem__(self, key: str) -> Section:
        for s in self._sections:
            if key == s.name:
                return s

        raise KeyError(f"Unknown Section Name: {key}")

    def __setitem__(self, key: str, value: Section) -> None:
        if not isinstance(value, Section):
            raise ValueError(f"Can not append value of type: {type(value)} to JACL")

        if key != value.name:
            raise NameError(
                f"Section Key, must match the name of the section. {key} != {value.name}"
            )

        self.add(value)

    def __getattribute__(self, name: str, /) -> Any:
        try:
            return super().__getattribute__(name)
        except AttributeError:
            return self.__getitem__(name)


class TokenType(Enum):
    OPEN_CURLY = auto()
    CLOSE_CURLY = auto()
    WORD = auto()
    BOOL_TRUE = auto()
    BOOL_FALSE = auto()
    INTEGER = auto()
    FLOAT = auto()
    NONE = auto()

    @staticmethod
    def get_token_type(view: str | int | float) -> TokenType:
        if isinstance(view, int):
            return TokenType.INTEGER
        elif isinstance(view, float):
            return TokenType.FLOAT

        for kw_name, kw_type in keywords:
            if view.lower() == kw_name.lower():
                return kw_type

        return TokenType.WORD


@define
class Token:
    type: TokenType = field(default=None)
    value: Any = field(default=None)

    def determine_value(self, word: str | int | float) -> None:
        """Determine value and set self.value to determined value or else just the word text"""
        if self.type == TokenType.BOOL_TRUE:
            self.value = True
        elif self.type == TokenType.BOOL_FALSE:
            self.value = False
        elif self.type == TokenType.NONE:
            self.value = None
        elif self.type in (TokenType.INTEGER, TokenType.FLOAT, TokenType.WORD):
            self.value = word


keywords = [
    ("true", TokenType.BOOL_TRUE),
    ("false", TokenType.BOOL_FALSE),
    ("none", TokenType.NONE),
]


class TextView:
    def __init__(self, txt: str) -> None:
        self._txt: str = txt

    def __eq__(self, value: object, /) -> bool:
        if not isinstance(value, (str, TextView)):
            return False

        if isinstance(value, str):
            return self._txt == value
        else:
            return self._txt == value._txt

    def __str__(self):
        return self._txt

    def __len__(self):
        return len(self._txt)

    def triml(self, n: int = 1) -> str:
        """Trim n chars from the left most(top-most) part of the text and return"""
        if n > len(self):
            raise OverflowError(
                f"Not enough characters to read. Tried to read {n} chars, current length: {len(self)}"
            )
        chars = self._txt[0:n]
        self._txt = self._txt[n:]
        return chars

    def checkl(self, n: int = 1) -> str:
        """Check n chars from the left most part of the text and return"""
        if n > len(self):
            raise OverflowError(
                f"Not enough characters to read. Tried to read {n} chars, current length: {len(self)}"
            )

        return self._txt[0:n]

    @staticmethod
    def isalnum(s: str) -> bool:
        o = ord(s)
        if 32 < o < 123:
            return True

        return False


def lex(view: TextView) -> list[Token]:
    assert type(view) == TextView
    tokens = []

    while len(view) > 0:
        token = Token()
        char: str = view.triml()
        if char == '"':
            # String Literals
            word = ""
            try:
                while view.checkl() != '"':
                    word += view.triml()
            except OverflowError as e:
                raise SyntaxError("Unterminated String Literal indicator '" "'") from e
            view.triml()  # Trim the trailing "
            token.type = TokenType.WORD
            token.value = word
            tokens.append(token)

        elif char == "'":
            # String Literals
            word = ""
            try:
                while view.checkl() != "'":
                    word += view.triml()
            except OverflowError as e:
                raise SyntaxError("Unterminated String Literal indicator '" "'") from e
            view.triml()  # Trim the trailing "
            token.type = TokenType.WORD
            token.value = word
            tokens.append(token)

        elif char == "{":
            token.type = TokenType.OPEN_CURLY
            tokens.append(token)

        elif char == "}":
            token.type = TokenType.CLOSE_CURLY
            tokens.append(token)

        elif char == "#":
            # Comment Signifiers
            next_two_chars = view.checkl(2)
            # Block Comments
            if next_two_chars == "##":
                view.triml(2)  # Trim the remaining two ##
                try:
                    while view.checkl(3) != "###":
                        view.triml()
                except OverflowError as e:
                    raise SyntaxError("No closing comment block found") from e

                view.triml(3)  # Trim the closing ###

            # Single Line Comments
            else:
                try:
                    while view.checkl() != "\n":
                        view.triml()
                except OverflowError as e:
                    raise SyntaxError(
                        "Unknown error occurred while processing comment line. Expected newline"
                    ) from e

        elif TextView.isalnum(char):
            word = ""
            word += char
            while len(view) > 0 and TextView.isalnum(view.checkl()):
                char = view.triml()
                word += char

            # Check if the word is any numerics
            try:
                word = int(word)
            except ValueError:
                try:
                    word = float(word)
                except ValueError:
                    pass

            token.type = TokenType.get_token_type(word)
            token.determine_value(word)
            tokens.append(token)

    return tokens


def _parse_section(tokens, section: Section) -> Section:
    while len(tokens) > 0:
        token = tokens.pop(0)
        if token.type == TokenType.WORD:
            next_token = tokens[0]
            if next_token.type == TokenType.OPEN_CURLY:
                # Current Token is subsection Starter
                subsection = _parse_section(tokens, Section(token.value))
                section.add(subsection)

            elif next_token.type in (
                TokenType.WORD,
                TokenType.FLOAT,
                TokenType.INTEGER,
                TokenType.BOOL_FALSE,
                TokenType.BOOL_TRUE,
            ):
                # Current Token is a Variable Name
                section.add(Variable(name=token.value, value=next_token.value))
                tokens.pop(0)  # Eat the next token
            else:
                raise SyntaxError(
                    f"Unknown token when parsing section: {section.name} - Token: {token}"
                )
        elif token.type == TokenType.CLOSE_CURLY:
            break  # Closing Section

    return section


def parse(tokens: list[Token]) -> JACL:
    jacl = JACL()

    while len(tokens) > 0:
        token = tokens.pop(0)
        if token.type == TokenType.WORD:
            next_token = tokens[0]
            if next_token.type == TokenType.OPEN_CURLY:
                # Current Token is a Section Starter
                tokens.pop(0)  # Eat the curly Brace
                section = _parse_section(tokens, Section(token.value))
                jacl.add(section)
        else:
            raise SyntaxError(f"Unknown Token when parsing: {token}")

    return jacl


def loads(path: Union[os.PathLike, str]):
    if not isinstance(path, Path):
        path = Path(path)
    tokens = lex(TextView(path.read_text()))
    jacl = parse(tokens)

    return jacl


if __name__ == "__main__":
    config = loads(sys.argv[1])
    application_settings = config["application.settings"]
    print(application_settings)
    pprint(asdict(config))
    pprint(application_settings.config_location)
