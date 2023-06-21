{ runCommand, python3Packages }:

runCommand "check-black" { nativeBuildInputs = [ python3Packages.black ]; } ''
  set -e
  black --check --diff ${./..}
  touch $out
''
