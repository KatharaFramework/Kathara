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
  format = "other";

  src = fetchFromGitHub {
    owner = "KatharaFramework";
    repo = "Kathara";
    rev = version;
    hash = "sha256-771BJANCgYuV5ebdqPWIbykcanEZP+duTkbYQdwL8cU=";
  };

  nativeBuildInputs = [
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

      dockerPython = python3Packages.docker.overridePythonAttrs (old: rec {
        version = "7.0.0";
        src = fetchPypi {
          pname = old.pname;
          inherit version;
          hash = "sha256-Mjc2+5LNlBj8XnEzvJU+EanaBPRIP4KLUn21U/Hn5aM=";
        };
        nativeBuildInputs = (old.nativeBuildInputs or [ ]) ++ [ python3Packages.setuptools-scm ];
        SETUPTOOLS_SCM_PRETEND_VERSION = version;
      });

    in
    [
      dockerPython
      binaryornot
      networkx
      pyroute2
      tabulate
      requests
      pyuv
      rich
      fs
      chardet
      libtmux
      slug
      kubernetes
    ];

  buildPhase = ''
    runHook preBuild

    pushd docs
    make roff-build
    popd

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
    cat > "$out/libexec/kathara-xterm" <<'EOF'
    #!${stdenv.shell}
    exec ${xterm}/bin/xterm -fa Monospace "$@"
    EOF
    chmod 755 "$out/libexec/kathara-xterm"

    substituteInPlace "$out/share/$pname/src/Kathara/setting/Setting.py" \
      --replace "'/usr/bin/xterm'" "'$out/libexec/kathara-xterm'"

    substituteInPlace "$out/share/$pname/src/Kathara/cli/ui/utils.py" \
      --replace "command.append(connect_command)" "command.extend([\"sh\", \"-lc\", \"for i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20; do %s && break; sleep 0.2; done\" % connect_command])"

    substituteInPlace "$out/share/$pname/src/Kathara/cli/ui/utils.py" \
      --replace "connect_command = \"%s connect %s -l %s\" % (executable_path, is_vmachine, machine.name)" "connect_command = \"%s connect %s -d \\\"%s\\\" -l %s\" % (executable_path, is_vmachine, machine.lab.fs_path(), machine.name)"

    install -d -m 755 "$out/bin"
    makeWrapper ${python3Packages.python}/bin/python "$out/bin/$pname" \
      --add-flags "$out/share/$pname/src/kathara.py" \
      --prefix PATH : "${lib.makeBinPath [ docker tmux xterm ]}" \
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
