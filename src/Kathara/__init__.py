import warnings

# Suppress deprecation warning from fs library using pkg_resources
# See: https://github.com/PyFilesystem/pyfilesystem2/issues/577
warnings.filterwarnings("ignore", message="pkg_resources is deprecated as an API")