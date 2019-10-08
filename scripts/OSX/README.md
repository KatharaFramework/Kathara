# Compiling Kathara for Mac OSX

1. Install `pkgbuild`, `productbuild` and `make` from Apple developer repository
	- If you have `XCode` installed you probably already have them installed
	- Otherwise, download them from [here](https://developer.apple.com/devcenter/mac/index.action)
2. Run `make all` to automatically do the following steps
	- Run `make deps` to automatically download and install dependencies
	- Run `make binary` to automatically compile the package
	- Run `make pkg` to create package
	- Run `make dmg` to create dmg (Disk Image) file
	- Run `make clean` to clean all intermediate files
6. Share the `Kathara-setup.dmg` in output folder :)