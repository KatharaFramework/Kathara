

### NixOS (flake)

If you use this repository as a flake input, add the package (or module) to your NixOS configuration so `kathara` is installed in your system profile and available in `PATH`.

```nix
# flake.nix
inputs.kathara.url = "github:KatharaFramework/Kathara";

# configuration.nix
environment.systemPackages = [
  inputs.kathara.packages.${pkgs.system}.default
];
```

Alternatively, import the module exposed by the flake:

```nix
# flake.nix
inputs.kathara.url = "github:KatharaFramework/Kathara";

# configuration.nix
imports = [ inputs.kathara.nixosModules.default ];
```

### Home Manager (flake)

The flake also exposes a Home Manager module to install Kathará and manage `~/.config/kathara.conf` declaratively:

```nix
# flake.nix
inputs.kathara.url = "github:KatharaFramework/Kathara";

# home.nix
imports = [ inputs.kathara.homeManagerModules.default ];

programs.kathara = {
  enable = true;
  manager = "docker";
  image = "kathara/base";
  terminal = "/usr/bin/xterm";
  openTerminals = true;
  deviceShell = "/bin/bash";
  netPrefix = "kathara";
  devicePrefix = "kathara";
  debugLevel = "INFO";
  printStartupLog = true;
  enableIpv6 = false;

  # Optional: additional raw keys written to kathara.conf
  settings = { };
};
```

Available typed options under `programs.kathara`:

- `enable`
- `package`
- `image` (`kathara.conf`: `image`)
- `manager` (`kathara.conf`: `manager_type`; values: `docker`, `kubernetes`)
- `terminal` (`kathara.conf`: `terminal`)
- `openTerminals` (`kathara.conf`: `open_terminals`)
- `deviceShell` (`kathara.conf`: `device_shell`)
- `netPrefix` (`kathara.conf`: `net_prefix`)
- `devicePrefix` (`kathara.conf`: `device_prefix`)
- `debugLevel` (`kathara.conf`: `debug_level`; values: `CRITICAL`, `ERROR`, `WARNING`, `INFO`, `DEBUG`, `EXCEPTION`)
- `printStartupLog` (`kathara.conf`: `print_startup_log`)
- `enableIpv6` (`kathara.conf`: `enable_ipv6`)
- `settings` (extra raw JSON keys)

If you are not using flakes, you can still install Kathará from `configuration.nix` using `fetchTarball` and `callPackage`:

```nix
{ config, pkgs, ... }:

let
  katharaSrc = builtins.fetchTarball {
    url = "https://github.com/KatharaFramework/Kathara/archive/refs/tags/3.8.0.tar.gz";
    # sha256 = "sha256-...";
  };

  katharaPkg = pkgs.callPackage "${katharaSrc}/nix" { };
in
{
  environment.systemPackages = [
    katharaPkg
  ];
}
```
