import os


package_path = os.path.abspath(os.path.dirname(__file__))


def version():
    with open(os.path.join(package_path, 'VERSION'), encoding='utf-8') as f:
        return f.read()
