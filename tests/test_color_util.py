from claukawa.color_util import color_for


def test_color_is_stable():
    assert color_for("/foo/bar") == color_for("/foo/bar")


def test_different_paths_differ():
    assert color_for("/foo/bar") != color_for("/foo/baz")


def test_returns_rgb_in_range():
    r, g, b = color_for("anything")
    assert 0 <= r <= 255
    assert 0 <= g <= 255
    assert 0 <= b <= 255


def test_empty_path_does_not_crash():
    assert isinstance(color_for(""), tuple)
