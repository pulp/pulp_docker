class Version:
    """
    Represents a version of a Skopeo Directory Transport version file.

    This class enables rich comparisons between versions. All comparisons are implemented because
    functools.total_ordering is not available in Python 2.6.
    """
    def __init__(self, version):
        """
        Args:
            version (str): version number
        """
        self.version = version

    @classmethod
    def from_file(cls, path):
        """
        Creates a Version from a Skopeo version file.

        Args:
            path (str): path to the version file

        Return:
            (Version): instance

        Raises:
            (IOError): when path does not exist
        """
        with open(path) as version_file:
            version = version_file.readline().split(':')[1].strip()
            return cls(version)

    @property
    def components(self):
        """
        Return:
            (tuple) of 2 integer components of the release, (X, Y)
        """
        components = [int(comp) for comp in self.version.split(".")]
        assert len(components) == 2, "Directory Transport Versions must be in the form X.Y"
        return tuple(components)

    def __eq__(self, other):
        """
        Args:
            other (Version): version to compare with

        Return:
            (bool) True if self == other
        """
        return self.version == other.version

    def __ne__(self, other):
        """
        Args:
            other (Version): version to compare with

        Return:
            (bool) True if self != other
        """
        return not self.version == other.version

    def __gt__(self, other):
        """
        Args:
            other (Version): version to compare with

        Return:
            (bool) True if self > other
        """
        comparisons = zip(self.components, other.components)
        for s, o in comparisons:
            if s != o:
                return s > o
        return False

    def __ge__(self, other):
        """
        Args:
            other (Version): version to compare with

        Return:
            (bool) True if self >= other
        """
        op_result = self.__gt__(other)
        return op_result or self == other

    def __lt__(self, other):
        """
        Args:
            other (Version): version to compare with

        Return:
            (bool) True if self < other
        """
        comparisons = zip(self.components, other.components)
        for s, o in comparisons:
            if s != o:
                return not s > o

    def __le__(self, other):
        """
        Args:
            other (Version): version to compare with

        Return:
            (bool) True if self <= other
        """
        op_result = self.__lt__(other)
        return op_result or self == other

    def __repr__(self):
        """
        Return:
            (string) in the format that skopeo uses.
        """
        return "Directory Transport Version: {v}\n".format(v=self.version)
