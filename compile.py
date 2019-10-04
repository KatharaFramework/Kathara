from distutils.core import setup
from distutils.extension import Extension
from Cython.Distutils import build_ext
from Cython.Build import cythonize

NAME = "Kathara"
VERSION = "0.47"
DESCR = "Lorem ipsum"
URL = "http://www.kathara.org/"
AUTHOR = "Kathara Team"
EMAIL = "contact@kathara.org"

ext_modules = [
    Extension("Resources.*", ["./Resources/*.py"]),
    Extension("Resources.api.*", ["./Resources/api/*.py"]),
    Extension("Resources.command.*", ["./Resources/command/*.py"]),
    Extension("Resources.foundation.command.*", ["./Resources/foundation/command/*.py"]),
    Extension("Resources.foundation.manager.*", ["./Resources/foundation/manager/*.py"]),
    Extension("Resources.manager.docker.*", ["./Resources/manager/docker/*.py"]),
    Extension("Resources.model.*", ["./Resources/model/*.py"]),
    Extension("Resources.parser.netkit.*", ["./Resources/parser/netkit/*.py"]),
    Extension("Resources.setting.*", ["./Resources/setting/*.py"]),
    Extension("Resources.trdparty.depgen.*", ["./Resources/trdparty/depgen/*.py"]),
    Extension("Resources.trdparty.dockerpty.*", ["./Resources/trdparty/dockerpty/*.py"]),
    Extension("Resources.validator.*", ["./Resources/validator/*.py"])
]
setup(
    name=NAME,
    version=VERSION,
    description=DESCR,
    author=AUTHOR,
    author_email=EMAIL,
    url=URL,
    cmdclass = {'build_ext': build_ext},
    ext_modules = cythonize(ext_modules, 
        compiler_directives={'language_level' : "3"},
        build_dir="build2")
)