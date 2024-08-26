yml_to_yaml:
  fd -t f -e yml --threads=1 -x git mv {} {.}.yaml

ac:
  ansible-lint; yamllint
