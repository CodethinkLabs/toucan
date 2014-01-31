#!/bin/bash

rm /tmp/toucan/reason.yaml
cat <<-EOF > "/tmp/toucan/reason.yaml"
short-name: scenario
name: Scenario test reason
description: >
  This is a reason made in a test.
EOF
