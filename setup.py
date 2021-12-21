from distutils.core import setup

from setuptools import find_packages

setup(
    name='kathara',
    package_dir={'': 'src'},
    packages=find_packages('src'),
    py_modules=['kathara'],
    version='3.3.0',
    license='gpl-3.0',
    description='A lightweight container based emulation system.',
    author='Kathara Framework',
    author_email='contact@kathara.org',
    url='https://www.kathara.org',
    download_url='https://github.com/KatharaFramework/Kathara/archive/refs/tags/3.3.0.tar.gz',
    keywords=['NETWORK-EMULATION', 'CONTAINERS', 'NFV'],
    install_requires=[
        "binaryornot>=0.4.4",
        "docker>=4.4.4",
        "kubernetes>=20.13.0",
        "requests>=2.22.0",
        "coloredlogs>=10.0",
        "terminaltables>=3.1.0",
        "slug>=2.0",
        "deepdiff>=4.0.9",
        "pyroute2>=0.5.19",
        "progressbar2>=1.14.0",
        "libtmux>=0.8.2; platform_system == 'darwin' or platform_system == 'linux'",
        "pyuv>=1.4.0",
        "appscript>=1.1.0; platform_system == 'darwin'",
        "pypiwin32>=223; platform_system == 'win32'",
        "windows-curses>=2.1.0; platform_system == 'win32'"
    ],
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Programming Language :: Python :: 3.9',
    ],
)
