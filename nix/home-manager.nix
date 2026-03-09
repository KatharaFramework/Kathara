{
  config,
  lib,
  pkgs,
  ...
}:

let
  cfg = config.programs.kathara;
  jsonFormat = pkgs.formats.json { };
  typedSettings = lib.filterAttrs (_: value: value != null) {
    image = cfg.image;
    manager_type = cfg.manager;
    terminal = cfg.terminal;
    open_terminals = cfg.openTerminals;
    device_shell = cfg.deviceShell;
    net_prefix = cfg.netPrefix;
    device_prefix = cfg.devicePrefix;
    debug_level = cfg.debugLevel;
    print_startup_log = cfg.printStartupLog;
    enable_ipv6 = cfg.enableIpv6;
  };
in
{
  options.programs.kathara = {
    enable = lib.mkEnableOption "Kathara";

    package = lib.mkOption {
      type = lib.types.package;
      default = if pkgs ? kathara then pkgs.kathara else pkgs.callPackage ../nix { };
      description = "Kathara package to install.";
    };

    image = lib.mkOption {
      type = lib.types.nullOr lib.types.str;
      default = null;
      example = "kathara/base";
      description = "Default image used by Kathara devices (kathara.conf key: image).";
    };

    manager = lib.mkOption {
      type = lib.types.nullOr (
        lib.types.enum [
          "docker"
          "kubernetes"
        ]
      );
      default = null;
      example = "docker";
      description = "Manager backend (kathara.conf key: manager_type).";
    };

    terminal = lib.mkOption {
      type = lib.types.nullOr lib.types.str;
      default = null;
      example = "/usr/bin/xterm";
      description = "Terminal command used by Kathara (kathara.conf key: terminal).";
    };

    openTerminals = lib.mkOption {
      type = lib.types.nullOr lib.types.bool;
      default = null;
      description = "Automatically open terminals when starting devices (kathara.conf key: open_terminals).";
    };

    deviceShell = lib.mkOption {
      type = lib.types.nullOr lib.types.str;
      default = null;
      example = "/bin/bash";
      description = "Default shell inside devices (kathara.conf key: device_shell).";
    };

    netPrefix = lib.mkOption {
      type = lib.types.nullOr lib.types.str;
      default = null;
      example = "kathara";
      description = "Prefix for network names (kathara.conf key: net_prefix).";
    };

    devicePrefix = lib.mkOption {
      type = lib.types.nullOr lib.types.str;
      default = null;
      example = "kathara";
      description = "Prefix for device names (kathara.conf key: device_prefix).";
    };

    debugLevel = lib.mkOption {
      type = lib.types.nullOr (
        lib.types.enum [
          "CRITICAL"
          "ERROR"
          "WARNING"
          "INFO"
          "DEBUG"
          "EXCEPTION"
        ]
      );
      default = null;
      example = "INFO";
      description = "Logging level (kathara.conf key: debug_level).";
    };

    printStartupLog = lib.mkOption {
      type = lib.types.nullOr lib.types.bool;
      default = null;
      description = "Print startup logs (kathara.conf key: print_startup_log).";
    };

    enableIpv6 = lib.mkOption {
      type = lib.types.nullOr lib.types.bool;
      default = null;
      description = "Enable IPv6 features (kathara.conf key: enable_ipv6).";
    };

    settings = lib.mkOption {
      type = jsonFormat.type;
      default = { };
      example = {
        manager_type = "docker";
        open_terminals = false;
      };
      description = ''
        Additional raw settings written to ~/.config/kathara.conf.
        Values defined by typed options (such as manager, image, terminal) take precedence.
      '';
    };
  };

  config = lib.mkIf cfg.enable {
    home.packages = [ cfg.package ];

    xdg.configFile."kathara.conf".source = jsonFormat.generate "kathara.conf" (
      cfg.settings // typedSettings
    );
  };
}
