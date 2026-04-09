{
  # Flake metadata shown by `nix flake metadata` and similar commands.
  description = "Kathara Nix flake";

  # Pin nixpkgs so package/module behavior is reproducible.
  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-23.05";

  outputs =
    { self, nixpkgs }:
    let
      # Supported target systems for exported packages/apps.
      systems = [
        "x86_64-linux"
        "aarch64-linux"
      ];
      # Helper: build an attribute set for every supported system.
      forAllSystems = nixpkgs.lib.genAttrs systems;
    in
    {
      # Overlay exposing `pkgs.kathara` when this flake is imported elsewhere.
      overlays.default = final: prev: {
        kathara = final.callPackage ./nix { };
      };

      # Build package outputs for each supported system.
      packages = forAllSystems (
        system:
        let
          # Import nixpkgs for the current system.
          pkgs = import nixpkgs { inherit system; };
        in
        rec {
          # Package expression lives in `./nix/default.nix`.
          kathara = pkgs.callPackage ./nix { };
          # `nix build` defaults to this package.
          default = kathara;
        }
      );

      # NixOS module: install Kathara system-wide and register the overlay.
      nixosModules.default =
        { pkgs, ... }:
        {
          nixpkgs.overlays = [ self.overlays.default ];
          environment.systemPackages = [ pkgs.kathara ];
        };

      # Home Manager module exported by this flake.
      homeManagerModules.default = import ./nix/home-manager.nix;

      # `nix run` entrypoint -> `kathara` executable from the default package.
      apps = forAllSystems (system: {
        default = {
          type = "app";
          program = "${self.packages.${system}.default}/bin/kathara";
        };
      });
    };
}
