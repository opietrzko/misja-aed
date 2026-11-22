"""Test walidacji zdalnego wykazu AED (import XML i CKAN). Wymaga Django (importuje mcod.resources)."""

import unittest
from unittest import mock

import requests

from mcod.aed.constants import AED_COLUMNS
from mcod.aed.utils import (
    AED_REMOTE_BAD_COLUMNS,
    AED_REMOTE_BAD_EXTENSION,
    AED_REMOTE_NO_URL,
    AED_REMOTE_NOT_ACCESSIBLE,
    check_remote_aed_file,
)


def _response(status=200, content_type="text/csv", body=b""):
    resp = mock.Mock()
    resp.status_code = status
    resp.headers = {"Content-Type": content_type}
    resp.content = body
    return resp


GOOD_CSV = (",".join(AED_COLUMNS) + "\n" + ",".join(["x"] * len(AED_COLUMNS)) + "\n").encode()
BAD_CSV = ("a,b,c\n1,2,3\n").encode()
PATCH = "mcod.resources.dga_utils.request_remote_dga"


class CheckRemoteAedFileTest(unittest.TestCase):
    def test_no_url(self):
        self.assertEqual(check_remote_aed_file(None), AED_REMOTE_NO_URL)

    def test_connection_error(self):
        with mock.patch(PATCH, side_effect=requests.exceptions.ConnectionError):
            self.assertEqual(check_remote_aed_file("http://x/a.csv"), AED_REMOTE_NOT_ACCESSIBLE)

    def test_not_200(self):
        with mock.patch(PATCH, return_value=_response(status=404)):
            self.assertEqual(check_remote_aed_file("http://x/a.csv"), AED_REMOTE_NOT_ACCESSIBLE)

    def test_bad_extension(self):
        with mock.patch(PATCH, return_value=_response(content_type="application/json", body=b"{}")):
            self.assertEqual(check_remote_aed_file("http://x/a.json"), AED_REMOTE_BAD_EXTENSION)

    def test_bad_columns(self):
        with mock.patch(PATCH, return_value=_response(body=BAD_CSV)):
            self.assertEqual(check_remote_aed_file("http://x/a.csv"), AED_REMOTE_BAD_COLUMNS)

    def test_good_file(self):
        with mock.patch(PATCH, return_value=_response(body=GOOD_CSV)):
            self.assertIsNone(check_remote_aed_file("http://x/a.csv"))
