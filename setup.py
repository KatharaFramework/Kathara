from setuptools import find_packages, setup

setup(
    name='kathara',
    package_dir={'': 'src'},
    packages=find_packages('src'),
    py_modules=['kathara'],
    version='3.8.1',
    license='gpl-3.0',
    description='A lightweight container-based network emulation tool.',
    author='Kathara Framework',
    author_email='contact@kathara.org',
    url='https://www.kathara.org',
    download_url='https://github.com/KatharaFramework/Kathara/archive/refs/tags/3.8.1.tar.gz',
    keywords=['NETWORK-EMULATION', 'CONTAINERS', 'NFV'],
    install_requires=[
        "binaryornot>=0.4.4",
        "docker>=7.0.0",
        "kubernetes>=23.3.0",
        "requests>=2.22.0",
        "pyroute2",
        "rich",
        "fs>=2.4.16",
        "chardet",
        "libtmux>=0.8.2; platform_system == 'darwin' or platform_system == 'linux'",
        "appscript>=1.1.0; platform_system == 'darwin'",
        "pypiwin32>=223; platform_system == 'win32'",
        "windows-curses>=2.1.0; platform_system == 'win32'"
    ],
    extras_require={
        'test': ["pytest"],
    },
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.13',
    ],
)
