import pprint


def get_build_config():
    config = dict()

    # Print functions
    config['pp'] = pprint.PrettyPrinter(indent=4)
    config['info'] = lambda x: print('\033[94m' + x + '\033[0m')

    return config
