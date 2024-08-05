import unittest
from unittest.mock import MagicMock

from utils import get_all_info_for_PRs, ticket_mentioned_in_pr


def make_pr_mock(title, content, file_changes):
    pr = MagicMock()
    pr.title = title
    pr.body = content
    files = []
    for filename, content in file_changes.items():
        file = MagicMock()
        file.filename = filename
        file.patch = content
        files.append(file)
    pr.get_files.return_value = files
    return pr


class GithubUtilsTests(unittest.TestCase):
    def setUp(self):
        self.repository = MagicMock()
        self.pulls = []
        self.repository.get_pulls.return_value = self.pulls

    def test_GIVEN_PR_with_title_content_no_files_WHEN_get_info_called_THEN_return_title_and_content(self):
        expected_title = "TEST_TITLE"
        expected_content = "MY_CONTENT"

        self.pulls.append(make_pr_mock(expected_title, expected_content, {}))

        pr_info = get_all_info_for_PRs(self.repository, "")

        self.assertEqual((expected_title, expected_content, ""), pr_info[0])

    def test_GIVEN_PR_with_title_content_and_file_changed_WHEN_get_info_called_with_filename_THEN_return_title_content_and_file_changes(self):
        expected_title = "TEST_TITLE"
        expected_content = "MY_CONTENT"
        filename = "my_file"
        file_changes = "test_changes"

        self.pulls.append(make_pr_mock(expected_title, expected_content, {filename: file_changes}))

        pr_info = get_all_info_for_PRs(self.repository, filename)

        self.assertEqual((expected_title, expected_content, file_changes), pr_info[0])

    def test_GIVEN_PR_with_title_content_and_file_changed_WHEN_get_info_called_with_different_filename_THEN_return_title_content_and_no_file_changes(self):
        expected_title = "TEST_TITLE"
        expected_content = "MY_CONTENT"
        filename = "my_file"
        file_changes = "test_changes"

        self.pulls.append(make_pr_mock(expected_title, expected_content, {filename: file_changes}))

        pr_info = get_all_info_for_PRs(self.repository, "not_file")

        self.assertEqual((expected_title, expected_content, ""), pr_info[0])

    def test_GIVEN_PR_with_ticket_number_in_title_WHEN_prs_checked_THEN_returns_true(self):
        pr_infos = [("Ticket 1000", "Some body text", "Some code changes")]
        self.assertTrue(ticket_mentioned_in_pr(1000, pr_infos))

    def test_GIVEN_PR_with_url_to_ticket_in_code_WHEN_prs_checked_THEN_returns_true(self):
        pr_infos = [("Bad title", "Some body text", "see https://github.com/ISISComputingGroup/IBEX/issues/1000")]
        self.assertTrue(ticket_mentioned_in_pr(1000, pr_infos))

    def test_GIVEN_PR_with_ticket_not_mentioned_WHEN_prs_checked_THEN_returns_false(self):
        pr_infos = [("Bad title", "Some body text", "some code changes")]
        self.assertFalse(ticket_mentioned_in_pr(1000, pr_infos))

    def test_GIVEN_two_PRs_with_ticket_mentioned_in_first_WHEN_prs_checked_THEN_returns_true(self):
        pr_infos = [("Ticket 1000", "Some body text", "some code changes"),
                    ("Bad title", "Some body text", "some code changes")]
        self.assertTrue(ticket_mentioned_in_pr(1000, pr_infos))

    def test_GIVEN_two_PRs_with_ticket_mentioned_in_second_WHEN_prs_checked_THEN_returns_true(self):
        pr_infos = [("Bad title", "Some body text", "some code changes"),
                    ("Ticket 1000", "Some body text", "some code changes")]
        self.assertTrue(ticket_mentioned_in_pr(1000, pr_infos))
