{
  description = "DNS blocker utilizing unbound(8)";
  nixConfig.bash-prompt = "[nix-develop]$ ";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs = { self, nixpkgs }:
    let
      systems = [ "x86_64-linux" "aarch64-linux" ];

      forAllSystems = f:
        nixpkgs.lib.genAttrs systems
        (system: f system nixpkgs.legacyPackages.${system});
    in {
      packages = forAllSystems (_: pkgs: {
        default = pkgs.python3Packages.buildPythonApplication {
          pname = "unbound-blocker";
          version = "0.1.0";
          src = ./.;
          format = "pyproject";

          nativeBuildInputs = with pkgs.python3Packages; [ setuptools-scm ];
          propagatedBuildInputs = with pkgs.python3Packages; [ click requests ];
          passthru.optional-dependencies = {
            lint = with pkgs.python3Packages; [
              black
              mypy
              pkgs.ruff
              types-requests
            ];
          };
        };
      });

      devShells = forAllSystems (system: pkgs: {
        default = pkgs.mkShell {
          packages = with pkgs; [ deadnix nixfmt statix ];

          inputsFrom = [ self.packages."${system}".default ];
        };
      });

      formatter = forAllSystems (_: pkgs:
        pkgs.writeShellApplication {
          name = "nixfmt";
          runtimeInputs = with pkgs; [ findutils nixfmt ];
          text = ''
            find . -type f -name '*.nix' -exec nixfmt {} \+
          '';
        });

      checks = forAllSystems (system: pkgs: {
        black = pkgs.callPackage ./checks/black.nix { };
        mypy = pkgs.callPackage ./checks/mypy.nix {
          pythonEnv = pkgs.python3.withPackages
            (_: self.packages."${system}".default.optional-dependencies.lint);
        };
        ruff = pkgs.callPackage ./checks/ruff.nix { };
      });
    };
}
