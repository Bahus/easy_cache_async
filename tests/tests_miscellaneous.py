from tests.tests_locmem import User, ordinal_func


class TestMiscellaneous:

    def test_class_repr(self):
        assert repr(User.class_method_full_spec) == (
            '<TaggedCached: '
            'callable="' + __name__ + '.User.class_method_full_spec", '
            'cache_key="{cls.name}:{a}", tags="[\'tag4\', \'tag5:{cls.name}\']", '
            'prefix="' + __name__ + '.User.<lambda>", timeout=500>'
        )

        assert repr(User.class_method_default_cache_key) == (
            '<Cached: '
            'callable="' + __name__ + '.User.class_method_default_cache_key", '
            'cache_key="easy_cache_async.core.Cached.create_cache_key", timeout=DEFAULT_TIMEOUT>'
        )

        assert repr(User.static_method) == (
            '<TaggedCached: '
            'callable="' + __name__ + '.User.static_method", '
            'cache_key="{hg}:{hg}:{test}", tags="()", '
            'prefix="пользователь", timeout=DEFAULT_TIMEOUT>'
        )

        assert repr(User.property_no_tags) == (
            '<Cached: '
            'callable="' + __name__ + '.User.property_no_tags", '
            'cache_key="static_key", timeout=DEFAULT_TIMEOUT>'
        )

        assert repr(User.instance_method_custom_tags) == (
            '<TaggedCached: '
            'callable="' + __name__ + '.User.instance_method_custom_tags", '
            'cache_key="{a}:{b}", tags="' + __name__ + '.User.generate_custom_tags", '
            'prefix="None", timeout=DEFAULT_TIMEOUT>'
        )

        assert repr(ordinal_func) == (
            '<TaggedCached: '
            'callable="' + __name__ + '.ordinal_func", '
            'cache_key="{kwargs[a]}:{kwargs[b]}", tags="()", '
            'prefix="пользователь", timeout=DEFAULT_TIMEOUT>'
        )
