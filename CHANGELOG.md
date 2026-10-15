# Changelog

All notable changes to Kathará are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Every release PR (`develop` -> `main`) must add a `## [X.Y.Z] - YYYY-MM-DD` section
for the version in `src/Kathara/version.py`. Use these headings, in this order, and
skip the ones you don't need: Added, Changed, Deprecated, Removed, Fixed.

## [3.8.4] - 2026-10-15

### Added
- Build and package Kathará (Linux, macOS, Windows, PyPI) from the CI/CD pipeline

### Fixed
- Fix the permission problem with PyInstaller

## [3.8.3] - 2026-04-09

### Added
- Add possibility to keep collision domains when undeploying a network scenario (#382)

### Fixed
- Fix TMUX `DeprecatedError` (#384)
- Minor Fix (#383)

## [3.8.1] - 2026-03-19

### Added
- Add a configurable setting to manage volume mounting behavior (#374)
- Add a timeout while checking for new releases on GitHub (#366)
- Add a timeout while checking for new versions of Docker images (#366)

### Removed
- Remove `--xterm` parameter from `vstart`/`lstart` commands (#373)
- Remove the `pyuv` dependency (#367)

### Fixed
- Minor fixes

## [3.8.0] - 2025-07-29

### Added
- Add the possibility to mount additional volumes on devices using the `volume` metadata (#332)
- Add the possibility to specify custom entrypoint and arguments for a device using the `entrypoint` and `args` metadata (#355)

### Changed
- **⚠️ BREAKING**: The `ltest` command has been removed (#358). Please use the `kathara-lab-checker` tool as its replacement with enhanced functionalities. For further information, visit: https://github.com/KatharaFramework/kathara-lab-checker
- Allow to run a single device in privileged mode using the `privileged` metadata (#354)
- Allow specifying per-network-scenario `kathara.conf` configuration file (#340)
- (Python API) Add `retrieve_files` method to copy files from devices to the host (#357)

### Fixed
- Minor fixes (#352 #353 #356 #360 #361)

## [3.7.9] - 2025-03-26

### Changed
- Open device terminals when `--privileged` flag is set (#349 #329)
- Assign device FQDN in `/etc/hosts` (if no `/etc/hosts` is passed by the user)  (#341)

### Fixed
- (Docker) Fix user-defined interface-specific sysctls on Docker Engine >= v27.0.0 (#348)
- Fix TMUX issues (#333)

## [3.7.8] - 2025-01-08

### Added
- Add `--topology` argument to `kathara linfo` that displays a list of collision domains and the devices connected to each of them (#323)
- (Docker) Add the possibility to specify `ulimits` in network scenario metadata (thanks to @g4br-i) (#302)
- (Kubernetes) Add the support to private image registries through the `docker.json` file (thanks to @GioBar00) (#282)

### Changed
- `kathara linfo` now displays a column with the connected interfaces of each device (#321)
- `kathara exec` now returns the exact exit code of the command (#292)
- API Improvements in the `Lab` object (#325 #326)

### Fixed
- (Docker) Fix compatibility with docker-io version numbers (#309)
- (Docker) Fix `rp_filter` sysctl assigment on Docker Engine >= v27.0.0 (#320)
- Minor bug fixes (#322 #324)

## [3.7.7] - 2024-09-06

### Fixed
- Properly set driver options to disable/enable IPV6 (#306)
- Minor adjustments and optimizations

## [3.7.6] - 2024-06-17

### Added
- Add the possibility to exclude machines while deploying a network scenario, both from CLI and Python APIs (#294)

### Fixed
- Fix IPv6 disabling issue (#293)
- Minor

## [3.7.5] - 2024-05-01

### Fixed
- (Docker) Fix `rp_filter` issue on all platforms and Docker versions (#278)
- (Docker) Fix Docker API objects reloading (#285)
- Minor fixes (#284)

## [3.7.4] - 2024-03-27

### Fixed
- (Docker) Fix `rp_filter` on `eth0` that was causing startup errors on some distributions (#278) (thanks to @whatever4711)
- (Megalos) Fix watch methods while starting/stopping devices that were causing `lstart`/`lclean` to hang indefinitely (#277)
- Minor fixes

## [3.7.3] - 2024-03-18

### Added
- New CLI UI using [`rich`](https://github.com/Textualize/rich) library! (#269)
- Add `gnome-terminal` as official supported terminal emulator (#264)

### Changed
- (Docker) Show progress during Docker image pull (#267)
- Similarly to the official `docker pull` command
- (Docker) It is now correctly possible to specify a `linux/amd64` image on Apple Silicon (#268)
- They can be run using Rosetta
- Several API improvements and bug fixes (#271)

## [3.7.1] - 2024-01-09

### Added
- Add `lab` object parameter to all `Manager` methods (#254)

### Changed
- It is now possible to specify a MAC Address for a network interface (#137)
- The MAC Address can be specified in the `lab.conf` and using the `vstart`/`lstart`/`vconfig`/`lconfig` commands when declaring an interface. The syntax is `<COLLISION_DOMAIN>/<MAC_ADDRESS>`.
- For example, in a `lab.conf` file: `machine[0]="A/00:00:00:00:00:01"`.
- (Docker) Collision domains are now created per-network-scenario by default (#256)
- Previously, they were shared between different scenarios. It is possible to change the default behaviour from `kathara settings`.
- (Docker) If a `.shutdown` file is present in the network scenario, Kathará now correctly waits for the script termination before removing the container (#255)
- Several fixes of `lconfig` and `vconfig` commands (#252)
- Methods now correctly check if only one of the parameters between `lab_hash`, `lab_name`, and `lab` is passed.

### Fixed
- Minor fixes and improvements (#257 #258 #259 #261)

## [3.7.0] - 2023-10-02

### Added
- Add support for the new Kathará Network Plugin based on VDE software switches. It is possible to select the legacy Network Plugin (based on Linux Bridges) from `kathara settings` (#241)

### Changed
- For further information on the new Network Plugin, please visit the [corresponding repository](https://github.com/KatharaFramework/NetworkPlugin).
- Switch the default image to `kathara/base` for new installations (#243)

### Fixed
- Fix Docker images fetching in `kathara settings` with new Docker Hub API format (#244)

## [3.6.3] - 2023-07-21

### Added
- Add new helper methods to `model.Lab` (#229)
- Add [Homebrew tap](https://github.com/KatharaFramework/homebrew-kathara) for installing Kathará on macOS

### Changed
- Use `chardet` to parse all byte strings in order to correctly encode non-UTF8 characters (#208)
- Wait for startup commands execution while opening a connection to a device (the wait can be overridden by pressing `[ENTER]`) (#209)
- Keep correct folders/files permissions when copying files inside the device
- Rename `startup_commands` meta to `exec_commands` to avoid ambiguity with `.startup` files (#228)

### Fixed
- Fix `sysctl` metadata parsing for negative values (#226)
- Fix `machine.is_ipv6_enabled()` method to correctly follow priority of `ipv6` meta (#227)
- Minor fixes

## [3.6.2] - 2023-06-25

### Added
- Add a warning message if a meta is assigned more than once on the same device (#219)
- Add support for Docker images tags in `kathara settings` (#218)

### Deprecated
- **⚠️ DEPRECATION WARNING**: End of support for Ubuntu Bionic (18.04 LTS). Starting from this Release, the package will not be updated anymore.
- **⚠️ DEPRECATION WARNING**: End of support for Ubuntu Kinetic (22.04). Starting from next Release, the package will not be updated anymore.

### Fixed
- Fix Python `FilesystemMixin` APIs for file modifications (#220)
- Fix error message in `Lab.new_machine()` (#221)
- Fix Docker `api_object` reload in `Machine` when disconnecting an existing link at runtime (#224)

## [3.6.0] - 2023-05-24

### Added
- Add filesystem abstraction that allows Python users to manage network scenarios' files and configurations in memory, without requiring any underlying host filesystem (#205)
- Add `.toml` setup file as requested by Python 3.11 specifications (#214)
- Add unit tests for CLI commands (#204)
- Add support to Ubuntu 23.04 (Lunar Lobster)

### Fixed
- Fix Quagga permissions that prevent from writing configurations inside `vtysh` (#212)
- Fix deprecation Warnings of `libtmux` (#207, thanks to @whatever4711)
- Minor fixes (#203 and #206)

## [3.5.5] - 2023-01-17

### Added
- Add support for Ubuntu 22.10 (Kinetic Kudu)
- Add `--shared` option to start commands that allows to mount shared folder, overriding the value defined in `kathara.conf`(#200)
- Add `--hosthome` option to start commands that allows to mount home folder, overriding the value defined in `kathara.conf` (#200)

### Changed
- Bump `dockerpy` version to >= 6.0.1 and remove Windows patches for `The pipe has been ended` errors (#199)
- (Docker) Raise a custom exception when a binary is not found in the container image (fix #190)
- (Kubernetes) Return the control to the user only when all devices are started up or cleaned up (#195 #196 #197)

### Fixed
- (Kubernetes) Fix possible VNI collisions by loading already deployed networks before creating new ones (fix #198)

## [3.5.1] - 2022-09-30

### Added
- Add possibility to disconnect a device from a collision domain using `vconfig` and `lconfig` commands (see man for further information) (#173)
- Add check to ensure that required Docker images are compatible with the host architecture (fix #178)
- Add several utility methods to the `Kathara` facade and model classes (#181)

### Changed
- It is now possible to restart only specific devices using `lrestart` (fix #177)
- More generic regular expression for device `env` meta (fix #168)
- Network scenario hash is now computed from `LAB_NAME` meta, if present (fix #163)
- Improve exceptions handling and better error descriptions (#179 #183)
- Change `pyuv` dependency with the Python 3.10 compatible version (fix #182)
- Commands inside a device are run with the shell specified in the `shell` meta, if defined (fix #186)
- [Windows] Add workaround to fix the problem introduced in Docker Desktop 4.12.0 that prevents PowerShell to correctly open (fix #191)

## [3.5.0] - 2022-05-11

### Added
- Add support to Ubuntu 22.04 LTS (Jammy Jellyfish) (#164)
- Add Settings option to select the Docker Image Update Policy (#156)
- Add possibility to declare container environment variables from `vstart` and `lab.conf` (#158)

### Changed
- Refactor of Managers and add more expressive Python APIs (#154)
- Decouple UI Logic from Business Logic (#155)

### Fixed
- Fix `lab.dep` parser (#146)

## [3.3.0] - 2021-12-20

### Added
- Add multi-arch support (thanks to Nicolas Ollinger and Marcel Großmann) (fix #140 #128)
- Add Apple Silicon build scripts and binary (thanks to Nicolas Ollinger) (fix #131)
- Add `arm64` binaries for Debian-based systems (check our [LaunchPad page](https://launchpad.net/~katharaframework/+archive/ubuntu/kathara) for more information)
- Add check that throws an exception when a device is connected multiple times on the same CD

### Changed
- Unmount `/etc/resolv.conf` and `/etc/hosts` instead of patching them with `cat` (fix #137)
- Lab object has no side-effect when it is deployed with selected devices

### Fixed
- Fix `exec` command with non-returning commands (like `ping`) (fix #143)

## [3.2.0] - 2021-10-06

### Added
- Add unit tests in `tests/` folder, using `pytest` package
- (Docker) Add possibility to share the same collision domains between different users. For more information visit the [wiki](https://github.com/KatharaFramework/Kathara/wiki/SharedCollisionDomains)
- (Docker) Add possibility to connect to a remote Docker daemon instead of local one (only between UNIX systems). For more information visit the [wiki](https://github.com/KatharaFramework/Kathara/wiki/RemoteDocker)

### Changed
- Kathará is now available as a PyPI package! For more information visit the [dedicated page](https://pypi.org/project/kathara/)
- All the Python source code is now typed!
- (Docker) Checks on external interfaces are now always executed, even if the collision domain already exists
- Hidden files in a machine folder (like `.htaccess`) are now correctly copied into the container (issue #134)
- Commands are now accepted only if they are entirely lowercase

### Fixed
- (Kubernetes) Fix `ltest`, which never terminated due to a bug in `copy_files`
- Minor fixes (better lab integrity checks, better file I/O checks)

## [3.1.0] - 2021-03-21

### Added
- Add option to specify number of terminals to open for a device
- Add option in vstart for sysctl parameters (was only available in lab.conf file)

### Changed
- Advanced port forwarding options: you can now forward multiple container ports to the host
- Bump DockerPY version to 4.4.0 and use max_pool_size = cpu_count with no limit (before the limit was 10)

### Fixed
- Fix Kubernetes timeout on huge requests
- Minor fixes (fix lstart directory parsing on MacOS and MacOS-specific terminal options)

## [3.0.6] - 2020-12-03

### Fixed
- Fix ltest exec commands
- Fix check command

## [3.0.5] - 2020-11-19

### Fixed
- Fix ConfigMap check in Kubernetes Manager

## [3.0.3] - 2020-11-12

### Added
- Add Exception log level

### Changed
- Print Operating System in `check` command

### Fixed
- Fix Settings bug
- Fix Bash Autocompletion
- Fix link deletion progress bar

## [3.0.1] - 2020-11-11

### Added
- Add Megalos (Kubernetes Manager) support
- Add TMUX Support (thanks to Marcel Großmann)
- Support for unified version of Docker Network Plugin

### Changed
- Native tty wrappers for Unix/Windows for Docker exec and Socket-based for Kubernetes exec (using pyuv)
- Introduce bash autocompletion of commands on Linux
- It is now possible to specify a tag for a Docker image (thanks to Tommaso Caiazzi and Marcel Großmann)

### Fixed
- Minor fixes

## [2.2.4] - 2020-10-05

### Fixed
- Fix issue #101

## [2.2.3] - 2020-04-15

### Fixed
- Fix no_shared and no_hosthome flags
- Fix lrestart
- Fix privileged flag in vstart

## [2.2.2] - 2020-02-18

### Added
- Add custom machine sysctls
- Add lconfig command

### Fixed
- Fix Windows Connect
- Fix machine binary files copy

## [2.2.0] - 2020-01-29

### Added
- add check update to docker images
- add check update to docker images
- add plugin selection for linux platforms
- Add setting to enable ipv6

### Changed
- Limit thread to 10 due to urllib3 limitations
- Docker max_pool_size set to cpu_count
- Moved few stuff from settings + Fix image pull
- Loading bar instead of text when starting/cleaning lab
- Manager code polishing (moved deployment methods in Link/Machine, like undeploy)

### Removed
- Removed duplicated code on list chunks
- remove check on default image on starting and add check update for docker_network_plugin

### Fixed
- Fix multithread pull
- fix quotes on mac connect command
- fix machine check update
- fix quotes on mac connect command
- fix machine check update
- Fix iptables parsing (for network plugin) + Minor fixes
- Fix to lab.ext interface names greater than 15 chars
- Fix to lclean when trying to clean an external interface without sudo

## [2.1.4] - 2019-11-28

### Added
- Add privileged mode to devices.

### Changed
- Multithreaded cleanup.

## [2.1.3] - 2019-11-27

### Changed
- Brctl patch is now done once

### Fixed
- Fix brctl patch with "bridge" flag
- fix rp_filter with AppArmor
- Minor fixes

## [2.0.9] - 2019-11-07

### Fixed
- Fix Slug dependency

## [2.0.7] - 2019-11-06

### Changed
- Current User Name (used for Docker Container name) is slugified to avoid spaces and special chars

## [2.0.6] - 2019-11-06

### Changed
- Autopull alpine image

### Fixed
- Fix network overlap
- Fix terminals on CMD on Windows
- Fix libreadline7 lib

## [2.0.3] - 2019-11-03

### Changed
- Rewritten completely to work with Docker API and classful python
- Now works with Docker API
- Packaged and ready to use for Debian based Linux (via Launchpad), Windows and Mac OS

## [0.36.1] - 2019-06-30

### Fixed
- Fixed a potential issue with the network counter

## [0.36.0] - 2019-06-11

### Added
- Add support for External Labs.
- Add support for labs split across multiple machines

### Fixed
- Fixed a bug where additional options were not applied to every machine during `lstart`.
- Fix for counter too high exception (#47).

## [0.35.3] - 2019-03-18

### Fixed
- Fixed a bug in Windows occurring when the lab was in a different drive

## [0.35.2] - 2019-03-15

### Fixed
- Fixed an installation error on Linux/Mac.

## [0.35.1] - 2019-03-15

### Changed
- The `ipaddress` library is now added by the installer if not present already.

### Fixed
- Fixed a string encoding error with some Python 2.7 environments.

## [0.35] - 2019-03-13

### Changed
- Increased the default network subnet limit from 256 to over 21k

### Fixed
- Fixed the command length issues when the paths were too long or the lab was too big

## [0.34.1] - 2018-11-15

### Added
- Added log function (at the moment used only for errors in win2unix file conversions)

### Changed
- Handled non-text files in machine folders (#30)
- Handled comments in .startup files (#32)

## [0.34] - 2018-11-13

### Added
- Added some user friendly messages

### Changed
- Moved P4-examples to Labs repo (https://github.com/KatharaFramework/Kathara-Labs/tree/master/P4)

### Fixed
- Fixed bad encoding of paths with python2 (#24)
- Fixed of install permissions (#29)
- Fixed permission error in apache labs (#28)

## [0.33.1] - 2018-10-30

### Changed
- Modified the `install` script for Unix systems so that Kathará can now work if the installation user is different from the end user (so also in multi-user systems)

### Fixed
- Fixed a bug with `lclean` under Windows
- Fixed a bug with `vclean` anc legacy cleaning commands

## [0.33.0] - 2018-10-27

### Added
- Add compatibility with both Python 2 and 3 (#22)

## [0.32.1] - 2018-10-18

### Changed
- Temporarily removed update script to avoid errors on Mac OS.

### Fixed
- Fixed an error on Mac OS during install script.

## [0.32.0] - 2018-10-18

### Added
- Added a simple update script (`$NETKIT_HOME/update`).
- Added a simple script that can print the status of the required components (`$NETKIT_HOME/check`).

### Fixed
- Fixed a permission issue with the config file during install if `$NETKIT_HOME` was outside the `$HOME` directory (as it should be).

## [0.31.0b] - 2018-10-14

### Changed
- Recompiled GUI

### Fixed
- Fixed installer error on Mac OS

## [0.31.0] - 2018-10-13

### Added
- Added option to change the shell reference of a Docker image, allowing for easier extensions (thanks to @itgenie98 )

### Fixed
- Fixed the behavior of Docker networks using brctl. Now networks correctly behave like hubs instead of switch, allowing l2 SDN networks.

## [0.30.3] - 2018-08-05

### Changed
- Wrapper stability

## [0.30.2] - 2018-08-01

### Fixed
- Bug fixes and stability

## [0.30] - 2018-05-21

### Added
- Added `ltest` command for Linux.

### Fixed
- Minor fixes to `lstart`.

## [0.29.2] - 2018-05-11

### Fixed
- Fix for issues #3

## [0.29.1] - 2018-05-03

### Fixed
- Fix for issues #2 and #3

## [0.29.0] - 2018-04-17

### Added
- Added edit option to change the container platform main command

### Changed
- Improved security of admin mode installation

### Fixed
- Fixes to Unix permissions

## [0.28.0] - 2018-02-11

### Changed
- Moved images from personal developer account to a Kathará dedicated account on Docker Hub

## [0.27.5] - 2018-01-26

### Changed
- Updated GUI.

### Fixed
- Fixed an ussue with lab paths containing spaces on Mac OS.

## [0.27.2] - 2018-01-14

### Changed
- Updated GUI

## [0.27.1] - 2018-01-14

### Added
- Added GUI to the release

## [0.27] - 2018-01-13

- No release notes.

## [0.26] - 2017-11-06

### Added
- Added a way to check the version number

### Changed
- lrestart now uses lclean instead of lcrash

### Fixed
- Fixed a minor bug with the previous version

## [0.25] - 2017-11-06

### Added
- Added notices to commands that do not delete containers, since some behavious are a little bit different from Netkit

### Fixed
- Fixed a problem occurring when using lstart after using lcrash instead of lclean.

## [0.24] - 2017-11-06

### Fixed
- Fixed --admin mode under Unix

## [0.23] - 2017-11-01

### Added
- Added options to install under Linux to bypass the wrapper (only if you're a system administrator) and to skip the P4 image installation, that is very heavy and may not be useful.
- Added the --bridged parameter to vstart and lab.conf to allow the containers to be connected to the Internet through the host machine

## [0.1] - 2017-10-31

- No release notes.

