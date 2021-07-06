from distutils.core import setup
from setuptools import find_packages

setup(
    name='kathara',  # How you named your package folder (MyLib)
    package_dir={'': 'src'},
    packages=find_packages(where='src'),  # Chose the same as "name"

    version='0.1',  # Start with a small number and increase it with every change you make
    license='gpl-3.0',  # Chose a license from here: https://help.github.com/articles/licensing-a-repository
    description='A lightweight container based emulation system.',  # Give a short description about your library
    author='Tommaso Caiazzi',  # Type in your name
    author_email='contact@kathara.org',  # Type in your E-Mail
    url='https://www.kathara.org',  # Provide either the link to your github or to your website
    download_url='https://github.com/KatharaFramework/Kathara/archive/refs/tags/3.1.0.tar.gz',
    # I explain this later on
    keywords=['NETWORK-EMULATION', 'CONTAINERS', 'NFV'],  # Keywords that define your package best
    install_requires=[  # I get to this in a second
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
        # Chose either "3 - Alpha", "4 - Beta" or "5 - Production/Stable" as the current state of your package
        'Intended Audience :: Developers',  # Define that your audience are developers
        'Topic :: Software Development :: Build Tools',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Programming Language :: Python :: 3',  # Specify which pyhton versions that you want to support
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ],
)
