from collections import namedtuple
import re
import unittest

from wtforms.validators import ValidationError

from fixtures import standard_graph, graph, users, groups, session, permissions  # noqa
from util import get_group_permissions, get_user_permissions
from grouper.constants import (
        ARGUMENT_VALIDATION,
        AUDIT_MANAGER,
        PERMISSION_AUDITOR,
        PERMISSION_VALIDATION,
        )
from grouper.fe.forms import ValidateRegex
import grouper.fe.util


def test_basic_permission(standard_graph, session, users, groups, permissions):  # noqa
    """ Test adding some permissions to various groups and ensuring that the permissions are all
        implemented as expected. This also tests permissions inheritance in the graph. """

    graph = standard_graph  # noqa

    assert sorted(get_group_permissions(graph, "team-sre")) == ["audited:", "ssh:*", "sudo:shell"]
    assert sorted(get_group_permissions(graph, "tech-ops")) == [
        "audited:", "ssh:shell", "sudo:shell"]
    assert sorted(get_group_permissions(graph, "team-infra")) == ["sudo:shell"]
    assert sorted(get_group_permissions(graph, "all-teams")) == []

    assert sorted(get_user_permissions(graph, "gary@a.co")) == [
        "audited:", "ssh:*", "ssh:shell", "sudo:shell"]
    assert sorted(get_user_permissions(graph, "zay@a.co")) == [
        "audited:", "ssh:*", "ssh:shell", "sudo:shell"]
    assert sorted(get_user_permissions(graph, "zorkian@a.co")) == [
        "audited:", AUDIT_MANAGER + ":", PERMISSION_AUDITOR + ":", "ssh:*", "sudo:shell"]
    assert sorted(get_user_permissions(graph, "testuser@a.co")) == []
    assert sorted(get_user_permissions(graph, "figurehead@a.co")) == [
        "sudo:shell"]


def test_has_permission(standard_graph, users):  # noqa
    """ Tests the has_permission method of a user object. """

    # In our setup, zorkian has 'audited' with no arguments
    assert users["zorkian@a.co"].has_permission("audited"), "zorkian has permission audited"
    assert not users["zorkian@a.co"].has_permission("audited", argument='foo'), \
        "zorkian has permission audited:foo"
    assert not users["zorkian@a.co"].has_permission("audited", argument='*'), \
        "zorkian has permission audited:*"

    # zay has ssh:*
    assert users["zay@a.co"].has_permission("ssh"), "zay has permission ssh"
    assert users["zay@a.co"].has_permission("ssh", argument='foo'), "zay has permission ssh:foo"
    assert users["zay@a.co"].has_permission("ssh", argument='*'), "zay has permission ssh:*"


class PermissionTests(unittest.TestCase):
    def test_reject_bad_permission_names(self):
        self.assertEquals(len(grouper.fe.util.test_reserved_names("permission_lacks_period")), 1)
        self.assertEquals(len(grouper.fe.util.test_reserved_names("grouper.prefix.reserved")), 1)
        self.assertEquals(len(grouper.fe.util.test_reserved_names("admin.prefix.reserved")), 1)
        self.assertEquals(len(grouper.fe.util.test_reserved_names("test.prefix.reserved")), 1)

        Field = namedtuple("field", "data")

        def eval_permission(perm):
            ValidateRegex(PERMISSION_VALIDATION)(form=None, field=Field(data=perm))

        self.assertIsNone(eval_permission('foo.bar'))
        self.assertIsNone(eval_permission('foobar'))
        self.assertIsNone(eval_permission('foo.bar_baz'))
        self.assertRaises(ValidationError, eval_permission, 'foo__bar')
        self.assertRaises(ValidationError, eval_permission, 'foo.bar.')
        self.assertRaises(ValidationError, eval_permission, 'foo._bar')

        def eval_argument(arg):
            ValidateRegex(ARGUMENT_VALIDATION)(form=None, field=Field(data=arg))

        self.assertIsNone(eval_argument('foo.bar'))
        self.assertIsNone(eval_argument('foobar'))
        self.assertIsNone(eval_argument('underscore_'))
        self.assertIsNone(eval_argument('equals='))
        self.assertIsNone(eval_argument('plus+'))
        self.assertIsNone(eval_argument('slash/'))
        self.assertIsNone(eval_argument('dot.'))
        self.assertIsNone(eval_argument('colon:'))
        self.assertIsNone(eval_argument('hyphen-'))
        self.assertIsNone(eval_argument('underscore_equals=plus+slash/dot.color:hyphen-ok'))
        self.assertRaises(ValidationError, eval_argument, 'whitespace invalid')
        self.assertRaises(ValidationError, eval_argument, 'question?mark')
        self.assertRaises(ValidationError, eval_argument, 'exclaimation!point')
