#!/usr/bin/env python
# coding: utf-8

import builtins
import copy
import datetime
import enum
import inspect
import pathlib
import types
import typing
import uuid

import click
import stringcase


def autoclick(
    *object: typing.Union[types.FunctionType, click.Command], group=None, **settings
) -> click.Command:
    """Automatically generate a click command line application using type inference."""
    app = group or click.Group()
    for command in object:
        if isinstance(command, click.Command):
            app.add_command(command)
        elif isinstance(command, types.FunctionType):
            decorators = signature_to_decorators(command)
            command = command_from_decorators(
                command, *decorators, **settings, help=inspect.getdoc(command)
            )
            app.add_command(command)
        elif isinstance(command, dict):
            decorators = decorators_from_dict(command)
            command = command_from_decorators(None, *decorators, **settings)
    return command if len(object) == 1 else app


def istype(x: typing.Any, y: type) -> bool:
    if isinstance(x, type):
        return issubclass(x, y)
    return False


def click_type(
    object: typing.Union[type, tuple], default=None
) -> typing.Union[type, click.types.ParamType]:
    """Translate python types to click's subset of types."""
    if isinstance(object, typing._GenericAlias):
        return click_type(object.__args__[0], default)
    elif isinstance(object, type):
        if issubclass(object, datetime.datetime):
            return click.DateTime()
        if issubclass(object, typing.Tuple):
            return click.Tuple(object.__args__)
        if issubclass(object, uuid.UUID):
            return click.UUID(default)
        if object is list:
            return
        if issubclass(object, set):
            return click.Choice(object)

        if issubclass(object, pathlib.Path):
            return click.Path()
        if object in {builtins.object, typing.Any}:
            return
        return object
    else:
        if isinstance(object, tuple):
            if all(isinstance(x, int) for x in object[:2]):
                return click.IntRange(*object)
            if all(isinstance(x, float) for x in object[:2]):
                return click.FloatRange(*object)


def command_from_decorators(command, *decorators, **settings):
    if command is None:
        *decorators, command = decorators
    for decorator in reversed(decorators):
        command = decorator(command)
    return click.command(no_args_is_help=bool(decorators), **settings)(command)


def decorators_from_dicts(annotations, defaults, *decorators):
    for k, v in annotations.items():
        if k in defaults:
            t = click_type(v, defaults.get(k))
            decorators += (
                click.option(
                    "-" * (1 if len(k) == 1 else 2) + stringcase.spinalcase(k),
                    type=t,
                    default=defaults.get(k),
                    show_default=True,
                    is_flag=v is bool,
                ),
            )

        elif isinstance(v, typing._GenericAlias) or istype(v, list):
            decorators += (
                click.argument(
                    stringcase.spinalcase(k),
                    type=click_type(getattr(v, "__args__", (str,))[0]),
                    nargs=-1,
                ),
            )
        else:
            decorators += (
                click.argument(stringcase.spinalcase(k), type=click_type(v)),
            )
    return decorators


def decorators_from_dict(object):
    return decorators_from_dicts(object.get("__annotations__", {}), object)


def decorators_from_module(object):
    return decorators_from_dict(vars(object))


def signature_to_decorators(object, *decorators):
    signature = inspect.signature(object)
    decorators += decorators_from_dicts(
        {
            k: typing.List[v.annotation]
            if v.kind == inspect._ParameterKind.VAR_POSITIONAL
            else v.annotation
            for k, v in signature.parameters.items()
            if k != "ctx"
        },
        {
            k: v.default
            for k, v in signature.parameters.items()
            if v.default != inspect._empty
        },
    )
    for k, v in signature.parameters.items():
        if k == "ctx":
            decorators += (click.pass_context,)
        break
    return decorators


if __name__ == "__main__":
    if "__file__" in locals():
        if "covtest" in __import__("sys").argv:
            print(__import__("doctest").testmod(optionflags=8))
    else:
        import IPython

        complement, copy, compose
        get_ipython().system(
            "jupyter nbconvert --to python --TemplateExporter.exclude_input_prompt=True cleye.ipynb"
        )
        with IPython.utils.capture.capture_output():
            get_ipython().system("black cleye.py")
        get_ipython().system("isort cleye.py")
        get_ipython().system("ipython -m coverage -- run cleye.py covtest")
        get_ipython().system("coverage report")
        get_ipython().system("coverage html")
        with IPython.utils.capture.capture_output():
            get_ipython().system("pyreverse cleye -osvg -pcleye")
        IPython.display.display(IPython.display.SVG("classes_cleye.svg"))
        with IPython.utils.capture.capture_output():
            get_ipython().system("pyreverse cleye -osvg -pcleye -my -s1")
        IPython.display.display(IPython.display.SVG("classes_cleye.svg"))
