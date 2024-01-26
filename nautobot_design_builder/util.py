"""Main design builder app module, contains DesignJob and base methods and functions."""
import functools
import importlib
import inspect
import logging
import os
import pkgutil
import sys
from importlib.machinery import ModuleSpec
from types import ModuleType
from typing import Iterator, Tuple, Type, TYPE_CHECKING
from packaging.version import Version
import yaml

from django.conf import settings
import nautobot
from nautobot.extras.models import GitRepository


from nautobot_design_builder import metadata

if TYPE_CHECKING:
    from nautobot_design_builder.design_job import DesignJob
    from typing import Dict, List

logger = logging.getLogger(__name__)

DESIGN_BUILDER_ROOT_MODULE = "design_builder_designs"


def get_class_dir(cls) -> str:
    """Function to return the directory where a given path is stored.

    Returns:
        str: A path to a directory
    """
    return os.path.dirname(inspect.getfile(cls))


def load_design_yaml(cls, resource) -> "List | Dict":
    """Loads data from a YAML design file.

    Args:
        resource (str): name of the YAML design file without the path

    Returns:
        list or dict: list or dictionary containing data from YAML design files
    """
    return yaml.safe_load(load_design_file(cls, resource))


def load_design_file(cls, resource) -> str:
    """Reads data from a file and returns it as string.

    Args:
        resource (str): name of the YAML design file without the path

    Returns:
        str: contents of design file as string
    """
    with open(os.path.join(get_class_dir(cls), resource), encoding="UTF-8") as file:
        return file.read()


def load_design_package(path: str, package_name: str) -> Type[ModuleType]:
    """Load the package (__init__.py) from the path and assign it package_name.

    Args:
        path (str): _description_
        package_name (str): _description_

    Raises:
        ModuleNotFoundError: _description_

    Returns:
        _type_: _description_import
    """
    if DESIGN_BUILDER_ROOT_MODULE not in sys.modules:
        package_spec = ModuleSpec(name=DESIGN_BUILDER_ROOT_MODULE, loader=None)
        package = importlib.util.module_from_spec(package_spec)
        sys.modules[DESIGN_BUILDER_ROOT_MODULE] = package

    if package_name in sys.modules:
        return sys.modules[package_name]

    init_path = os.path.join(path, "__init__.py")
    try:
        package_spec = importlib.util.spec_from_file_location(package_name, init_path)
        package = importlib.util.module_from_spec(package_spec)
        sys.modules[package_name] = package
        package_spec.loader.exec_module(package)
        return package
    except FileNotFoundError:
        # pylint: disable=raise-missing-from
        raise ModuleNotFoundError(f"no module named '{package_name}' at {path}")


def load_design_module(path: str, package_name: str, module_name: str) -> Type[ModuleType]:
    """Load module_name from the path and set the parent package to package_name.

    Args:
        path (str): Path to directory containing the module.
        package_name (str): Name to give the loaded package.
        module_name (str): Name of the module to load from the path.

    Raises:
        ModuleNotFoundError: If the package cannot be found (missing __init__.py)
            or the module cannot be found.

    Returns:
        Type[ModuleType]: The loaded module.
    """
    if package_name not in sys.modules:
        load_design_package(path, package_name)

    package_path = f"{package_name}.{module_name}"

    importer = pkgutil.get_importer(path)
    spec = importer.find_spec(package_path)
    if spec:
        module = importlib.util.module_from_spec(spec)
        if spec.submodule_search_locations:
            module.__package__ = package_path
        else:
            module.__package__ = package_name
        sys.modules[package_path] = module
        spec.loader.exec_module(module)
        return module

    raise ModuleNotFoundError(f"no module named '{module_name}' at {path}")


def designs_in_directory(
    path,
    package_name: str,
    local_logger=logger,
    module_name: str = None,
    reload_modules=False,
) -> Iterator[Tuple[str, Type["DesignJob"]]]:
    """
    Walk the available Python modules in the given directory, and for each module, walk its DesignJob class members.

    Args:
        path (str): Directory to import modules from, outside of sys.path
        module_name (str): Specific module name to select; if unspecified, all modules will be inspected
        reload_modules (bool): Whether to force reloading of modules even if previously loaded into Python.

    Yields:
        ("package_name.module_name", "DesignJobClassName")
    """
    # this prevents a circular import
    from nautobot_design_builder.design_job import DesignJob  # pylint: disable=import-outside-toplevel

    def is_design(obj):
        try:
            return issubclass(obj, DesignJob) and obj is not DesignJob and not inspect.isabstract(obj)
        except TypeError:
            return False

    if reload_modules:
        for key in list(sys.modules.keys()):
            if key.startswith(package_name):
                del sys.modules[key]
    for _, discovered_module_name, _ in pkgutil.iter_modules([path]):
        if module_name and discovered_module_name != module_name:
            continue
        try:
            module = load_design_module(path, package_name, discovered_module_name)
        except Exception as ex:  # pylint:disable=broad-except
            local_logger.exception(f"Unable to load module {discovered_module_name} from {path}: {ex}")
            continue
        # Get all members of the module that are DesignJob subclasses
        for design_class_name, _ in inspect.getmembers(module, is_design):
            yield f"{package_name}.{discovered_module_name}", design_class_name


def package_name_for_repo(repo: GitRepository) -> str:
    """Generate the package name for a git repository.

    Args:
        repo (GitRepository): Git Repository containing some design builder designs

    Returns:
        str: package name, such as design_builder_designs.repo_slug
    """
    return f"{DESIGN_BUILDER_ROOT_MODULE}.{repo.slug.replace('.', '_').replace('-', '_')}"


def designs_in_repository(
    repo: GitRepository, local_logger=logger, module_name: str = None, reload_modules=False
) -> Iterator[Tuple[str, Type["DesignJob"]]]:
    """Iterate over the designs in a given git repository.

    Returns:
        Iterator: an iterator that will return tuples of package names and class names.

    For the following directory structure:
        repo-base-dir/designs/design1.py # containing class Design1(DesignJob)
        repo-base-dir/designs/design2.py # containing class Design2(DesignJob)

    The returned values will be yielded:
        ("repo_base_dir.design1", "Design1")
        ("repo_base_dir.design2", "Design2")

    Note that the package name is the full package name where the base package is
    a normalized version of the GitRepository slug. The name is normalized by replacing
    dashes and spaces with underscores and converting to lower case.

    The reason designs are loaded with a base package of the git repo slug is to
    prevent collisions of class names and modules between design repos and also
    to allow for designs spanning multiple files (breaking out contexts and so
    forth into other files).
    """
    package_name = package_name_for_repo(repo)
    path = os.path.join(repo.filesystem_path, "designs")
    for discovered_name, class_name in designs_in_directory(
        path, package_name, local_logger=local_logger, module_name=module_name, reload_modules=reload_modules
    ):
        yield discovered_name, class_name, path


def load_jobs(module_name=None):
    """Expose designs to the Nautobot Jobs framework.

    Args:
        module_name (str, optional): Module name to limit design discovery. Defaults to None.

    This method is used inside a jobs module to expose designs to Nautobot. Due
    to a limitation with the way jobs are loaded, it is not possible for jobs
    to be organized in multiple files. The `load_jobs` method essentially overcomes
    this limitation by discovering designs and creating dynamic classes within
    a jobs module.

    To use this method, create a jobs module like so:

        # jobs.py
        from nautobot_design_builder.util import load_jobs

        load_jobs()

    If designs are stored in different modules and that module separation
    is desired, then a module name can be supplied to the method:

        # jobs/tenant1.py
        from nautobot_design_builder.util import load_jobs

        load_jobs(module_name="tenant1")
    """
    frame = sys._getframe(1)  # pylint:disable=protected-access
    filename = frame.f_globals["__file__"]
    dirname = os.path.abspath(os.path.join(os.path.dirname(filename)))
    designs = {}
    is_local = dirname == settings.JOBS_ROOT
    if is_local:
        dirname = os.path.join(dirname, "..", "designs")
        package_name = f"{DESIGN_BUILDER_ROOT_MODULE}.local_designs"
        for discovered_name, class_name in designs_in_directory(
            dirname, package_name, module_name=module_name, reload_modules=True
        ):
            designs[class_name] = get_design_class(dirname, discovered_name, class_name)
    else:
        try:
            repo_slug = os.path.basename(os.path.abspath(os.path.join(dirname, "..")))
            repo = GitRepository.objects.get(slug=repo_slug)
            for discovered_name, class_name, module_path in designs_in_repository(
                repo, module_name=module_name, reload_modules=True
            ):
                designs[class_name] = get_design_class(module_path, discovered_name, class_name)
        except GitRepository.DoesNotExist:
            return

    if is_local:
        frame.f_globals["jobs"] = []

    for class_name, cls in designs.items():
        new_cls = type(class_name, (cls,), {})
        new_cls.__module__ = frame.f_globals["__name__"]
        frame.f_globals[class_name] = new_cls
        if is_local:
            frame.f_globals["jobs"].append(new_cls)


def get_design_class(path: str, module_name: str, class_name: str) -> Type["DesignJob"]:
    """Retrieve the Python class using a filesystem path, module name and class name.

    Args:
        path (str): filesystem path to the package containing the module.
        module_name (str): name of the module to load from the package.
        class_name (str): name of the class to load from the module.

    Returns:
        Type[DesignJob]: The class.
    """
    package_name, module_name = module_name.rsplit(".", 1)
    if package_name in sys.modules:
        del sys.modules[package_name]

    path = os.path.join(path)
    module = load_design_module(path, package_name, module_name)
    return getattr(module, class_name)


@functools.total_ordering
class _NautobotVersion:
    """Utility for comparing Nautobot versions."""

    def __init__(self):
        self.version = Version(metadata.version(nautobot.__name__))
        # This includes alpha/beta as version numbers
        self.version = Version(self.version.base_version)

    def __eq__(self, version_string):
        return self.version == Version(version_string)

    def __lt__(self, version_string):
        return self.version < Version(version_string)


nautobot_version = _NautobotVersion()
