from invoke import Collection, Program

from chops import tasks
from chops import utils


program = Program(namespace=Collection.from_module(tasks), version=utils.version())


if __name__ == "__main__":
    program.run()
