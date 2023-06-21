{ runCommand, ruff }:

runCommand "check-ruff" { nativeBuildInputs = [ ruff ]; } ''
  set -e
  ruff check --no-cache ${./..}
  touch $out
''
