# Compiling Kathara for Mac OSX (Unsigned)

1. Install `pkgbuild`, `productbuild` and `make` from Apple developer repository
    - If you have `XCode` installed you probably already have them installed
    - Otherwise, download them from [here](https://developer.apple.com/devcenter/mac/index.action)
    - **NOTE:** You need Python 3.11 in order to compile the binary ([Quick link](https://www.python.org/downloads/release/python-3117/))
2. Install Ruby from Homebrew: `brew install ruby` 
3. Change the Kathara version number in both `src/Kathara/version.py` and `Makefile` files.
4. Run `make all_x86` or `make all_arm64` to automatically compile and create the package for the desired architecture.
You can compile the `x86` package on a Mac with Intel CPU, and the `arm64` on a Mac with Apple CPU.
    - Run `make deps` to automatically download and install dependencies for your architecture
    - Run `make binary_x86_64` or `make binary_arm64` to automatically compile the package
    - Run `make createInstaller_x86_64` or `make createInstaller_arm64` to create package
    - Run `make clean` to clean all intermediate files
5. Share the Kathara pkg in `Output` folder :)

# Compiling Kathara for Mac OSX (Signed)

1. Change the `Makefile` and add your Apple Developer Certificate ID
2. Install `pkgbuild`, `productbuild` and `make` from Apple developer repository
    - If you have `XCode` installed you probably already have them installed
    - Otherwise, download them from [here](https://developer.apple.com/devcenter/mac/index.action)
    - **NOTE:** You need Python 3.11 in order to compile the binary ([Quick link](https://www.python.org/downloads/release/python-3117/))
3. Install Ruby from Homebrew: `brew install ruby` 
4. Change the Kathara version number in both `src/Kathara/version.py` and `Makefile` files.
5. Run `make allSigned_x86` or `make allSigned_arm64` to automatically compile and create the package for the desired architecture. 
You can compile the `x86` package on a Mac with Intel CPU, and the `arm64` on a Mac with Apple CPU.
    - Run `make deps` to automatically download and install dependencies for your architecture
    - Run `make binary_x86_64` or `make binary_arm64` to automatically compile the package
    - Run `make createInstaller_x86_64` or `make createInstaller_arm64` to create package
    - Run `make signProduct_x86_64` or `make signProduct_arm64` to sign the package
    - Run `make clean` to clean all intermediate files
6. Share the Kathara pkg signed in `Output` folder :)