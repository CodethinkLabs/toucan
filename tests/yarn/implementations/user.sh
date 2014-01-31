#!/bin/bash

rm /tmp/toucan/user.yaml
cat <<-EOF > "/tmp/toucan/user.yaml"
name: Scenario Test
email: scenario.test@test.org
roles:
  - admin
default-view: Default
EOF
