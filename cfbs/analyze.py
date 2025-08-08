from collections import OrderedDict
import os
from typing import Tuple, Union
import copy

from cfbs.internal_file_management import fetch_archive
from cfbs.masterfiles.analyze import (
    highest_version,
    sort_versions,
    version_as_comparable_list,
)
from cfbs.utils import (
    CFBSNetworkError,
    cfbs_dir,
    deduplicate_list,
    fetch_url,
    file_sha256,
    get_json,
    immediate_subdirectories,
    mkdir,
    read_json,
    CFBSExitError,
)


def path_components(path):
    """Returns a list of path components of `path`.

    The first component is `""` for a path starting with a separator. On Windows, if `path` begins with n backslashes, the first n components will be `""`.

    The last component is the name of the file or directory, trailing separators do not affect the result.
    """
    norm_path = os.path.normpath(path)

    dir_components = norm_path.split(os.sep)

    return dir_components


def name(path):
    """Returns the name of the path to file or directory."""
    return path_components(path)[-1]


def is_path_component(path, component):
    """Returns whether `component` is a path component of `path`."""
    p_components = path_components(path)

    # check if `component` is a directory or a file
    if component[-1] == "/":
        # strip the suffixed directory slash
        component = component[:-1]

        return component in p_components[:-1]
    else:
        return component == p_components[-1]


def contains_ignored_components(path, ignored_components):
    """Returns whether `path` contains any of the path components in `ignored_components`."""
    for i_comp in ignored_components:
        if is_path_component(path, i_comp):
            return True

    return False


DEFAULT_CHECKSUMS_DICT = {"checksums": {}}
DEFAULT_FILES_DICT = {"files": {}}


def checksums_files(
    files_dir_path,
    checksums_dict=None,
    files_dict=None,
    ignored_path_components=[],
):
    if checksums_dict is None:
        checksums_dict = copy.deepcopy(DEFAULT_CHECKSUMS_DICT)
    if files_dict is None:
        files_dict = copy.deepcopy(DEFAULT_FILES_DICT)

    for root, _, files in os.walk(files_dir_path):
        for name in files:
            full_relpath = os.path.join(root, name)
            tarball_relpath = os.path.relpath(full_relpath, files_dir_path)
            file_checksum = file_sha256(full_relpath)

            if contains_ignored_components(full_relpath, ignored_path_components):
                continue

            if file_checksum not in checksums_dict["checksums"]:
                checksums_dict["checksums"][file_checksum] = set()
            checksums_dict["checksums"][file_checksum].add(tarball_relpath)

            if tarball_relpath not in files_dict["files"]:
                files_dict["files"][tarball_relpath] = set()
            files_dict["files"][tarball_relpath].add(file_checksum)

    return checksums_dict, files_dict


def mpf_vcf_dicts(offline=False):
    """(vcf stands for versions, checksums, files)"""
    REPO_OWNER = "cfengine"
    REPO_NAME = "release-information"

    REPO_OWNERNAME = REPO_OWNER + "/" + REPO_NAME
    # RI stands for release information
    RI_SUBDIRS = "downloads/github.com/" + REPO_OWNERNAME + "/archive/refs/tags/"

    if offline:
        ERROR_MESSAGE = (
            "Masterfiles Policy Framework release information not found. "
            + "Provide the release information, for example by running 'cfbs analyze' without '--offline'."
        )

        cfbs_ri_dir = os.path.join(cfbs_dir(), RI_SUBDIRS)
        if not os.path.exists(cfbs_ri_dir):
            raise CFBSExitError(ERROR_MESSAGE)

        ri_versions = immediate_subdirectories(cfbs_ri_dir)
        if len(ri_versions) == 0:
            raise CFBSExitError(ERROR_MESSAGE)

        ri_latest_version = max(ri_versions)
        mpf_vcf_path = os.path.join(
            cfbs_ri_dir,
            ri_latest_version,
            REPO_NAME + "-" + ri_latest_version,
            "masterfiles",
        )
    else:
        REPO_URL = "https://github.com/" + REPO_OWNERNAME
        LATEST_RELEASE_API_URL = (
            "https://api.github.com/repos/" + REPO_OWNERNAME + "/releases/latest"
        )

        try:
            latest_release_data = get_json(LATEST_RELEASE_API_URL)
        except CFBSNetworkError:
            raise CFBSExitError(
                "Downloading CFEngine release information failed - check your Wi-Fi / network settings."
            )

        latest_release_name = latest_release_data["name"]
        ri_archive_url = REPO_URL + "/archive/refs/tags/" + latest_release_name + ".zip"
        ri_checksums_url = (
            REPO_URL + "/releases/download/" + latest_release_name + "/checksums.txt"
        )
        ri_version_subdirs = RI_SUBDIRS + latest_release_name
        ri_version_path = os.path.join(cfbs_dir(), ri_version_subdirs)
        mpf_vcf_subdirs = REPO_NAME + "-" + latest_release_name + "/masterfiles/"
        mpf_vcf_path = os.path.join(ri_version_path, mpf_vcf_subdirs)

        if not os.path.exists(mpf_vcf_path):
            mkdir(ri_version_path)

            archive_checksums_path = ri_version_path + "/checksums.txt"
            try:
                fetch_url(ri_checksums_url, archive_checksums_path)
            except CFBSNetworkError as e:
                raise CFBSExitError(str(e))

            with open(archive_checksums_path) as file:
                lines = [line.rstrip() for line in file]
                zip_line = lines[1]
                zip_checksum = zip_line.split(" ")[0]

            fetch_archive(
                ri_archive_url,
                zip_checksum,
                directory=ri_version_path,
                with_index=False,
                extract_to_directory=True,
            )

    mpf_versions_json_path = os.path.join(mpf_vcf_path, "versions.json")
    mpf_checkfiles_json_path = os.path.join(mpf_vcf_path, "checksums.json")
    mpf_files_json_path = os.path.join(mpf_vcf_path, "files.json")

    mpf_versions_dict = read_json(mpf_versions_json_path)
    assert mpf_versions_dict is not None

    mpf_versions_dict = mpf_versions_dict["versions"]

    mpf_checksums_dict = read_json(mpf_checkfiles_json_path)
    assert mpf_checksums_dict is not None
    mpf_checksums_dict = mpf_checksums_dict["checksums"]

    mpf_files_dict = read_json(mpf_files_json_path)
    assert mpf_files_dict is not None
    mpf_files_dict = mpf_files_dict["files"]

    return mpf_versions_dict, mpf_checksums_dict, mpf_files_dict


def filepaths_sorted(filepaths):
    """Currently sorts alphabetically, not hierarchically."""
    return sorted(filepaths)


def filepaths_display(filepaths):
    filepaths = filepaths_sorted(filepaths)

    for path in filepaths[:-1]:
        print("├──", path)
    if len(filepaths) > 0:
        print("└──", filepaths[-1])


def list_or_single(elements):
    if len(elements) == 1:
        return elements[0]
    return elements


def filepaths_display_moved(filepaths):
    filepaths = filepaths_sorted(filepaths)

    for path in filepaths[:-1]:
        print("├──", path[0], "<-", list_or_single(path[1]))
    if len(filepaths) > 0:
        print("└──", filepaths[-1][0], "<-", list_or_single(filepaths[-1][1]))


def mpf_normalized_path(path, is_parentpath: bool, masterfiles_dir):
    """Returns a filepath converted from `path` to an MPF-comparable form.

    `path` should be a path inside the masterfiles directory (or inside the parent directory, if `is_parentpath` is `True`).
    """
    # downloaded MPF release information filepaths always have forward slashes
    norm_path = path.replace(os.sep, "/")

    if is_parentpath:
        if norm_path.startswith(masterfiles_dir + "/"):
            norm_path = os.path.relpath(norm_path, masterfiles_dir)
            # `os.path.relpath` will still output paths with `os.sep`, even if `norm_path` uses forward slashes on e.g. Windows
            norm_path = norm_path.replace(os.sep, "/")
            norm_path = "masterfiles/" + norm_path
    else:
        norm_path = "masterfiles/" + norm_path

    return norm_path


def mpf_denormalized_path(path, is_parentpath, masterfiles_dir):
    """Inverse function of `mpf_normalized_path`."""
    denorm_path = path
    # this does work as intended even if the first dir isn't masterfiles and there's a masterfiles dir deeper in the path
    relpath = os.path.relpath(denorm_path, "masterfiles")

    if is_parentpath:
        # if `"masterfiles"`, substitute to `masterfiles_dir`
        # if not, then the path should stay the same
        if not relpath.startswith(".." + os.sep):
            denorm_path = os.path.join(masterfiles_dir, relpath)

    else:
        # this will work as intended even for other directories than `masterfiles` e.g. `modules`
        denorm_path = relpath

    return denorm_path


class VersionsCounter:
    def __init__(self):
        self._versions_counts = {}

    def increment(self, version):
        if version not in self._versions_counts:
            self._versions_counts[version] = 0
        self._versions_counts[version] += 1

    def most_common_version(self):
        """Returns version with the highest count. In case of a tie, returns the highest version with the highest count."""
        highest_count = max(self._versions_counts.values(), default=0)

        versions_with_highest_count = [
            k for (k, v) in self._versions_counts.items() if v == highest_count
        ]

        return highest_version(versions_with_highest_count)

    def sorted_list(self):
        """Returns a sorted list of key-value pairs `(version, count)`.
        The sorting is in descending order. In case of a count tie,
        the higher version's pair is considered greater."""
        return sorted(
            self._versions_counts.items(),
            key=lambda item: (item[1], version_as_comparable_list(item[0])),
            reverse=True,
        )

    def is_empty(self):
        return self._versions_counts == {}


class VersionsData:
    def __init__(self):
        self.version_counter = VersionsCounter()
        self.highest_version_counter = VersionsCounter()
        # acronyms: vc = version_counter, hvc = highest_version_counter
        self.different_filepath_vc = VersionsCounter()
        self.different_filepath_hvc = VersionsCounter()

    def display(self, verbose=False):
        if not self.version_counter.is_empty():
            if verbose:
                print(
                    "Same filepath versions distribution:",
                    self.version_counter.sorted_list(),
                )
            if verbose:
                print(
                    "Same filepath highest versions distribution:",
                    self.highest_version_counter.sorted_list(),
                )
        if not self.different_filepath_vc.is_empty():
            if verbose:
                print(
                    "Different filepath versions distribution:",
                    self.different_filepath_vc.sorted_list(),
                )
            if verbose:
                print(
                    "Different filepath highest versions distribution:",
                    self.different_filepath_hvc.sorted_list(),
                )
        if self.version_counter.is_empty() and self.different_filepath_vc.is_empty():
            print(
                "Not a single file in the analyzed policy set appears in the Masterfiles Policy Framework.\n"
            )
        elif verbose:
            print()

    def to_json_dict(self):
        json_dict = OrderedDict()

        json_dict["same_filepath_versions"] = self.version_counter.sorted_list()
        json_dict["same_filepath_highest_versions"] = (
            self.highest_version_counter.sorted_list()
        )
        json_dict["different_filepath_versions"] = (
            self.different_filepath_vc.sorted_list()
        )
        json_dict["different_filepath_highest_versions"] = (
            self.different_filepath_hvc.sorted_list()
        )

        return json_dict


class AnalyzedFiles:
    def __init__(self, reference_version: Union[str, None]):
        self.reference_version = reference_version

        self.unmodified = []
        self.missing = []
        self.modified = []
        self.moved_or_renamed = []
        self.different = []
        self.different_modified = []
        self.different_moved_or_renamed = []
        self.not_from_any = []

    @staticmethod
    def _denormalize_origin(origin, is_parentpath, masterfiles_dir):
        return [
            (mpf_denormalized_path(filepath, is_parentpath, masterfiles_dir), versions)
            for (filepath, versions) in origin.items()
        ]

    def denormalize(self, is_parentpath, masterfiles_dir):
        """Currently irreversible and meant to only be used once after all the files are analyzed."""

        self.unmodified = [
            mpf_denormalized_path(file, is_parentpath, masterfiles_dir)
            for file in self.unmodified
        ]
        self.missing = [
            mpf_denormalized_path(file, is_parentpath, masterfiles_dir)
            for file in self.missing
        ]
        self.modified = [
            mpf_denormalized_path(file, is_parentpath, masterfiles_dir)
            for file in self.modified
        ]
        self.moved_or_renamed = [
            (
                mpf_denormalized_path(file, is_parentpath, masterfiles_dir),
                [
                    mpf_denormalized_path(o_f, is_parentpath, masterfiles_dir)
                    for o_f in origin_filepaths
                ],
            )
            for (file, origin_filepaths) in self.moved_or_renamed
        ]
        self.different = [
            (
                mpf_denormalized_path(file, is_parentpath, masterfiles_dir),
                other_versions,
            )
            for (file, other_versions) in self.different
        ]
        self.different_modified = [
            (
                mpf_denormalized_path(file, is_parentpath, masterfiles_dir),
                other_versions,
            )
            for (file, other_versions) in self.different_modified
        ]
        self.different_moved_or_renamed = [
            (
                mpf_denormalized_path(file, is_parentpath, masterfiles_dir),
                AnalyzedFiles._denormalize_origin(
                    origin, is_parentpath, masterfiles_dir
                ),
            )
            for (file, origin) in self.different_moved_or_renamed
        ]
        self.not_from_any = [
            mpf_denormalized_path(file, is_parentpath, masterfiles_dir)
            for file in self.not_from_any
        ]

    def sort(self):
        self.unmodified = filepaths_sorted(self.unmodified)
        self.missing = filepaths_sorted(self.missing)
        self.modified = filepaths_sorted(self.modified)
        self.moved_or_renamed = filepaths_sorted(self.moved_or_renamed)
        self.different = filepaths_sorted(self.different)
        self.different_modified = filepaths_sorted(self.different_modified)
        self.different_moved_or_renamed = filepaths_sorted(
            self.different_moved_or_renamed
        )
        self.not_from_any = filepaths_sorted(self.not_from_any)

    def display(self, display_unmodified=False):
        print("Reference version:", self.reference_version, "\n")

        if display_unmodified:
            if len(self.unmodified) > 0:
                print("Files unmodified from the version:")
            filepaths_display(self.unmodified)

        if len(self.missing) > 0:
            print("Files missing from the version:")
        elif self.reference_version is not None:
            print("No files are missing from the version.")
        filepaths_display(self.missing)

        if len(self.modified) == 0 and len(self.moved_or_renamed) == 0:
            print("No files of the version are modified.")
        if len(self.modified) > 0:
            print("Files from the version but with modifications:")
        filepaths_display(self.modified)
        if len(self.moved_or_renamed) > 0:
            print("Files moved or renamed:")
        filepaths_display_moved(self.moved_or_renamed)

        if (
            len(self.different) == 0
            and len(self.different_modified) == 0
            and len(self.different_moved_or_renamed) == 0
        ):
            print("No files are from a different version.")
        if len(self.different) > 0:
            print("Files from a different version:")
        filepaths_display(self.different)
        if len(self.different_modified) > 0:
            print("Files from a different version, with modifications:")
        filepaths_display(self.different_modified)
        if len(self.different_moved_or_renamed) > 0:
            print("Files moved or renamed from a different version:")
        filepaths_display_moved(self.different_moved_or_renamed)

        if len(self.not_from_any) > 0:
            print("Files not from any version (with both custom content and path):")
        else:
            print("No files are not from any version.")
        filepaths_display(self.not_from_any)

    def to_json_dict(self):
        self.sort()

        json_dict = OrderedDict()

        json_dict["reference_version"] = self.reference_version

        json_dict["files"] = {}

        json_dict["files"]["unmodified"] = self.unmodified
        json_dict["files"]["missing"] = self.missing
        json_dict["files"]["modified"] = self.modified
        json_dict["files"]["moved_or_renamed"] = self.moved_or_renamed
        json_dict["files"]["different_version"] = self.different
        json_dict["files"]["different_version_modified"] = self.different_modified
        json_dict["files"][
            "different_version_moved_or_renamed"
        ] = self.different_moved_or_renamed
        json_dict["files"]["not_from_any_version"] = self.not_from_any

        return json_dict


DEFAULT_IGNORED_PATH_COMPONENTS = [
    # VCS files - Git:
    ".git/",
    ".gitignore",
    ".gitattributes",
    # infrastructure configuration files - GitHub:
    ".github/",
    # CFEngine policy distribution generated files:
    "cf_promises_release_id",
    "cf_promises_validated",
]


def possible_policyset_paths(path, masterfiles_dir, is_parentpath, files_dict):
    """Returns a list of possible policy-set paths inside an analyzed `path`.

    The returned paths are in the form of relative paths to `path`.
    """
    possible_policyset_relpaths = []

    for filepath in files_dict:
        file_name = name(filepath)
        if file_name in ("promises.cf", "update.cf"):
            actual_filepath = mpf_denormalized_path(
                filepath, is_parentpath, masterfiles_dir
            )
            # `checksums_files` output paths relative to its `files_dir_path` argument,
            # therefore `actual_filepath` is now relative to the user-provided path already

            filepath_dir = os.path.dirname(actual_filepath)
            possible_policyset_relpaths.append(filepath_dir)

    # for drive root, the path's parent is the path itself, so only check the parent path if this is not the case
    if os.path.realpath(path) != os.path.realpath(os.path.join(path, "..")):
        if os.path.exists(os.path.join(path, "..", "update.cf")) or os.path.exists(
            os.path.join(path, "..", "promises.cf")
        ):
            possible_policyset_relpaths.append("..")

    possible_policyset_relpaths = deduplicate_list(possible_policyset_relpaths)

    return possible_policyset_relpaths


def analyze_policyset(
    path,
    is_parentpath=False,
    reference_version=None,
    masterfiles_dir="masterfiles",
    ignored_path_components=None,
    offline=False,
) -> Tuple[AnalyzedFiles, VersionsData]:
    """`path` should be either a masterfiles-path (containing masterfiles files directly),
    or a parent-path (containing `masterfiles_dir` and "modules" folders). `is_parentpath`
    should specify which of the two it is.

    The analysis ignores policyset (not MPF release information) files whose filepaths
    contain any of the path components specified in `ignored_path_components`.
    Components in `ignored_path_components` should end with a `/` if the component
    represents a directory (also on operating systems using a different separator
    e.g. a backslash), and should not end with a `/` if it represents a file.
    """
    if ignored_path_components is None:
        ignored_path_components = copy.deepcopy(DEFAULT_IGNORED_PATH_COMPONENTS)

    checksums_dict, files_dict = checksums_files(
        path, ignored_path_components=ignored_path_components
    )
    checksums_dict = checksums_dict["checksums"]
    files_dict = files_dict["files"]

    # MPF filepath data contains "masterfiles/" (which might not be the same as `masterfiles_dir + "/"`) and "modules/" at the beginning of the filepaths
    # therefore, care is needed comparing policyset filepaths to MPF filepaths
    # before such comparing, convert the policyset filepaths to an MPF-comparable form using `mpf_normalized_path`
    mpf_versions_dict, mpf_checksums_dict, mpf_files_dict = mpf_vcf_dicts(offline)

    # as mentioned above, normalize the analyzed policyset filepaths to be of the same form as filepaths in MPF dicts so that the two can be compared
    for checksum in checksums_dict:
        checksums_dict[checksum] = {
            mpf_normalized_path(file, is_parentpath, masterfiles_dir)
            for file in checksums_dict[checksum]
        }
    files_dict = {
        mpf_normalized_path(file, is_parentpath, masterfiles_dir): checksums
        for file, checksums in files_dict.items()
    }

    versions_data = VersionsData()

    # first, count versions in order to find the reference version:
    for checksum, files_of_checksum in checksums_dict.items():
        filepaths_highest_versions = {}
        dfv_fhv = {}  # acronym for different_filepath_vc_filepaths_highest_versions

        if checksum in mpf_checksums_dict:
            # 1A. checksum known:
            checksum_mpf_files_dict = mpf_checksums_dict[checksum]

            for filepath in files_of_checksum:
                if filepath in checksum_mpf_files_dict:
                    # 1A1. a match of both checksum and filepath:
                    for version in checksum_mpf_files_dict[filepath]:
                        versions_data.version_counter.increment(version)

                    filepaths_highest_versions[filepath] = highest_version(
                        checksum_mpf_files_dict[filepath]
                    )
                else:
                    # 1A2. there are files with the same checksum in MPF but not the same filepath:
                    if filepath in mpf_files_dict:
                        # 1A2A. filepath exists somewhere else but not for this checksum:
                        filepath_versions = []
                        for mpf_checksum in mpf_files_dict[filepath]:
                            filepath_versions += mpf_files_dict[filepath][mpf_checksum]
                        for version in filepath_versions:
                            versions_data.different_filepath_vc.increment(version)
                        dfv_fhv[filepath] = highest_version(filepath_versions)
                    else:
                        # 1A2B. checksum exists but filepath is not known:
                        # there are no versions to count since the filepath is not known
                        pass

        for filepath in files_of_checksum:
            if filepath in filepaths_highest_versions:
                versions_data.highest_version_counter.increment(
                    filepaths_highest_versions[filepath]
                )
            if filepath in dfv_fhv:
                versions_data.different_filepath_hvc.increment(dfv_fhv[filepath])

    if reference_version is None:
        reference_version = versions_data.version_counter.most_common_version()

    # if not a single file in the analyzed policyset has an MPF-known (checksum, filepath),
    # and a specific `reference_version` was not given, `reference_version` will still be `None`
    if reference_version is None:
        # try to detect whether the user provided a wrong policy set path
        # gather all possible policy set paths, by detecting promises.cf or update.cf
        possible_policyset_relpaths = possible_policyset_paths(
            path, masterfiles_dir, is_parentpath, files_dict
        )

        # check whether the policy set contains update.cf or promises.cf directly in masterfiles
        # `os.path.dirname` results in `''` rather than `'.'` for current directory
        if not (
            (masterfiles_dir if is_parentpath else "") in possible_policyset_relpaths
        ):
            extra_error_text = ""
            if len(possible_policyset_relpaths) > 0:
                extra_error_text = (
                    "Did you mean to provide one of the following paths (or their parent paths), relative to the provided path, instead?:\n  "
                    + "\n  ".join(possible_policyset_relpaths)
                    + "\n"
                )
            raise CFBSExitError(
                "There doesn't seem to be a valid policy set in the supplied path.\n       Usage: cfbs analyze path/to/policy-set\n"
                + extra_error_text
            )

        reference_version_files = []
        reference_version_checksums = {}
    else:
        reference_version_files = mpf_versions_dict[reference_version].keys()
        reference_version_checksums = {}
        for mpf_filepath in mpf_versions_dict[reference_version]:
            mpf_checksum = mpf_versions_dict[reference_version][mpf_filepath]
            if mpf_checksum not in reference_version_checksums:
                reference_version_checksums[mpf_checksum] = []
            reference_version_checksums[mpf_checksum].append(mpf_filepath)

    analyzed_files = AnalyzedFiles(reference_version)

    # categorize all files, based on their relation with the reference version and known MPF files:
    # 1. files present:
    for checksum, files_of_checksum in checksums_dict.items():
        if checksum in mpf_checksums_dict:
            # 1A. checksum known:
            checksum_mpf_files_dict = mpf_checksums_dict[checksum]

            for filepath in files_of_checksum:
                if filepath in checksum_mpf_files_dict:
                    # 1A1. (checksum, filepath) known:
                    # check whether the (checksum, filepath) is in the reference version
                    if (
                        filepath not in reference_version_files
                    ) or checksum != mpf_versions_dict[reference_version][filepath]:
                        # 1A1A. the file is modified to the same filepath of a different version:
                        other_versions = mpf_checksums_dict[checksum][filepath]
                        # since MPF data is sorted, so is `other_versions`
                        analyzed_files.different.append((filepath, other_versions))
                    else:
                        # 1A1B. the file is unmodified and present in the reference version
                        analyzed_files.unmodified.append(filepath)
                else:
                    # 1A2. checksum is known but there's no matching filepath with that checksum:
                    # therefore, it must be a rename/move
                    origin = mpf_checksums_dict[checksum]
                    if checksum in reference_version_checksums:
                        origin_filepaths = origin.keys()
                        analyzed_files.moved_or_renamed.append(
                            (filepath, origin_filepaths)
                        )
                    else:
                        analyzed_files.different_moved_or_renamed.append(
                            (filepath, origin)
                        )
        else:
            # 1B. checksum unknown:
            for filepath in files_of_checksum:
                if filepath in mpf_files_dict:
                    # 1B1. filepath is known:
                    if filepath in reference_version_files:
                        analyzed_files.modified.append(filepath)
                    else:
                        other_versions = []
                        for checksum in mpf_files_dict[filepath]:
                            versions_list = mpf_files_dict[filepath][checksum]
                            other_versions.extend(versions_list)
                        sort_versions(other_versions)
                        analyzed_files.different_modified.append(
                            (filepath, other_versions)
                        )
                else:
                    analyzed_files.not_from_any.append(filepath)
    # 2. files missing from the reference version:
    for filepath in reference_version_files:
        if filepath not in files_dict:
            # the file is missing, but only if it's not present in any origin in moved_or_renamed
            is_present = False
            for _, origin_filepaths in analyzed_files.moved_or_renamed:
                if filepath in origin_filepaths:
                    is_present = True
                    break
            if not is_present:
                analyzed_files.missing.append(filepath)

    # denormalize filepaths in all the analyzed files lists for display
    analyzed_files.denormalize(is_parentpath, masterfiles_dir)

    return analyzed_files, versions_data
