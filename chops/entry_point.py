from invoke import Collection, Program

from chops import tasks
from chops import helpers


program = Program(namespace=Collection.from_module(tasks), version=helpers.version())
