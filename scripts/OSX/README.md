# Compiling Kathara for Mac OSX (Unsigned)

1. Install `pkgbuild`, `productbuild` and `make` from Apple developer repository
	- If you have `XCode` installed you probably already have them installed
	- Otherwise, download them from [here](https://developer.apple.com/devcenter/mac/index.action)
2. Change the Kathara version number in both `src/Kathara/version.py` and `Makefile` files.
3. Run `make all` to automatically compile and create the package
	- Run `make deps` to automatically download and install dependencies
	- Run `make binary` to automatically compile the package
	- Run `make createInstaller` to create package
	- Run `make clean` to clean all intermediate files
4. Share the Kathara pkg in `Output` folder :)

# Compiling Kathara for Mac OSX (Signed)

1. Change the `Makefile` and add your Apple Developer Certificate ID
2. Install `pkgbuild`, `productbuild` and `make` from Apple developer repository
	- If you have `XCode` installed you probably already have them installed
	- Otherwise, download them from [here](https://developer.apple.com/devcenter/mac/index.action)
3. Change the Kathara version number in both `src/Kathara/version.py` and `Makefile` files.
4. Run `make allSigned` to automatically compile and create the package
	- Run `make deps` to automatically download and install dependencies
	- Run `make binary` to automatically compile the package
	- Run `make createInstaller` to create package
	- Run `make signProduct` to sign the package
	- Run `make clean` to clean all intermediate files
5. Share the Kathara pkg signed in `Output` folder :)