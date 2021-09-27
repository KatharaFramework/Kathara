from distutils.core import setup

from setuptools import find_packages

setup(
    name='kathara',
    package_dir={'': 'src'},
    packages=find_packages('src', exclude=["Kathara.cli", "Kathara.cli.*"]),
    version='0.8.0',
    license='gpl-3.0',
    description='A lightweight container based emulation system.',
    author='Tommaso Caiazzi',
    author_email='contact@kathara.org',
    url='https://www.kathara.org',
    download_url='https://github.com/KatharaFramework/Kathara/archive/refs/tags/3.1.0.tar.gz',
    keywords=['NETWORK-EMULATION', 'CONTAINERS', 'NFV'],
    install_requires=[
        "binaryornot>=0.4.4",
        "urllib3<1.26,>=1.24.1",
        "docker>=4.4.0",
        "pyyaml<5.4,>=5",
        "kubernetes>=11.0.0",
        "requests>=2.22.0",
        "coloredlogs>=10.0",
        "terminaltables>=3.1.0",
        "slug>=2.0",
        "deepdiff>=4.0.9",
        "pyroute2>=0.5.7",
        "progressbar2>=1.14.0",
        "libtmux>=0.8.2; platform_system == 'darwin' or platform_system == 'linux'",
        "pyuv>=1.4.0",
        "appscript>=1.1.0; platform_system == 'darwin'",
        "pypiwin32>=223; platform_system == 'win32'",
        "windows-curses>=2.1.0; platform_system == 'win32'"
    ],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ],
)
