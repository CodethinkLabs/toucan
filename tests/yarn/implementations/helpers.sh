#!/bin/bash
#
# Copyright (C) 2013 Codethink Limited.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


# Helper functions for scenario tests.


export HOME="$DATADIR/home"
export PYTHONPATH="$SRCDIR:$PYTHONPATH"
export XDG_CONFIG_DIRS="$DATADIR/system-config-dir"
export XDG_CONFIG_HOME="$DATADIR/user-config-dir"
export XDG_DATA_DIRS="$DATADIR/system-data-dir"
export XDG_DATA_HOME="$DATADIR/user-data-dir"


# Create the home directory
if [[ ! -d "$HOME" ]]; then
    mkdir "$HOME"
fi


# Create a global git config for the test user
if [[ ! -e "$HOME/.gitconfig" ]]; then
    cat > "$HOME/.gitconfig" <<-EOF
[user]
    name = Test user
    email = test.user@project.org
EOF
fi


# Create a consonant register
if [[ ! -d "$DATADIR/system-config-dir/consonant" ]]; then
    mkdir -p "$DATADIR/system-config-dir/consonant"
    cat > "$DATADIR/system-config-dir/consonant/register.yaml" <<-EOF
schemas:
    org.consonant-project.toucan.schema.0: >
        file://$SRCDIR/data/org.consonant-project.toucan.schema.0.yaml
EOF
fi



dump_output()
{
    echo "STDOUT:"
    cat $DATADIR/stdout
    echo "STDERR:"
    cat $DATADIR/stderr
}


run_toucan_cli()
{
    if [ "$API" != "cli" ]; then
        return
    fi

    trap dump_output 0
    cd $DATADIR
    PARAMS=$(cat | xargs echo -n)
    $SRCDIR/toucan $PARAMS >$DATADIR/stdout 2>$DATADIR/stderr
    echo $? > $DATADIR/exit-code
    exit 0
}


run_python_test()
{
    trap dump_output 0
    cd $DATADIR
    CODE=$(cat)
    cat > test.py <<-EOF
import yaml

$CODE
EOF
    if ! python test.py 2>&1 >/dev/null; then
        py.test -q test.py
    fi
}


run_consonant_store_test()
{
    trap dump_output 0
    cd $DATADIR
    CODE=$(cat)
    cat > test.py <<-EOF
import consonant
import os
import yaml

store_location = os.path.abspath(os.path.join('board'))
factory = consonant.service.factories.ServiceFactory()
store = factory.service(store_location)

$CODE
EOF
    if ! python test.py 2>&1 >/dev/null; then
        py.test -q test.py
    fi
}

check_object_count()
{
    trap dump_output 0
    cd $DATADIR
    VALUE=$(cat)
    cat > test.py <<-EOF
import yaml, types

objects = $VALUE

with open('stdout', 'r') as stream:
    output = yaml.load_all(stream)
    if not isinstance(output, types.GeneratorType):
        print 'bad output'
    else:
        data = []
        for item in output:
            if item:
                data.append(item)
        assert len(data) == objects
EOF
    if ! python test.py 2>&1 >/dev/null; then
        py.test -q test.py
    fi
}

check_object_property()
{
    trap dump_output 0
    cd $DATADIR
    PROPERTY=$(cat)
    cat > test.py <<-EOF
import yaml, types

prop = $PROPERTY

with open('stdout', 'r') as stream:
    output = yaml.load_all(stream)
    if not isinstance(output, types.GeneratorType):
        raise Exception('Bad output')
    elif not isinstance(prop, dict):
        raise Exception('Property request must be a dict.')
    else:
        data = []
        for item in output:
            if item:
                data.append(item)
        assert data[prop['object']][prop['key']] == prop['value']
EOF
    if ! python test.py 2>&1 >/dev/null; then
        py.test -q test.py
    fi
}

check_object_property_order()
{
    trap dump_output 0
    cd $DATADIR
    OPTIONS=$(cat)
    cat > test.py <<-EOF
import yaml, types

options = $OPTIONS

with open('stdout', 'r') as stream:
    output = yaml.load_all(stream)
    if not isinstance(output, types.GeneratorType):
        raise Exception('Bad output')
    elif not isinstance(options, dict):
        raise Exception('Property request must be a dict.')
    else:
        data = []
        for item in output:
            if item:
                data.append(item)
        assert data[options['object'] - 1].keys() == options['order']
EOF
    if ! python test.py 2>&1 >/dev/null; then
        py.test -q test.py
    fi
}

check_object_property_length()
{
    trap dump_output 0
    cd $DATADIR
    OPTIONS=$(cat)
    cat > test.py <<-EOF
import yaml, types

options = $OPTIONS

with open('stdout', 'r') as stream:
    output = yaml.load_all(stream)
    if not isinstance(output, types.GeneratorType):
        raise Exception('Bad output')
    elif not isinstance(options, dict):
        raise Exception('Property request must be a dict.')
    else:
        data = []
        for item in output:
            if item:
                data.append(item)
        prop = data[options['object'] - 1][options['property']]
        assert len(prop) == options['length']
EOF
    if ! python test.py 2>&1 >/dev/null; then
        py.test -q test.py
    fi
}

check_object_property_existence()
{
    trap dump_output 0
    cd $DATADIR
    OPTIONS=$(cat)
    cat > test.py <<-EOF
import yaml, types

options = $OPTIONS

with open('stdout', 'r') as stream:
    output = yaml.load_all(stream)
    if not isinstance(output, types.GeneratorType):
        raise Exception('Bad output')
    elif not isinstance(options, dict):
        raise Exception('Property request must be a dict.')
    else:
        data = []
        for item in output:
            if item:
                data.append(item)
        assert options['property'] in data[options['object']]
EOF
    if ! python test.py 2>&1 >/dev/null; then
        py.test -q test.py
    fi
}
}
