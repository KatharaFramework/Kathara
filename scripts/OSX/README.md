# Compiling Kathara for Mac OSX (Unsigned)

1. Install [Tart](https://github.com/openai/tart) from Homebrew.
2. Change the Kathara version number in both `src/Kathara/version.py` and `Makefile` files.
3. Run `make tart-build_x86_64` or `make tart-build_arm64` to automatically compile and create the package for the desired architecture. You can also run `make tart-build_all` to build for both.
    - Run `make clean` to clean all intermediate files.
4. Share the Kathara pkg in `Output` folder :)

# Compiling Kathara for Mac OSX (Signed)

1. Change the `Makefile` and add your Apple Developer Certificate ID, the `.p12` path and the certificate password (if set).
2. Install [Tart](https://github.com/openai/tart) from Homebrew.
3. Change the Kathara version number in both `src/Kathara/version.py` and `Makefile` files.
4. Run `make tart-buildSigned_x86_64` or `make tart-buildSigned_arm64` to automatically compile and create the package for the desired architecture. You can also run `make tart-buildSigned_all` to build for both.
    - Run `make clean` to clean all intermediate files.
5. Share the Kathara pkg signed in `Output` folder :)