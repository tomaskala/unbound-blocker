{ runCommand, pythonEnv }:

runCommand "check-mypy" { nativeBuildInputs = [ pythonEnv ]; } ''
  set -e
  python -m mypy --pretty --no-color-output ${./..}
  touch $out
''
