#!/bin/bash

rm /tmp/toucan/milestone.yaml
cat <<-EOF > "/tmp/toucan/milestone.yaml"
short-name: scenario
name: Scenario test milestone
description: >
  This is a milestone created in a test.
deadline: 0000000000 +0000
EOF
