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
          opentofu
          ansible
          openssh
          sqlite
          jq
          curl
        ];

        shellHook = ''
          echo "sask dev shell — $(python --version), Poetry $(poetry --version | cut -d' ' -f3)"
          export PROJECT_ROOT="$PWD"
          export PS1="(sask) $PS1"
        '';
      };
    };
}

