{
  description = "sask — small resource server experiment";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-25.05";
  };

  outputs = { self, nixpkgs }:
    let
      system = "x86_64-linux";
      pkgs = import nixpkgs { inherit system; };
    in {
      devShells.${system}.default = pkgs.mkShell {
        packages = with pkgs; [
          python312
          poetry
          ruff
          opentofu
          ansible
          ansible-lint
          openssh
          sqlite
          jq
          curl
        ];

        shellHook = ''
          echo "sask dev shell — $(python --version), Poetry $(poetry --version | cut -d' ' -f3)"
          export PROJECT_ROOT="$PWD"
          export PS1="(sask) $PS1"

          # sask runtime defaults — override in your shell as needed.
          export SASK_HOST="127.0.0.1"
          export SASK_PORT="8080"
          export SASK_TOKENS_PATH="$HOME/.config/sask/tokens.toml"
          export SASK_MANIFEST_PATH="$PROJECT_ROOT/resources/manifest.toml"
        '';
      };
    };
}

