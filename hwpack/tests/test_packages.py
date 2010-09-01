import os

from testtools import TestCase

from hwpack.packages import (
    ensure_file_uri_starts_with_three_slashes,
    PackageFetcher,
    )
from hwpack.testing import AptSource, Package, TestCaseWithFixtures


class EnsureURITests(TestCase):

    def test_modifies_file_uri_with_one_slash(self):
        uri = "file:/something"
        self.assertEqual(
            "file:///something",
            ensure_file_uri_starts_with_three_slashes(uri))

    def test_doesnt_modify_file_uri_with_three_slashes(self):
        uri = "file:///something"
        self.assertEqual(
            uri, ensure_file_uri_starts_with_three_slashes(uri))

    def test_doesnt_modify_file_uri_with_hostname(self):
        uri = "file://localhost/something"
        self.assertEqual(
            uri, ensure_file_uri_starts_with_three_slashes(uri))

    def test_doesnt_modify_http_uri(self):
        uri = "http://example.org/something"
        self.assertEqual(
            uri, ensure_file_uri_starts_with_three_slashes(uri))


class PackageFetcherTests(TestCaseWithFixtures):

    def test_cleanup_removes_tempdir(self):
        fetcher = PackageFetcher([])
        fetcher.prepare()
        tempdir = fetcher.tempdir
        fetcher.cleanup()
        self.assertFalse(os.path.exists(tempdir))

    def test_cleanup_ignores_missing_tempdir(self):
        fetcher = PackageFetcher([])
        fetcher.prepare()
        tempdir = fetcher.tempdir
        fetcher.cleanup()
        # Check that there is no problem removing it again
        fetcher.cleanup()

    def test_cleanup_before_prepare(self):
        fetcher = PackageFetcher([])
        # Check that there is no problem cleaning up before we start
        fetcher.cleanup()

    def test_prepare_creates_tempdir(self):
        fetcher = PackageFetcher([])
        self.addCleanup(fetcher.cleanup)
        fetcher.prepare()
        self.assertTrue(os.path.isdir(fetcher.tempdir))

    def test_prepare_creates_var_lib_dpkg_status_file(self):
        fetcher = PackageFetcher([])
        self.addCleanup(fetcher.cleanup)
        fetcher.prepare()
        self.assertEqual(
            '',
            open(os.path.join(
                fetcher.tempdir, "var", "lib", "dpkg", "status")).read())

    def test_prepare_creates_var_cache_apt_archives_partial_dir(self):
        fetcher = PackageFetcher([])
        self.addCleanup(fetcher.cleanup)
        fetcher.prepare()
        self.assertTrue(
            os.path.isdir(os.path.join(
                fetcher.tempdir, "var", "cache", "apt", "archives",
                "partial")))

    def test_prepare_creates_var_lib_apt_lists_partial_dir(self):
        fetcher = PackageFetcher([])
        self.addCleanup(fetcher.cleanup)
        fetcher.prepare()
        self.assertTrue(
            os.path.isdir(os.path.join(
                fetcher.tempdir, "var", "lib", "apt", "lists", "partial")))

    def test_prepare_creates_etc_apt_sources_list_file(self):
        source1 = self.useFixture(AptSource([]))
        source2 = self.useFixture(AptSource([]))
        fetcher = PackageFetcher(
            [source1.sources_entry, source2.sources_entry])
        self.addCleanup(fetcher.cleanup)
        fetcher.prepare()
        self.assertEqual(
            "deb %s\ndeb %s\n" % (
                source1.sources_entry, source2.sources_entry),
            open(os.path.join(
                fetcher.tempdir, "etc", "apt", "sources.list")).read())

    def get_fetcher(self, sources):
        fetcher = PackageFetcher([s.sources_entry for s in sources])
        self.addCleanup(fetcher.cleanup)
        fetcher.prepare()
        return fetcher

    def test_fetch_packages_not_found_because_no_sources(self):
        fetcher = self.get_fetcher([])
        self.assertRaises(KeyError, fetcher.fetch_packages, ["nothere"])

    def test_fetch_packages_not_found_because_not_in_sources(self):
        available_package = Package("foo", "1.0")
        source = self.useFixture(AptSource([available_package]))
        fetcher = self.get_fetcher([source])
        self.assertRaises(KeyError, fetcher.fetch_packages, ["nothere"])

    def test_fetch_packages_not_found_one_of_two_missing(self):
        available_package = Package("foo", "1.0")
        source = self.useFixture(AptSource([available_package]))
        fetcher = self.get_fetcher([source])
        self.assertRaises(
            KeyError, fetcher.fetch_packages, ["foo", "nothere"])

    def test_fetch_packges_fetches_no_packages(self):
        available_package = Package("foo", "1.0")
        source = self.useFixture(AptSource([available_package]))
        fetcher = self.get_fetcher([source])
        self.assertEqual(0, len(fetcher.fetch_packages([])))

    def test_fetch_packges_fetches_single_package(self):
        available_package = Package("foo", "1.0")
        source = self.useFixture(AptSource([available_package]))
        fetcher = self.get_fetcher([source])
        self.assertEqual(1, len(fetcher.fetch_packages(["foo"])))

    def test_fetch_packges_fetches_correct_filename(self):
        available_package = Package("foo", "1.0")
        source = self.useFixture(AptSource([available_package]))
        fetcher = self.get_fetcher([source])
        self.assertEqual(
            [available_package.filename],
            fetcher.fetch_packages(["foo"]).keys())

    def test_fetch_packges_fetches_correct_contents(self):
        available_package = Package("foo", "1.0")
        source = self.useFixture(AptSource([available_package]))
        fetcher = self.get_fetcher([source])
        self.assertEqual(
            available_package.content,
            fetcher.fetch_packages(
                ["foo"])[available_package.filename].read())

    def test_fetch_packges_fetches_multiple_packages(self):
        available_packages = [Package("bar", "1.0"), Package("foo", "1.0")]
        source = self.useFixture(AptSource(available_packages))
        fetcher = self.get_fetcher([source])
        self.assertEqual(2, len(fetcher.fetch_packages(["foo", "bar"])))

    def test_fetch_packges_fetches_multiple_packages_correctly(self):
        available_packages = [Package("bar", "1.0"), Package("foo", "1.0")]
        source = self.useFixture(AptSource(available_packages))
        fetcher = self.get_fetcher([source])
        fetched_contents = fetcher.fetch_packages(["foo", "bar"])
        self.assertEqual(
            dict([(p.filename, p.content) for p in available_packages]),
            dict([(fn, fetched_contents[fn].read())
                for fn in fetched_contents]))

    def test_fetch_packages_fetches_newest(self):
        available_packages = [Package("bar", "1.0"), Package("bar", "1.1")]
        source = self.useFixture(AptSource(available_packages))
        fetcher = self.get_fetcher([source])
        fetched_contents = fetcher.fetch_packages(["bar"])
        self.assertEqual(
            {available_packages[1].filename: available_packages[1].content},
            dict([(fn, fetched_contents[fn].read())
                for fn in fetched_contents]))

    def test_fetch_packages_fetches_newest_from_multiple_sources(self):
        old_source_packages = [Package("bar", "1.0")]
        new_source_packages = [Package("bar", "1.1")]
        old_source = self.useFixture(AptSource(old_source_packages))
        new_source = self.useFixture(AptSource(new_source_packages))
        fetcher = self.get_fetcher([old_source, new_source])
        fetched_contents = fetcher.fetch_packages(["bar"])
        self.assertEqual(
            {new_source_packages[0].filename: new_source_packages[0].content},
            dict([(fn, fetched_contents[fn].read())
                for fn in fetched_contents]))
