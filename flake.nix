{
  description = "Reticulum-MeshChatX development environment";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs {
          inherit system;
          config.allowUnfree = true;
        };

        python = pkgs.python312;
        node = pkgs.nodejs_22;
      in
      {
        devShells.default = pkgs.mkShell {
          buildInputs = with pkgs; [
            # Core
            git
            curl
            go-task
            pkg-config
            libffi
            openssl

            # Audio (for LXST/Telephony)
            libopus
            portaudio

            # Backend
            python
            poetry
            ruff

            # Frontend
            node
            pnpm

            # Electron & Linux Packaging
            electron
            fakeroot
            rpm
            dpkg
            wine
            mono

            # Android Development
            gradle
            openjdk17

            # Containerization
            docker
            docker-compose
          ];

          shellHook = ''
            echo "Reticulum-MeshChatX development environment"
            echo "Python version: $(${python}/bin/python --version)"
            echo "Node version:   $(${node}/bin/node --version)"
            echo "Task version:   $(task --version 2>/dev/null || echo 'not available')"
            echo "Poetry version: $(poetry --version 2>/dev/null || echo 'not available')"
            echo "PNPM version:   $(pnpm --version 2>/dev/null || echo 'not available')"
            
            # Set up development environment variables
            export LD_LIBRARY_PATH="${pkgs.libopus}/lib:${pkgs.portaudio}/lib:$LD_LIBRARY_PATH"
          '';
        };

        # Simple package definition for the backend
        packages.default = pkgs.python312Packages.buildPythonPackage {
          pname = "reticulum-meshchatx";
          version = "4.2.0";
          src = ./.;
          format = "pyproject";

          nativeBuildInputs = with pkgs; [
            python312Packages.setuptools
            python312Packages.wheel
          ];

          propagatedBuildInputs = with pkgs.python312Packages; [
            aiohttp
            psutil
            websockets
            bcrypt
            aiohttp-session
            cryptography
            requests
            ply
            # Note: rns, lxmf, lxst are handled via poetry or manual vendoring
          ];

          buildInputs = [
            pkgs.libopus
            pkgs.portaudio
          ];

          doCheck = false;
        };
      });
}
