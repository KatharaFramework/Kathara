# Compiling Kathara for Mac OSX (Unsigned)

1. Install `pkgbuild`, `productbuild` and `make` from Apple developer repository
    - If you have `XCode` installed you probably already have them installed
    - Otherwise, download them from [here](https://developer.apple.com/devcenter/mac/index.action)
    - **NOTE:** You need Python 3.13 in order to compile the binary ([Quick link](https://www.python.org/downloads/release/python-31312/))
2. Install Ruby from Homebrew: `brew install ruby` 
3. Check the Kathara version number in `src/Kathara/version.py`. The `Makefile` does not hold the version: pass the same one to `make` as `VERSION=x.y.z`.
4. Run `make all_x86 VERSION=x.y.z` or `make all_arm64 VERSION=x.y.z` to automatically compile and create the package for the desired architecture.
You can compile the `x86` package on a Mac with Intel CPU, and the `arm64` on a Mac with Apple CPU.
On Rosetta enabled Mac with Apple CPU you can compile the `x86` package passing the `SET_ARCH='arch -x86_64'` variable to the make command. This will:
    1. Automatically download and install dependencies for your architecture
    2. Automatically compile the package
    3. Create package
    4. Clean all intermediate files
5. Share the Kathara pkg in `Output` folder :)

# Compiling Kathara for Mac OSX (Signed)

1. Check the `Makefile` and add your Apple Developer Certificate ID
2. Install `pkgbuild`, `productbuild` and `make` from Apple developer repository
    - If you have `XCode` installed you probably already have them installed
    - Otherwise, download them from [here](https://developer.apple.com/devcenter/mac/index.action)
    - **NOTE:** You need Python 3.13 in order to compile the binary ([Quick link](https://www.python.org/downloads/release/python-31312/))
3. Install Ruby from Homebrew: `brew install ruby` 
4. Check the Kathara version number in `src/Kathara/version.py`. The `Makefile` does not hold the version: pass the same one to `make` as `VERSION=x.y.z`.
5. Run `make allSigned_x86 VERSION=x.y.z` or `make allSigned_arm64 VERSION=x.y.z` to automatically compile and create the package for the desired architecture. 
You can compile the `x86` package on a Mac with Intel CPU, and the `arm64` on a Mac with Apple CPU.
On Rosetta enabled Mac with Apple CPU you can compile the `x86` package passing the `SET_ARCH='arch -x86_64'` variable to the make command. This will:
    1. Automatically download and install dependencies for your architecture
    2. Automatically compile the package
    3. Sign executables and shared objects
    4. Create package
    5. Sign the package
    6. Notarize package
    7. Clean all intermediate files
6. Share the Kathara pkg signed in `Output` folder :)