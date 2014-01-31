#!/bin/bash

rm /tmp/toucan/lane.yaml
cat <<-EOF > "/tmp/toucan/lane.yaml"
name: Scenario
description: >
  Scenario test lane
views:
  - Default
EOF
