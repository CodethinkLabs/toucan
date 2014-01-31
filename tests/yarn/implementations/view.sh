#!/bin/bash

rm /tmp/toucan/view.yaml
cat <<-EOF > "/tmp/toucan/view.yaml"
name: Scenario
description: >
  Scenario test view
lanes:
  - Backlog
  - Doing
EOF
