{
  lib,
  stdenv,
  python3Packages,
  fetchFromGitHub,
  fetchPypi,
  ronn,
  makeWrapper,
  m4,
  chrpath,
  xterm,
  docker,
  tmux,
}:

python3Packages.buildPythonApplication rec {
  pname = "kathara";
  version = "3.8.0";
  # Upstream project uses its own Makefiles/build scripts, so keep custom phases.
  format = "other";

  # Build from an exact upstream tag/revision for reproducibility.
  src = fetchFromGitHub {
    owner = "KatharaFramework";
    repo = "Kathara";
    rev = version;
    hash = "sha256-771BJANCgYuV5ebdqPWIbykcanEZP+duTkbYQdwL8cU=";
  };

  nativeBuildInputs = [
    # Used to create wrapper scripts and generate manpages/completions at build time.
    makeWrapper
    ronn
    chrpath
    m4
    python3Packages.setuptools
    python3Packages.pytest
  ];

  propagatedBuildInputs =
    with python3Packages;
    let
      # `slug` is not provided by nixpkgs under the expected import name.
      slug = buildPythonPackage rec {
        pname = "slug";
        version = "2.0";
        format = "wheel";
        src = fetchPypi {
          inherit pname version format;
          hash = "sha256-9VskoFY0KM5WJDB59q63nA3RzFu/izmxC9blJjuovl8=";
          dist = "py3";
          python = "py3";
        };
      };

      # Keep explicit aliasing for readability where package name conflicts are possible.
      dockerPython = python3Packages.docker;
    in
    [
      dockerPython
      binaryornot
      networkx
      pyroute2
      tabulate
      rich
      fs
      pyuv
      requests
      chardet
      libtmux
      slug
      kubernetes
    ];

  buildPhase = ''
    runHook preBuild

    # Convert docs/*.ronn into manpage roff files.
    pushd docs
    make roff-build
    popd

    # Generate Bash completion script consumed during install phase.
    pushd scripts/autocompletion
    python generate_autocompletion.py kathara.bash-completion
    popd

    runHook postBuild
  '';

  checkPhase = ''
    runHook preCheck
    pytest tests
    runHook postCheck
  '';

  installPhase = ''
    runHook preInstall

    # Move generated man pages under section-specific directories (man1, man5, ...).
    for man_file in docs/Roff/*; do
      section="''${man_file##*.}"
      man_file_dir="man$section"
      mkdir -p "docs/Roff/$man_file_dir"
      mv -f "$man_file" "docs/Roff/$man_file_dir/"
    done

    install -d -m 755 "$out/share/man"
    cp -r docs/Roff/* "$out/share/man/"

    install -d -m 755 "$out/share/bash-completion/completions"
    install -p -m 644 scripts/autocompletion/kathara.bash-completion "$out/share/bash-completion/completions/kathara"

    install -d -m 755 "$out/share/$pname/src"
    cp -r src/Kathara "$out/share/$pname/src/"
    install -p -m 755 src/kathara.py "$out/share/$pname/src/"

    install -d -m 755 "$out/libexec"
    # Stable xterm wrapper so Kathara doesn't depend on /usr/bin paths.
    cat > "$out/libexec/kathara-xterm" <<'EOF'
    #!${stdenv.shell}
    exec ${xterm}/bin/xterm -fa Monospace "$@"
    EOF
    chmod 755 "$out/libexec/kathara-xterm"

    substituteInPlace "$out/share/$pname/src/Kathara/setting/Setting.py" \
      --replace "'/usr/bin/xterm'" "'$out/libexec/kathara-xterm'"

    # Add retry loop to `connect` UI command to avoid race on just-started devices.
    substituteInPlace "$out/share/$pname/src/Kathara/cli/ui/utils.py" \
      --replace "command.append(connect_command)" "command.extend([\"sh\", \"-lc\", \"for i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20; do %s && break; sleep 0.2; done\" % connect_command])"

    # Pass lab directory explicitly to `kathara connect` from the UI helper.
    substituteInPlace "$out/share/$pname/src/Kathara/cli/ui/utils.py" \
      --replace "connect_command = \"%s connect %s -l %s\" % (executable_path, is_vmachine, machine.name)" "connect_command = \"%s connect %s -d \\\"%s\\\" -l %s\" % (executable_path, is_vmachine, machine.lab.fs_path(), machine.name)"

    install -d -m 755 "$out/bin"
    # Wrap launcher with runtime PATH/PYTHONPATH and warning filter.
    makeWrapper ${python3Packages.python}/bin/python "$out/bin/$pname" \
      --add-flags "$out/share/$pname/src/kathara.py" \
      --set PYTHONWARNINGS "ignore:pkg_resources is deprecated as an API:UserWarning:fs" \
      --prefix PATH : "${
        lib.makeBinPath [
          docker
          tmux
          xterm
        ]
      }" \
      --prefix PYTHONPATH : "${python3Packages.makePythonPath propagatedBuildInputs}:$out/share/$pname/src"

    runHook postInstall
  '';

  doCheck = false;

  meta = with lib; {
    description = "A lightweight container-based network emulation tool";
    homepage = "https://www.kathara.org/";
    license = licenses.gpl3Only;
    mainProgram = "kathara";
    platforms = platforms.linux;
  };
}
