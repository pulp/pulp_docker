"""
This migration moves the published content from /var/lib/pulp/published/docker/ to
/var/lib/pulp/published/docker/v1/.
"""
import os
import shutil

from pulp.plugins.util import misc


OLD_DOCKER_V1_PUBLISH_PATH = os.path.join('/', 'var', 'lib', 'pulp', 'published', 'docker')
NEW_DOCKER_V1_PUBLISH_PATH = os.path.join(OLD_DOCKER_V1_PUBLISH_PATH, 'v1')


def migrate():
    """
    Move all files and directories from /var/lib/pulp/published/docker/ to
    /var/lib/pulp/published/docker/v1/.
    """
    misc.mkdir(NEW_DOCKER_V1_PUBLISH_PATH)

    for folder in os.listdir(OLD_DOCKER_V1_PUBLISH_PATH):
        if folder == 'v1':
            continue
        source_folder = os.path.join(OLD_DOCKER_V1_PUBLISH_PATH, folder)
        destination_folder = os.path.join(NEW_DOCKER_V1_PUBLISH_PATH, folder)
        if os.path.exists(source_folder) and not os.path.exists(destination_folder):
            shutil.move(source_folder, NEW_DOCKER_V1_PUBLISH_PATH)

    # Now we must look for and repair broken symlinks
    _repair_links()


def _fix_link(path):
    """
    Adjust the link at path to reference the new publish path instead of the old publish path.

    :param path: The path to the link that needs to be fixed
    :type  path: basestring
    """
    link_target = os.readlink(path)
    new_target = link_target.replace(OLD_DOCKER_V1_PUBLISH_PATH, NEW_DOCKER_V1_PUBLISH_PATH)
    os.unlink(path)
    os.symlink(new_target, path)


def _link_broken(path):
    """
    Return True if the path is a broken symlink, False otherwise.

    :param path: The path to be checked
    :type  path: basestring
    :return:     True if the path is a broken symlink, False otherwise
    :rtype:      bool
    """
    if not os.path.islink(path):
        # We only need to adjust symlinks, so we can move on
        return False
    link_target = os.readlink(path)
    if link_target.startswith(NEW_DOCKER_V1_PUBLISH_PATH):
        # This link is already adjusted to point to the new v1 location, so we don't need to
        # do anything
        return False
    if link_target.startswith(OLD_DOCKER_V1_PUBLISH_PATH):
        return True
    return False


def _repair_links():
    """
    Walk the directory tree, looking for symlinks to /var/lib/pulp/published/docker instead of
    /var/lib/pulp/published/docker/v1 and fix them.
    """
    for dirpath, dirnames, filenames in os.walk(NEW_DOCKER_V1_PUBLISH_PATH):
        for dirname in dirnames:
            full_path = os.path.join(dirpath, dirname)
            if _link_broken(full_path):
                _fix_link(full_path)
        for filename in filenames:
            full_path = os.path.join(dirpath, filename)
            if _link_broken(full_path):
                _fix_link(full_path)
