#!/bin/bash

rm /tmp/toucan/card.yaml
cat <<-EOF > "/tmp/toucan/card.yaml"
title: Scenario Test
description: >
  This is a card created by the scenario test.
creator: Test User
lane: Backlog
reason: testing
milestone: testing
assignees:
  - Test User
EOF
