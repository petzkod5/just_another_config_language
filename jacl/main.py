from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, List, Union

EOF = "EOF"
SECTION_START = "{"
SECTION_END = "}"
SINGLE_LINE_COMMENT = "#"
MULTILINE_COMMENT = "###"

log = logging.getLogger(__name__)
handler = logging.StreamHandler()
fmt = logging.Formatter("%(levelname)-7s - %(message)s")
handler.setFormatter(fmt)
log.addHandler(handler)
log.setLevel(logging.WARNING)
log.debug("Started.")


class SyntaxError(Exception):
    """Config Syntax Error"""


@dataclass
class Variable:
    name: str
    value: Any


@dataclass
class Section:
    name: str
    variables: List[Variable] = field(default_factory=list)

    subsections: List[Section] = field(default_factory=list)

    def __getitem__(self, item) -> Union[Variable, Section]:
        for v in self.variables:
            if v.name == item:
                return v.value

        for s in self.subsections:
            if s.name == item:
                return s

        raise KeyError("Unknown Section member name %s", item)

    def __setitem__(self, key, value):
        for v in self.variables:
            if v.name == key:
                v.value = value
                return None

        raise KeyError("No variable member with key: %s", key)

    def __getattribute__(self, name, /) -> Union[Variable, Section, str]:
        try:
            return super().__getattribute__(name)
        except AttributeError:
            return self.__getitem__(name)

    def todict(self) -> dict:
        """Return Dict Representation of the Section"""
        d = {}
        for v in self.variables:
            d[v.name] = v.value

        for s in self.subsections:
            d[s.name] = s.todict()

        return d


@dataclass
class Config:
    sections: List[Section] = field(default_factory=list)

    def __len__(self):
        return len(self.sections)

    def __getitem__(self, item) -> Section:
        for s in self.sections:
            if s.name == item:
                return s
        else:
            raise KeyError("Unknown section name: %s", item)

    def __setitem__(self, /):
        raise AssertionError("Setting new items to config is not allowed.")

    def __getattribute__(self, name: str, /) -> Section:
        try:
            return super().__getattribute__(name)
        except AttributeError:
            return self.__getitem__(name)

    def todict(self) -> dict:
        """Return Dictionary Representation of the config"""
        d = {}
        for s in self.sections:
            d[s.name] = s.todict()

        return d

    @staticmethod
    def from_file(file: Union[str, Path]) -> Config:
        if not isinstance(file, Path):
            file = Path(file)

        if not file.exists() or not file.is_file():
            raise OSError(
                "Error opening file %s - check to make sure it exists and is a file",
                str(file),
            )

        return parse(tokenize(file.read_text()))


def normalize_section_name(name: str) -> str:
    name = name.replace(" ", "_")
    name = name.replace(".", "_")
    return name


def section(tokens: List[str], name: str) -> Section:
    this_section = Section(normalize_section_name(name))
    log.debug("Working on section: %s", name)

    current_token = eat(tokens)
    while current_token != SECTION_END:
        if current_token.startswith(MULTILINE_COMMENT):
            eat_until(tokens, MULTILINE_COMMENT)
            current_token = eat(tokens)
            continue

        if current_token.startswith(SINGLE_LINE_COMMENT):
            current_token = eat(tokens)  # Proceed to the next token and continue
            continue

        if lookahead(tokens) == SECTION_START:
            eat(tokens)  # Eat the section start
            subsection = section(tokens, current_token)
            this_section.subsections.append(subsection)
            current_token = eat(tokens)
            continue

        token_split = current_token.split(maxsplit=1)
        if len(token_split) != 2:
            raise SyntaxError(
                "Expected variable line with value, got %s", current_token
            )

        variable_name = token_split[0]
        try:
            # Try and check if the section variable is already
            # Present. If so, make it a list and append the value
            # to it.
            current_var = this_section[variable_name]
            if not isinstance(current_var, list):
                # If it's not already a list, make it a list
                this_section[variable_name] = [current_var]
                this_section[variable_name].append(token_split[1])
            else:
                this_section[variable_name].append(token_split[1])
        except KeyError:
            this_section.variables.append(
                Variable(name=variable_name, value=token_split[1])
            )

        # Eat the next token
        current_token = eat(tokens)

    log.debug("Returning from Section: %s", name)
    return this_section


def eat(tokens: List[str]):
    t = tokens.pop(0)
    log.debug("Eat: %s", t)
    return t


def eat_until(tokens: List[str], stopper: str):
    t = tokens.pop(0)
    while not t.startswith(stopper):
        t = tokens.pop(0)


def lookahead(tokens: List[str]):
    try:
        log.debug("NextT: %s", tokens[0])
        return tokens[0]
    except IndexError:
        return None


def parse(tokens: List[str]):
    log.debug("Parsing Tokens; %s", tokens)
    config = Config()

    while len(tokens) > 0:
        current_token = eat(tokens)

        if current_token.startswith(MULTILINE_COMMENT):
            eat_until(tokens, MULTILINE_COMMENT)
            continue

        if current_token.startswith(SINGLE_LINE_COMMENT):
            continue

        if lookahead(tokens) == SECTION_START:
            eat(tokens)  # Eat the starting {
            section_ = section(tokens, current_token)
            if section_.name in [s.name for s in config.sections]:
                raise SyntaxError(
                    "Top-Level sections must be unique. Found multiple sections named: %s",
                    section_.name,
                )
            config.sections.append(section_)

    return config


def tokenize(text: str):
    lines = []
    for line in text.splitlines():
        line = line.strip()
        # Cleanse the line of any inline comments
        if (
            not line.startswith(SINGLE_LINE_COMMENT)
            and len(line.split("#", maxsplit=1)) == 2
        ):
            line = line.split("#", maxsplit=1)[0].rstrip()
        if line:
            lines.append(line)

    return lines


if __name__ == "__main__":
    config = Config.from_file("./testconfig.p")
    from pprint import pprint

    pprint(config)
