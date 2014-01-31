#!/bin/bash

TMPFILE="$DATADIR/.edited"

if [[ ! -e "$TMPFILE" ]]; then
  touch "$TMPFILE"
  rm /tmp/toucan/user.yaml
  cat <<-EOF > "/tmp/toucan/user.yaml"
  name: Scenario Test
  email: scenario.test@test.org
  roles:
    - admin
  default-view: notaview
  EOF
else
  rm /tmp/toucan/user.yaml
  cat <<-EOF > "/tmp/toucan/user.yaml"
  name: Scenario Test
  email: scenario.test@test.org
  roles:
    - admin
  default-view: Default
  EOF
fi

