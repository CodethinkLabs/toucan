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


"""Representation, parsing and execution of Toucan board setup files."""


import consonant
import pygit2
import time
import yaml

from consonant.store import properties
from consonant.transaction import actions, transaction
from consonant.util import expressions, gitcli
from consonant.util.phase import Phase


class MetaData(object):

    """Service meta data in a board setup file."""

    def __init__(self, service_name, schema_name):
        self.service_name = service_name
        self.schema_name = schema_name


class BoardInfo(object):

    """Board information in a board setup file."""

    def __init__(self, name, description):
        self.name = name
        self.description = description


class View(object):

    """A view definition in a board setup file."""

    def __init__(self, name, description, lanes):
        self.name = name
        self.description = description
        self.lanes = lanes


class Lane(object):

    """A lane definition in a board setup file."""

    def __init__(self, name, description):
        self.name = name
        self.description = description


class User(object):

    """A user definition in a board setup file."""

    def __init__(self, name, email, roles):
        self.name = name
        self.email = email
        self.roles = roles


class SetupFile(object):

    """A Toucan board setup file."""

    def __init__(self):
        self.meta_data = None
        self.board_info = None
        self.views = {}
        self.lanes = {}
        self.users = {}


class SetupParserError(Exception):

    """Errors occuring while parsing Toucan board setup files."""

    pass


class SetupParser(object):

    """A parser for Toucan board setup files."""

    def parse(self, stream):
        """Parse a file stream and return a SetupFile on success."""

        # phase 1: load the input YAML
        with Phase() as phase:
            try:
                data = yaml.load(stream)
            except Exception, e:
                phase.error(e)

        # phase 2: validate the setup data
        with Phase() as phase:
            if not isinstance(data, dict):
                phase.error(SetupParserError(
                    'Setup file is not a YAML dictionary.'))
            else:
                self._validate_meta_data(phase, data)
                self._validate_board_info(phase, data)
                self._validate_views(phase, data)
                self._validate_lanes(phase, data)
                self._validate_users(phase, data)

        # phase 3: load the setup data into a SetupFile
        with Phase() as phase:
            setup_file = SetupFile()
            self._load_meta_data(phase, data, setup_file)
            self._load_board_info(phase, data, setup_file)
            self._load_views(phase, data, setup_file)
            self._load_lanes(phase, data, setup_file)
            self._load_users(phase, data, setup_file)
            return setup_file

    def _validate_meta_data(self, phase, data):
        # validate the service name
        if not 'name' in data:
            phase.error(SetupParserError(
                'Setup file defines no service name'))
        elif not isinstance(data['name'], basestring):
            phase.error(SetupParserError(
                'Setup file defines a non-string service name: %s' %
                data['name']))
        elif not expressions.service_name.match(data['name']):
            phase.error(SetupParserError(
                'Setup file defines an invalid service name: %s' %
                data['name']))

        # validate the schema name
        if not 'schema' in data:
            phase.error(SetupParserError(
                'Setup file defines no schema name'))
        elif not isinstance(data['schema'], basestring):
            phase.error(SetupParserError(
                'Setup file defines a non-string schema name: %s' %
                data['schema']))
        elif not expressions.schema_name.match(data['schema']):
            phase.error(SetupParserError(
                'Setup file defines an invalid schema name: %s' %
                data['schema']))

    def _load_meta_data(self, phase, data, setup_file):
        setup_file.meta_data = MetaData(data['name'], data['schema'])

    def _validate_board_info(self, phase, data):
        if not 'info' in data:
            phase.error(SetupParserError(
                'Setup file defines no board info'))
        elif not isinstance(data['info'], dict):
            phase.error(SetupParserError(
                'Setup file defines non-dict board info: %s' %
                data['info']))
        else:
            # validate the board name
            if not 'name' in data['info']:
                phase.error(SetupParserError(
                    'Setup file defines no board name'))
            elif not isinstance(data['info']['name'], basestring):
                phase.error(SetupParserError(
                    'Setup file defines a non-string board name: %s' %
                    data['info']['name']))

            # validate the board description
            if 'description' in data['info'] and \
                    not isinstance(data['info']['description'], basestring):
                phase.error(SetupParserError(
                    'Setup file defines a non-string board description: %s' %
                    data['info']['description']))

    def _load_board_info(self, phase, data, setup_file):
        setup_file.board_info = BoardInfo(
            data['info']['name'],
            data['info'].get('description', None))

    def _validate_views(self, phase, data):
        if not 'views' in data:
            return

        if not isinstance(data['views'], list):
            phase.error(SetupParserError(
                'Setup file defines a non-list views entry'))
        else:
            for view in data['views']:
                if not isinstance(view, dict):
                    phase.error(SetupParserError(
                        'Setup file defines a non-dict view: %s' % view))
                else:
                    # validate the view name
                    if not 'name' in view:
                        phase.error(SetupParserError(
                            'Setup file defines a view without a name: %s' %
                            view))
                    elif not isinstance(view['name'], basestring):
                        phase.error(SetupParserError(
                            'Setup file defines a non-string view name: %s' %
                            view['name']))

                    # validate the view description
                    if 'description' in view \
                            and not isinstance(
                                view['description'], basestring):
                        phase.error(SetupParserError(
                            'Setup file defines a non-string view '
                            'description: %s' % view['description']))

                    # validate the lane references in the view
                    if not 'lanes' in view:
                        phase.error(SetupParserError(
                            'Setup file defines a view with no lanes: %s' %
                            view))
                    elif not isinstance(view['lanes'], list):
                        phase.error(SetupParserError(
                            'Setup file defines a view with a non-list '
                            'lanes entry: %s' % view))
                    else:
                        for lane in view['lanes']:
                            if not isinstance(lane, basestring):
                                phase.error(SetupParserError(
                                    'Setup file defines a view with a '
                                    'non-string lane name reference: %s' %
                                    lane))
                            else:
                                lanes = [x for x in data.get('lanes', [])
                                         if isinstance(x, dict)
                                         and 'name' in x]
                                matches = [x for x in lanes
                                           if x['name'] == lane]
                                if not matches:
                                    phase.error(SetupParserError(
                                        'Setup file defines a view that '
                                        'refers to a non-existent lane: %s' %
                                        lane))

    def _load_views(self, phase, data, setup_file):
        if not 'views' in data:
            return
        for view in data['views']:
            setup_file.views[view['name']] = View(
                view['name'],
                view.get('description', None),
                view.get('lanes', []))

    def _validate_lanes(self, phase, data):
        if not 'lanes' in data:
            return

        if not isinstance(data['lanes'], list):
            phase.error(SetupParserError(
                'Setup file defines a non-lists lanes entry'))
        else:
            for lane in data['lanes']:
                if not isinstance(lane, dict):
                    phase.error(SetupParserError(
                        'Setup file defines a non-dict lane: %s' % lane))
                else:
                    # validate the lane name
                    if not 'name' in lane:
                        phase.error(SetupParserError(
                            'Setup file defines a lane without a name: %s' %
                            lane))
                    elif not isinstance(lane['name'], basestring):
                        phase.error(SetupParserError(
                            'Setup file defines a non-string lane name: %s' %
                            lane['name']))

                    # validate the lane description
                    if 'description' in lane \
                            and not isinstance(
                                lane['description'], basestring):
                        phase.error(SetupParserError(
                            'Setup file defines a non-string lane '
                            'description: %s' % lane['description']))

            # detect ambiguous lanes with the same name
            valid_lanes = [x for x in data['lanes']
                           if isinstance(x, dict) and 'name' in x]
            names = {}
            for lane in valid_lanes:
                if not lane['name'] in names:
                    names[lane['name']] = []
                names[lane['name']].append(lane)
            for name, lanes in names.iteritems():
                if len(lanes) > 1:
                    phase.error(SetupParserError(
                        'Setup file defines %d lanes with the same name: %s' %
                        (len(lanes), name)))

    def _load_lanes(self, phase, data, setup_file):
        if not 'lanes' in data:
            return
        for lane in data['lanes']:
            setup_file.lanes[lane['name']] = Lane(
                lane['name'],
                lane.get('description', None))

    def _validate_users(self, phase, data):
        if not 'users' in data:
            phase.error(SetupParserError(
                'Setup file defines no users'))
        else:
            if not isinstance(data['users'], list):
                phase.error(SetupParserError(
                    'Setup file defines a non-list users entry'))
            else:
                for user in data['users']:
                    if not isinstance(user, dict):
                        phase.error(SetupParserError(
                            'Setup file defines a non-dict user: %s' % user))
                else:
                    # validate user name
                    if not 'name' in user:
                        phase.error(SetupParserError(
                            'Setup file defines a user without a name: %s' %
                            user))
                    elif not isinstance(user['name'], basestring):
                        phase.error(SetupParserError(
                            'Setup file defines a non-string user name: %s' %
                            user['name']))

                    # validate user email
                    if not 'email' in user:
                        phase.error(SetupParserError(
                            'Setup file defines a user without an email '
                            'address: %s' % (user)))
                    elif not isinstance(user['email'], basestring):
                        phase.error(SetupParserError(
                            'Setup file defines a non-string user email: %s' %
                            user['email']))

                    # validate user roles
                    if not 'roles' in user:
                        phase.error(SetupParserError(
                            'Setup file defines a user with no roles: %s' %
                            user))
                    elif not isinstance(user['roles'], list):
                        phase.error(SetupParserError(
                            'Setup file defines a non-list user roles '
                            'entry: %s' % user['roles']))
                    else:
                        for role in user['roles']:
                            if not isinstance(role, basestring):
                                phase.error(SetupParserError(
                                    'Setup file defines a non-string '
                                    'user role: %s' % role))

                # detect ambiguous users with the same email address
                valid_users = [x for x in data['users']
                               if isinstance(x, dict) and 'email' in x]
                emails = {}
                for user in valid_users:
                    if not user['email'] in emails:
                        emails[user['email']] = []
                    emails[user['email']].append(user)
                for email, users in emails.iteritems():
                    if len(users) > 1:
                        phase.error(SetupParserError(
                            'Setup file defines %d users with the same '
                            'email address: %s' % (len(users), email)))

                # fail if there is no admin user
                valid_users = [x for x in data['users']
                               if isinstance(x, dict)
                               and 'roles' in x
                               and isinstance(x['roles'], list)]
                admins = []
                for user in valid_users:
                    if 'admin' in user['roles']:
                        admins.append(user)
                if not admins:
                    phase.error(SetupParserError(
                        'Setup file defines no users with the role "admin"'))

    def _load_users(self, phase, data, setup_file):
        if not 'users' in data:
            return
        for user in data['users']:
            setup_file.users[user['name']] = User(
                user['name'],
                user['email'],
                user.get('roles', []))


class SetupRunner(object):

    """A class that performs a setup against a repository and setup file."""

    def run(self, repo, setup_file):
        """Perform the board setup against a repository and setup file."""

        author = pygit2.Signature(
            gitcli.subcommand(repo, ['config', 'user.name']),
            gitcli.subcommand(repo, ['config', 'user.email']))

        self._create_initial_commit(repo, setup_file, author)
        self._populate_store(repo, setup_file, author)

    def _create_initial_commit(self, repo, setup_file, author):
        builder = repo.TreeBuilder()
        self._create_meta_data(repo, setup_file, builder)
        tree_oid = builder.write()
        repo.create_commit(
            'refs/heads/master',
            author, author,
            'Create store for board "%s"' % setup_file.board_info.name,
            tree_oid, [])

    def _create_meta_data(self, repo, setup_file, builder):
        meta_data = {
            'name': setup_file.meta_data.service_name,
            'schema': setup_file.meta_data.schema_name,
            }
        data = yaml.dump(meta_data)
        blob_oid = repo.create_blob(data)
        builder.insert('consonant.yaml', blob_oid, pygit2.GIT_FILEMODE_BLOB)

    def _populate_store(self, repo, setup_file, author):
        # obtain a Consonant store for the repository
        store_location = repo.path
        factory = consonant.service.factories.ServiceFactory()
        store = factory.service(store_location)

        # define what to base the initial transaction on
        begin_action = actions.BeginAction(
            'begin', store.ref('master').head.sha1)

        # define where to land the initial transaction
        commit_action = actions.CommitAction(
            'commit', 'refs/heads/master',
            '%s <%s>' % (author.name, author.email), time.strftime('%s %z'),
            '%s <%s>' % (author.name, author.email), time.strftime('%s %z'),
            'Populate store for board "%s"' % setup_file.board_info.name)

        # assign an action ID to each object to be created
        action_ids = {}
        for view in setup_file.views.itervalues():
            action_ids[view] = len(action_ids) + 1
        for lane in setup_file.lanes.itervalues():
            action_ids[lane] = len(action_ids) + 1
        for user in setup_file.users.itervalues():
            action_ids[user] = len(action_ids) + 1

        # create actions for all the objects
        create_actions = self._create_objects(setup_file, action_ids)

        # create a transaction to populate the store with the initial
        # board info, views, lanes and users
        t = transaction.Transaction(
            [begin_action] + create_actions + [commit_action])

        # apply the transaction
        store.apply_transaction(t)

    def _create_objects(self, setup_file, action_ids):
        actions = []

        actions.append(self._create_board_info(setup_file))

        # first pass: create all view, lane, user and user config objects
        for view in setup_file.views.itervalues():
            actions.append(self._create_view(setup_file, action_ids, view))
        for lane in setup_file.lanes.itervalues():
            actions.append(self._create_lane(setup_file, action_ids, lane))
        for user in setup_file.users.itervalues():
            actions.append(self._create_user(setup_file, action_ids, user))
            actions.append(self._create_user_config(
                setup_file, action_ids, user))

        # second pass: link all these objects together
        for view in setup_file.views.itervalues():
            actions.append(self._update_view(setup_file, action_ids, view))
        for lane in setup_file.lanes.itervalues():
            actions.append(self._update_lane(setup_file, action_ids, lane))
        for user in setup_file.users.itervalues():
            actions.append(self._update_user(setup_file, action_ids, user))
            actions.append(self._update_user_config(
                setup_file, action_ids, user))

        return actions

    def _create_board_info(self, setup_file):
        props = []
        props.append(properties.TextProperty(
            'name', setup_file.board_info.name))
        if setup_file.board_info.description:
            props.append(properties.TextProperty(
                'description', setup_file.board_info.description))
        return actions.CreateAction('info', 'info', props)

    def _create_view(self, setup_file, action_ids, view):
        action_id = action_ids[view]
        props = []
        props.append(properties.TextProperty('name', view.name))
        if view.description:
            props.append(properties.TextProperty(
                'description', view.description))
        return actions.CreateAction(action_id, 'view', props)

    def _create_lane(self, setup_file, action_ids, lane):
        action_id = action_ids[lane]
        props = []
        props.append(properties.TextProperty('name', lane.name))
        if lane.description:
            props.append(properties.TextProperty(
                'description', lane.description))
        return actions.CreateAction(action_id, 'lane', props)

    def _create_user(self, setup_file, action_ids, user):
        action_id = action_ids[user]
        props = []
        props.append(properties.TextProperty('name', user.name))
        if user.email:
            props.append(properties.TextProperty('email', user.email))
        props.append(properties.ListProperty(
            'roles', [properties.TextProperty('roles', x)
                      for x in user.roles]))
        return actions.CreateAction(action_id, 'user', props)

    def _create_user_config(self, setup_file, action_ids, user):
        action_id = 'config-%s' % action_ids[user]
        return actions.CreateAction(action_id, 'user-config', [])

    def _update_view(self, setup_file, action_ids, view):
        references = []
        for name in view.lanes:
            lane = [x for x in setup_file.lanes.itervalues()
                    if x.name == name][0]
            action_id = action_ids[lane]
            references.append(properties.ReferenceProperty(
                'lanes', {'action': action_id}))

        action_id = action_ids[view]
        props = [properties.ListProperty('lanes', references)]
        return actions.UpdateAction(
            'update%s' % action_id, None, action_id, props)

    def _update_lane(self, setup_file, action_ids, lane):
        views = [x for x in setup_file.views.itervalues()
                 if x.lanes and lane.name in x.lanes]

        references = []
        for view in views:
            action_id = action_ids[view]
            references.append(properties.ReferenceProperty(
                'views', {'action': action_id}))

        action_id = action_ids[lane]
        props = [properties.ListProperty('views', references)]
        return actions.UpdateAction(
            'update-%s' % action_id, None, action_id, props)

    def _update_user(self, setup_file, action_ids, user):
        action_id = action_ids[user]
        config_action_id = 'config-%s' % action_id
        props = [properties.ReferenceProperty(
            'config', {'action': config_action_id})]
        return actions.UpdateAction(
            'update-%s' % action_id, None, action_id, props)

    def _update_user_config(self, setup_file, action_ids, user):
        user_action_id = action_ids[user]
        action_id = 'config-%s' % user_action_id
        props = [properties.ReferenceProperty(
            'user', {'action': user_action_id})]
        return actions.UpdateAction(
            'update-%s' % action_id, None, action_id, props)
