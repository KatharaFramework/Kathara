from distutils.core import setup

from setuptools import find_packages

setup(
    name='kathara',
    package_dir={'': 'src'},
    packages=find_packages('src'),
    py_modules=['kathara'],
    version='3.6.0',
    license='gpl-3.0',
    description='A lightweight container based emulation system.',
    author='Kathara Framework',
    author_email='contact@kathara.org',
    url='https://www.kathara.org',
    download_url='https://github.com/KatharaFramework/Kathara/archive/refs/tags/3.6.0.tar.gz',
    keywords=['NETWORK-EMULATION', 'CONTAINERS', 'NFV'],
    install_requires=[
        "binaryornot>=0.4.4",
        "docker>=6.0.1",
        "kubernetes>=23.3.0",
        "requests>=2.22.0",
        "coloredlogs>=10.0",
        "terminaltables>=3.1.0",
        "slug>=2.0",
        "deepdiff==6.2.2",
        "pyroute2>=0.5.19",
        "progressbar2>=1.14.0",
        "fs>=2.4.16",
        "libtmux>=0.8.2; platform_system == 'darwin' or platform_system == 'linux'",
        "appscript>=1.1.0; platform_system == 'darwin'",
        "pypiwin32>=223; platform_system == 'win32'",
        "windows-curses>=2.1.0; platform_system == 'win32'"
    ],
    extras_require={
        'pyuv': ["pyuv @ https://api.github.com/repos/saghul/pyuv/tarball/master"],
    },
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11'
    ],
)
