"""Test loading designs from git."""
import inspect
import os
import sys
from collections import namedtuple
from unittest.mock import Mock

from django.conf import settings
from django.test import TestCase

from nautobot_design_builder.util import designs_in_repository, load_design_module, load_design_package

DESIGN_FILE_1 = """
from nautobot_design_builder.design_job import DesignJob

class Design1(DesignJob):
    class Meta:
        pass
"""

DESIGN_FILE_2_3 = """
from nautobot_design_builder.design_job import DesignJob

class Design2(DesignJob):
    class Meta:
        pass

class Design3(DesignJob):
    class Meta:
        pass

"""

DESIGN_FILE_3 = """
from nautobot_design_builder.design_job import DesignJob

class Design3(DesignJob):
    class Meta:
        pass
"""

DESIGN_FILE_4 = """
from nautobot_design_builder.design_job import DesignJob

# This file has an intentional syntax error
class Design4(DesignJob):
"""

DATASOURCE_IDENTIFIER = "extras.jobs"


def _create_file(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf8") as file:
        file.write(content)


def _create_module(path, content=""):
    _create_file(os.path.join(path, "__init__.py"), content)


class TestBase(TestCase):
    """Base class for tests."""

    def setUp(self) -> None:
        super().setUp()
        self.repo_class = namedtuple("GitRepository", "provided_contents current_head filesystem_path slug")
        self.repo_paths = []

    def tearDown(self) -> None:
        super().tearDown()

        def rmdir(path):
            for filename in os.listdir(path):
                file = os.path.join(path, filename)
                if os.path.isdir(file):
                    rmdir(file)
                else:
                    os.remove(os.path.join(path, filename))
            os.rmdir(path)

        for path in self.repo_paths:
            rmdir(path)

    def get_repo(
        self, provided_contents, slug, create_design_directory=True
    ):  # pylint: disable=missing-function-docstring
        repo_path = os.path.join(settings.GIT_ROOT, slug)
        if create_design_directory:
            design_path = os.path.join(repo_path, "designs")
            _create_module(design_path)
            self.repo_paths.append(design_path)
        else:
            os.makedirs(repo_path, exist_ok=True)
        self.repo_paths.append(repo_path)
        return self.repo_class(provided_contents, "main", repo_path, slug)


class TestModuleLoading(TestBase):
    """Test that designs are loaded correctly."""

    def test_load_design_package(self):
        package_name = "design_builder_designs.module_loading"
        repo = self.get_repo(DATASOURCE_IDENTIFIER, "module-loading")
        package1 = load_design_package(os.path.join(repo.filesystem_path, "designs"), package_name)
        self.assertEqual(package_name, package1.__name__)
        self.assertIs(sys.modules[package_name], package1)

        # check caching
        package2 = load_design_package(os.path.join(repo.filesystem_path, "designs"), package_name)
        self.assertIs(package1, package2)

        # check re-loading
        del sys.modules[package_name]
        package2 = load_design_package(os.path.join(repo.filesystem_path, "designs"), package_name)
        self.assertIsNot(package1, package2)

        del sys.modules[package_name]

    def test_package_not_found(self):
        package_name = "sample_repo"
        self.assertRaises(ModuleNotFoundError, load_design_package, "/no/repo/here", package_name)

    def test_load_design_module(self):
        package_name = "design_builder_designs.load_design_module"
        repo = self.get_repo(DATASOURCE_IDENTIFIER, "load-design-module")
        _create_file(os.path.join(repo.filesystem_path, "designs", "load_design_module.py"), DESIGN_FILE_1)
        module1 = load_design_module(os.path.join(repo.filesystem_path, "designs"), package_name, "load_design_module")
        self.assertTrue(hasattr(module1, "Design1"), f"{package_name}.design.py should have a Design1 class")
        self.assertTrue(inspect.isclass(module1.Design1), "Design1 should be a class")
        self.assertIn(f"{package_name}.load_design_module", sys.modules)
        self.assertIs(sys.modules[f"{package_name}.load_design_module"], module1)

        # load_design_module should always return a new/reloaded module
        module2 = load_design_module(os.path.join(repo.filesystem_path, "designs"), package_name, "load_design_module")
        self.assertIsNot(module1, module2)
        self.assertIs(sys.modules[f"{package_name}.load_design_module"], module2)

        del sys.modules[package_name]

    def test_module_not_found(self):
        package_name = "design_builder_designs.module_not_found"
        repo = self.get_repo(DATASOURCE_IDENTIFIER, "module-not-found")
        self.assertRaises(
            ModuleNotFoundError,
            load_design_module,
            os.path.join(repo.filesystem_path, "designs"),
            package_name,
            "design",
        )

        del sys.modules[package_name]


class TestDesignDiscovery(TestBase):
    """Test that designs are discovered correctly."""

    def test_single_design_in_one_file(self):
        repo = self.get_repo(DATASOURCE_IDENTIFIER, "single-design-one-file")
        _create_file(os.path.join(repo.filesystem_path, "designs", "single_design_one_file.py"), DESIGN_FILE_1)
        want_designs = [
            (
                "design_builder_designs.single_design_one_file.single_design_one_file",
                "Design1",
                os.path.join(repo.filesystem_path, "designs"),
            )
        ]
        got_designs = list(designs_in_repository(repo))
        self.assertEqual(want_designs, got_designs)

    def test_multiple_designs_in_one_file(self):
        repo = self.get_repo(DATASOURCE_IDENTIFIER, "multiple-designs-one-file")
        _create_file(os.path.join(repo.filesystem_path, "designs", "multiple_designs_one_file.py"), DESIGN_FILE_2_3)
        want_designs = [
            (
                "design_builder_designs.multiple_designs_one_file.multiple_designs_one_file",
                "Design2",
                os.path.join(repo.filesystem_path, "designs"),
            ),
            (
                "design_builder_designs.multiple_designs_one_file.multiple_designs_one_file",
                "Design3",
                os.path.join(repo.filesystem_path, "designs"),
            ),
        ]
        got_designs = list(designs_in_repository(repo))
        self.assertEqual(want_designs, got_designs)

    def test_multiple_designs_in_multiple_files(self):
        repo = self.get_repo(DATASOURCE_IDENTIFIER, "multiple-designs-multiple-files")
        _create_file(
            os.path.join(repo.filesystem_path, "designs", "multiple_designs_multiple_files1.py"), DESIGN_FILE_1
        )
        _create_file(
            os.path.join(repo.filesystem_path, "designs", "multiple_designs_multiple_files2.py"), DESIGN_FILE_3
        )
        want_designs = [
            (
                "design_builder_designs.multiple_designs_multiple_files.multiple_designs_multiple_files1",
                "Design1",
                os.path.join(repo.filesystem_path, "designs"),
            ),
            (
                "design_builder_designs.multiple_designs_multiple_files.multiple_designs_multiple_files2",
                "Design3",
                os.path.join(repo.filesystem_path, "designs"),
            ),
        ]
        got_designs = list(designs_in_repository(repo))
        self.assertEqual(want_designs, got_designs)

    def test_single_errored_design_in_one_file(self):
        repo = self.get_repo(DATASOURCE_IDENTIFIER, "single-errored-design")
        _create_file(os.path.join(repo.filesystem_path, "designs", "single_errored_design.py"), DESIGN_FILE_4)
        want_designs = []
        mock_logger = Mock()
        got_designs = list(designs_in_repository(repo, local_logger=mock_logger))
        self.assertEqual(want_designs, got_designs)

        got_args = mock_logger.exception.call_args[0]
        self.assertIn(f"Unable to load module single_errored_design from {repo.filesystem_path}/designs:", got_args[0])
