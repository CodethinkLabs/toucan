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


export PYTHONPATH="$SRCDIR:$PYTHONPATH"
export XDG_CONFIG_DIRS="$DATADIR/system-config-dir"
export XDG_CONFIG_HOME="$DATADIR/user-config-dir"
export XDG_DATA_DIRS="$DATADIR/system-data-dir"
export XDG_DATA_HOME="$DATADIR/user-data-dir"


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
