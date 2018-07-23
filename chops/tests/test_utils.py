from unittest import TestCase

from chops.utils import deep_merge, is_dict_like_list


def in_list_map(dct, key):
    for item in dct:
        if item['name'] == key:
            return True
    return False


def get_from_list_map(dct, key, default=None):
    for item in dct:
        if item['name'] == key:
            return item['value']
    return default


class DictMergeTestCase(TestCase):
    def test_merges_dicts(self):
        a = {
            'a': 1,
            'b': {
                'b1': 2,
                'b2': 3,
            },
        }
        b = {
            'a': 1,
            'b': {
                'b1': 4,
            },
        }

        assert deep_merge(a, b)['a'] == 1
        assert deep_merge(a, b)['b']['b2'] == 3
        assert deep_merge(a, b)['b']['b1'] == 4

    def test_inserts_new_keys(self):
        """Will it insert new keys by default?"""
        a = {
            'a': 1,
            'b': {
                'b1': 2,
                'b2': 3,
            },
        }
        b = {
            'a': 1,
            'b': {
                'b1': 4,
                'b3': 5
            },
            'c': 6,
        }

        assert deep_merge(a, b)['a'] == 1
        assert deep_merge(a, b)['b']['b2'] == 3
        assert deep_merge(a, b)['b']['b1'] == 4
        assert deep_merge(a, b)['b']['b3'] == 5
        assert deep_merge(a, b)['c'] == 6

    def test_does_not_insert_new_keys(self):
        """Will it avoid inserting new keys when required?"""
        a = {
            'a': 1,
            'b': {
                'b1': 2,
                'b2': 3,
            },
        }
        b = {
            'a': 1,
            'b': {
                'b1': 4,
                'b3': 5,
            },
            'c': 6,
        }

        assert deep_merge(a, b, add_keys=False)['a'] == 1
        assert deep_merge(a, b, add_keys=False)['b']['b2'] == 3
        assert deep_merge(a, b, add_keys=False)['b']['b1'] == 4
        try:
            assert deep_merge(a, b, add_keys=False)['b']['b3'] == 5
        except KeyError:
            pass
        else:
            raise Exception('New keys added when they should not be')

        try:
            assert deep_merge(a, b, add_keys=False)['b']['b3'] == 6
        except KeyError:
            pass
        else:
            raise Exception('New keys added when they should not be')

    def test_is_dict_like_list(self):
        """Check that we can recognise dict-like lists"""
        dict_likes = [
            [
                {'name': 'First Name', 'value': 'John'},
                {'name': 'Second Name', 'value': 'Smith'},
            ],
        ]
        not_even_close = [
            [
                {'name': 'First Name', 'value': 'John'},
                {'name': 'John Smith', 'value': 'high', 'size': 'large'},
            ],
            [
                {'name': 'First Name', 'value': 'John'},
                {'name': 'John Smith', 'size': 'large'},
            ],
            ['A', 'B'],
            'Some text',
        ]

        for item in dict_likes:
            assert is_dict_like_list(item), f'Should be a dictionary like list: {item}'

        for item in not_even_close:
            assert not is_dict_like_list(item), f'Should not be a dictionary like list: {item}'

    def test_merges_dict_like_lists(self):
        """Test that we can merge dictionary-like lists by default"""
        a = {
            'a': [
                {'name': 'a', 'value': 1},
                {'name': 'b', 'value': {'a': 1}},
            ]
        }

        b = {
            'a': [
                {'name': 'a', 'value': 2},
                {'name': 'b', 'value': {'a': 2, 'b': 3}},
            ]
        }

        merged = deep_merge(a, b)

        assert get_from_list_map(merged['a'], 'a') == 2
        assert get_from_list_map(merged['a'], 'b')['a'] == 2
        assert get_from_list_map(merged['a'], 'b')['b'] == 3

    def test_inserts_new_list_map_keys(self):
        """Will it insert new list map keys by default?"""
        a = {
            'a': [
                {'name': 'a', 'value': 1},
            ]
        }

        b = {
            'a': [
                {'name': 'b', 'value': 2},
            ]
        }

        merged = deep_merge(a, b)

        assert in_list_map(merged['a'], 'b')
        assert get_from_list_map(merged['a'], 'a') == 1
        assert get_from_list_map(merged['a'], 'b') == 2

    def test_does_not_insert_new_list_map_keys(self):
        """Will it avoid inserting new keys to list maps when required?"""
        a = {
            'a': [
                {'name': 'a', 'value': 1},
            ]
        }

        b = {
            'a': [
                {'name': 'b', 'value': 2},
            ]
        }

        merged = deep_merge(a, b, add_keys=False)

        assert not in_list_map(merged['a'], 'b')
        assert get_from_list_map(merged['a'], 'a') == 1

    def test_does_not_merge_list_maps(self):
        """Will it avoid merging list map keys if required?"""
        a = {
            'a': [
                {'name': 'a', 'value': 1},
            ]
        }

        b = {
            'a': [
                {'name': 'b', 'value': 2},
            ]
        }

        merged = deep_merge(a, b, merge_list_maps=False)

        assert not in_list_map(merged['a'], 'a')
        assert get_from_list_map(merged['a'], 'b') == 2
        assert len(merged['a']) == 1
