#!/bin/bash

run_consonant_store_test <<-EOF
commit = store.ref('master').head
klass = store.klass(commit, 'card')
objects = store.objects(commit, klass)
f = open('/tmp/toucan/card', 'w+')
f.write(objects[0].uuid[0:7])
f.close()
EOF

uuid=$(grep "[:alnum:]" "/tmp/toucan/card")
rm /tmp/toucan/comment.yaml
cat <<-EOF > "/tmp/toucan/comment.yaml"
card: $uuid
comment: >
  Scenario test comment
author: Test User
EOF
