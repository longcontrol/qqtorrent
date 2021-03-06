import sys
from nose.tools import *
import qqbt.cli


def setup():
    pass


def teardown():
    pass


def test_basic():
    pass


@nottest
def test_main_help():
    assert_raises(SystemExit, pgbt.cli.main, ['-h'])
    if hasattr(sys.stdout, 'getvalue'):
        output = sys.stdout.getvalue().strip()
        assert_true('usage' in output)


@nottest
def test_main_noargs():
    assert_raises(SystemExit, pgbt.cli.main, [])


@nottest
def test_main_hello():
    pgbt.cli.main(['zzz', '--hello'])
    if hasattr(sys.stdout, 'getvalue'):
        output = sys.stdout.getvalue().strip()
        assert_equals(output, 'hello')
