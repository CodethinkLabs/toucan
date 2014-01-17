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

    def __init__(self, name, description, cards):
        self.name = name
        self.description = description
        self.cards = cards


class User(object):

    """A user definition in a board setup file."""

    def __init__(self, name, email, roles, default_view, avatar):
        self.name = name
        self.email = email
        self.roles = roles
        self.default_view = default_view
        self.avatar = avatar


class Card(object):

    """A card definition in a board setup file."""

    def __init__(self, identifier, title, creator, description,
                 lane, reason, milestone, assignees, comments):
        self.id = identifier
        self.title = title
        self.creator = creator
        self.description = description
        self.lane = lane
        self.reason = reason
        self.milestone = milestone
        self.assignees = assignees
        self.comments = comments


class Reason(object):

    """A reason definition in a board setup file."""

    def __init__(self, short_name, name, description, work_items):
        self.short_name = short_name
        self.name = name
        self.description = description
        self.work_items = work_items


class Milestone(object):

    """A milestone definition in a board setup file."""

    def __init__(self, short_name, name, description, deadline):
        self.short_name = short_name
        self.name = name
        self.description = description
        self.deadline = deadline


class Comment(object):

    """A comment definition in a board setup file."""

    def __init__(self, identifier, content, author, attachment, card):
        self.id = identifier
        self.content = content
        self.author = author
        self.attachment = attachment
        self.card = card


class Attachment(object):

    """An attachment definition in a board setup file."""

    def __init__(self, name, comment):
        self.name = name
        self.comment = comment


class SetupFile(object):

    """A Toucan board setup file."""

    def __init__(self):
        # The setup file can define any of the following, so all of them
        # should have the potential to be loaded.
        self.meta_data = None
        self.board_info = None
        self.views = {}
        self.lanes = {}
        self.users = {}
        self.cards = {}
        self.reasons = {}
        self.milestones = {}
        self.comments = {}
        self.attachments = {}


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
                self._validate_cards(phase, data)
                self._validate_reasons(phase, data)
                self._validate_milestones(phase, data)
                self._validate_comments(phase, data)
                self._validate_attachments(phase, data)

        # phase 3: load the setup data into a SetupFile
        with Phase() as phase:
            setup_file = SetupFile()
            self._load_meta_data(phase, data, setup_file)
            self._load_board_info(phase, data, setup_file)
            self._load_views(phase, data, setup_file)
            self._load_lanes(phase, data, setup_file)
            self._load_users(phase, data, setup_file)
            self._load_cards(phase, data, setup_file)
            self._load_reasons(phase, data, setup_file)
            self._load_milestones(phase, data, setup_file)
            self._load_comments(phase, data, setup_file)
            self._load_attachments(phase, data, setup_file)

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

                    if 'cards' in lane:
                        if not isinstance(lane['cards'], list):
                            phase.error(SetupParserError(
                                'Setup file defines a lane with non-list '
                                'cards property: %s' % lane['cards']))
                        else:
                            for card in lane['cards']:
                                if not isinstance(card, int):
                                    phase.error(SetupParserError(
                                        'Setup file defines a comment with '
                                        'non-int card reference: %s' % card))
                                else:
                                    cards = [x for x in data.get('cards', [])
                                             if isinstance(x, dict)
                                             and 'id' in x]
                                    matches = [x for x in cards
                                               if x['id'] in lane['cards']]
                                    if not matches:
                                        phase.error(SetupParserError(
                                            'Setup file defines a lane '
                                            'with non-existant card reference:'
                                            ' %s' % card))

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
                lane.get('description', None),
                lane.get('cards', []))

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

                    # validate user default-view
                    if 'default-view' in user:
                        if not isinstance(user['default-view'], basestring):
                            phase.error(SetupParserError(
                                'Setup file defines a non-string user default-'
                                'view reference: %s' % user['default-view']))

                    # validate user avatar
                    if 'avatar' in user:
                        if not isinstance(user['avatar'], basestring):
                            phase.error(SetupParserError(
                                'Setup file defines a non-string user avatar: '
                                '%s' % user['avatar']))

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
                user.get('roles', []),
                user.get('default-view', ''),
                user.get('avatar', ''))

    def _validate_cards(self, phase, data):
        if not 'cards' in data:
            return

        if not isinstance(data['cards'], list):
            phase.error(SetupParserError(
                'Setup file defines a non-list cards entry.'))
        else:
            for card in data['cards']:
                if not isinstance(card, dict):
                    phase.error(SetupParserError(
                        'Setup file defines a non-dict card: %s' % card))
                else:
                    self._validate_card_id(phase, card)
                    self._validate_card_title(phase, card)
                    self._validate_card_creator(phase, card, data)
                    self._validate_card_description(phase, card)
                    self._validate_card_lane(phase, card, data)
                    self._validate_card_milestone(phase, card, data)
                    self._validate_card_reason(phase, card, data)
                    self._validate_card_assignees(phase, card, data)

    def _validate_card_id(self, phase, card):
        if not 'id' in card:
            phase.error(SetupParserError(
                'Setup file defines a card without an id: %s' % card))
        elif not isinstance(card['id'], int):
            phase.error(SetupParserError(
                'Setup file defines a card with non-int id: %s' % card['id']))

    def _validate_card_title(self, phase, card):
        # validate card title
        if not 'title' in card:
            phase.error(SetupParserError(
                'Setup file defines a card without a title: %s' % card))
        elif not isinstance(card['title'], basestring):
            phase.error(SetupParserError(
                'Setup file defines a card with non-string title: %s' %
                card['title']))

    def _validate_card_creator(self, phase, card, data):
        # validate card creator
        if not 'creator' in card:
            phase.error(SetupParserError(
                'Setup file defines a card without a creator: %s' % card))
        elif not isinstance(card['creator'], basestring):
            phase.error(SetupParserError(
                'Setup file defines a card with non-string creator: %s' %
                card['creator']))
        else:
            users = [x for x in data.get('users', [])
                     if isinstance(x, dict) and 'name' in x]
            matches = [x for x in users if x['name'] == card['creator']]
            if not matches:
                phase.error(SetupParserError(
                    'Setup file defines a card that refers '
                    'to a non-existent user: %s' % card))

    def _validate_card_description(self, phase, card):
        # validate card description
        if 'description' in card and \
                not isinstance(card['description'], basestring):
            phase.error(SetupParserError(
                'Setup file defines a card with non-string description: %s' %
                card['description']))

    def _validate_card_lane(self, phase, card, data):
        # validate card lane
        if not 'lane' in card:
            phase.error(SetupParserError(
                'Setup file defines a card without a lane: %s' % card))
        elif not isinstance(card['lane'], basestring):
            phase.error(SetupParserError(
                'Setup file defines a card with non-string lane: %s' %
                card['lane']))
        else:
            lanes = [x for x in data.get('lanes', [])
                     if isinstance(x, dict) and 'name' in x]
            matches = [x for x in lanes if x['name'] == card['lane']]
            if not matches:
                phase.error(SetupParserError(
                    'Setup file defines a card that refers '
                    'to a non-existent lane: %s' % card))

    def _validate_card_milestone(self, phase, card, data):
        # validate card milestone
        if 'milestone' in card:
            if not isinstance(card['milestone'], basestring):
                phase.error(SetupParserError(
                    'Setup file defines a card with non-string '
                    'milestone reference: %s' % card['milestone']))
            else:
                milestones = [x for x in data.get('milestones', [])
                              if isinstance(x, dict) and 'name' in x]
                matches = [x for x in milestones
                           if x['short-name'] == card['milestone']]
                if not matches:
                    phase.error(SetupParserError(
                        'Setup file defines a card that refers '
                        'to a non-existent milestone: %s' % card))

    def _validate_card_reason(self, phase, card, data):
        # validate card reason
        if not 'reason' in card:
            phase.error(SetupParserError(
                'Setup file defines a card without a reason: %s' % card))
        elif not isinstance(card['reason'], basestring):
            phase.error(SetupParserError(
                'Setup file defines a card with non-string '
                'reason reference: %s' % card['reason']))
        else:
            reasons = [x for x in data.get('reasons', [])
                       if isinstance(x, dict) and 'short-name' in x]
            matches = [x for x in reasons if x['short-name'] == card['reason']]
            if not matches:
                phase.error(SetupParserError(
                    'Setup file defines a card that refers '
                    'to a non-existent reason: %s' % card))

    def _validate_card_assignees(self, phase, card, data):
        # validate card assignees
        if 'assignees' in card:
            if not isinstance(card['assignees'], list):
                phase.error(SetupParserError(
                    'Setup file defines a card with non-list '
                    'assignees: %s' % card))
            else:
                for assignee in card['assignees']:
                    if not isinstance(assignee, basestring):
                        phase.error(SetupParserError(
                            'Setup file defines a card with '
                            'non-string assignee: %s' % card))
                    else:
                        users = [x for x in data.get('users', [])
                                 if isinstance(x, dict) and 'name' in x]
                        matches = [x for x in users if x['name'] == assignee]
                        if not matches:
                            phase.error(SetupParserError(
                                'Setup file defines a card that refers to '
                                'a non-existent user: %s' % card))

    def _load_cards(self, phase, data, setup_file):
        if not 'cards' in data:
            return
        for card in data['cards']:
            setup_file.cards[card['title']] = Card(
                card['id'],
                card['title'],
                card['creator'],
                card.get('description', None),
                card['lane'],
                card['reason'],
                card.get('milestone', None),
                card.get('assignees', []),
                card.get('comments', []))

    def _validate_reasons(self, phase, data):
        if not 'reasons' in data:
            return
        if not isinstance(data['reasons'], list):
            phase.error(SetupParserError(
                'Setup file defines a non-list reasons entry.'))
        else:
            for reason in data['reasons']:
                if not isinstance(reason, dict):
                    phase.error(SetupParserError(
                        'Setup file defines a non-dict reason: %s' % reason))
                else:
                    # validate short_name
                    if not 'short-name' in reason:
                        phase.error(SetupParserError(
                            'Setup file defines a reason without a '
                            'short-name: %s' % reason))
                    elif not isinstance(reason['short-name'], basestring):
                        phase.error(SetupParserError(
                            'Setup file defines a reason with non-string '
                            'short_name: %s' % reason['short-name']))

                    # validate name
                    if not 'name' in reason:
                        phase.error(SetupParserError(
                            'Setup file defines a reason without a name: %s' %
                            reason))
                    elif not isinstance(reason['name'], basestring):
                        phase.error(SetupParserError(
                            'Setup file defines a reason with non-string '
                            'name: %s' % reason['name']))

                    # validate description
                    if 'description' in reason:
                        if not isinstance(reason['description'], basestring):
                            phase.error(SetupParserError(
                                'Setup file defines a reason with non-string '
                                'description: %s' % reason['description']))

                    # validate work-items
                    # TODO:
                    #   These are references to an remote store, which is
                    #   currently unsupported by python-consonant.

    def _load_reasons(self, phase, data, setup_file):
        if not 'reasons' in data:
            return
        for reason in data['reasons']:
            setup_file.reasons[reason['name']] = Reason(
                reason['short-name'],
                reason['name'],
                reason.get('description', None),
                reason.get('work-items', []))

    def _validate_milestones(self, phase, data):
        if not 'milestones' in data:
            return
        if not isinstance(data['milestones'], list):
            phase.error(SetupParserError(
                'Setup file defines a non-list milestones entry.'))
        else:
            for milestone in data['milestones']:
                if not isinstance(milestone, dict):
                    phase.error(SetupParserError(
                        'Setup file defines a non-dict milestone: %s' %
                        milestone))
                else:
                    # validate short_name
                    if not 'short-name' in milestone:
                        phase.error(SetupParserError(
                            'Setup file defines a milestone without a '
                            'short-name: %s' % milestone))
                    elif not isinstance(milestone['short-name'], basestring):
                        phase.error(SetupParserError(
                            'Setup file defines a milestone with non-string '
                            'short_name: %s' % milestone['short-name']))

                    # validate name
                    if not 'name' in milestone:
                        phase.error(SetupParserError(
                            'Setup file defines a milestone without a name: %s'
                            % milestone))
                    elif not isinstance(milestone['name'], basestring):
                        phase.error(SetupParserError(
                            'Setup file defines a milestone with non-string '
                            'name: %s' % milestone['name']))

                    # validate description
                    if 'description' in milestone:
                        if not isinstance(
                                milestone['description'], basestring):
                            phase.error(SetupParserError(
                                'Setup file defines a milestone with '
                                'non-string'' description: %s'
                                % milestone['description']))

                    # validate deadline
                    if not 'deadline' in milestone:
                        phase.error(SetupParserError(
                            'Setup file defines a milestone without a '
                            'deadline: %s' % milestone))
                    elif not isinstance(milestone['deadline'], basestring):
                        phase.error(SetupParserError(
                            'Setup file defines a milestone with non-string '
                            'deadline: %s' % milestone['deadline']))

    def _load_milestones(self, phase, data, setup_file):
        if not 'milestones' in data:
            return
        for milestone in data['milestones']:
            setup_file.milestones[milestone['short-name']] = Milestone(
                milestone['short-name'],
                milestone['name'],
                milestone.get('description', None),
                milestone['deadline'])

    def _validate_comments(self, phase, data):
        if not 'comments' in data:
            return
        if not isinstance(data['comments'], list):
            phase.error(SetupParserError(
                'Setup file defines a non-list comments entry.'))
        else:
            for comment in data['comments']:
                if not isinstance(comment, dict):
                    phase.error(SetupParserError(
                        'Setup file defines a non-dict comment: %s' % comment))
                else:
                    if not 'id' in comment:
                        phase.error(SetupParserError(
                            'Setup file defines a comment without an id: %s' %
                            comment))
                    elif not isinstance(comment['id'], int):
                        phase.error(SetupParserError(
                            'Setup file defines a comment with non-int id: '
                            '%s' % comment['id']))

                    # validate comment
                    if not 'comment' in comment:
                        phase.error(SetupParserError(
                            'Setup file defines a comment without a comment:'
                            ' %s' % comment))
                    elif not isinstance(comment['comment'], basestring):
                        phase.error(SetupParserError(
                            'Setup file defines a comment with non-string '
                            'comment: %s' % comment['comment']))

                    # validate author
                    if not 'author' in comment:
                        phase.error(SetupParserError(
                            'Setup file defines a comment without an author: '
                            '%s' % comment))
                    elif not isinstance(comment['author'], basestring):
                        phase.error(SetupParserError(
                            'Setup file defines a comment with non-string '
                            'author reference: %s' % comment['author']))
                    else:
                        users = [x for x in data.get('users',
                                 []) if isinstance(x, dict)
                                 and 'name' in x]
                        matches = [x for x in users
                                   if x['name'] == comment['author']]
                        if not matches:
                            phase.error(SetupParserError(
                                'Setup file defines a comment with a '
                                'non-existant author: %s' % comment))

                    # validate attachment
                    if 'attachment' in comment:
                        if not isinstance(comment['attachment'], basestring):
                            phase.error(SetupParserError(
                                'Setup file defines a comment with non-string '
                                'attachment reference: %s' % comment))
                        else:
                            attachs = [x for x in data.get('attachments', [])
                                       if isinstance(x, dict)
                                       and 'name' in x]
                            matches = [x for x in attachs
                                       if x['name'] == comment['attachment']]
                            if not matches:
                                phase.error(SetupParserError(
                                    'Setup file defines a comment with '
                                    'non-existant attachment reference: %s'
                                    % comment))

                    if not 'card' in comment:
                        phase.error(SetupParserError(
                            'Setup file defines a comment without a card: %s' %
                            comment))
                    elif not isinstance(comment['card'], int):
                        phase.error(SetupParserError(
                            'Setup file defines a comment with non-int card '
                            'reference: %s' % comment['card']))
                    else:
                        cards = [x for x in data.get('cards', [])
                                 if isinstance(x, dict) and 'id' in x]
                        matches = [x for x in cards
                                   if x['id'] == comment['card']]
                        if not matches:
                            phase.error(SetupParserError(
                                'Setup file defines a comment with '
                                'non-existant card reference: %s' % comment))

    def _load_comments(self, phase, data, setup_file):
        if not 'comments' in data:
            return
        for comment in data['comments']:
            setup_file.comments[comment['id']] = Comment(
                comment['id'],
                comment['comment'],
                comment['author'],
                comment.get('attachment', None),
                comment['card'])

    def _validate_attachments(self, phase, data):
        if not 'attachments' in data:
            return
        if not isinstance(data['attachments'], list):
            phase.error(SetupParserError(
                'Setup file defines non-list attachments entry.'))
        else:
            for attachment in data['attachments']:
                if not isinstance(attachment, dict):
                    phase.error(SetupParserError(
                        'Setup file defines a non-dict attachment: %s'
                        % attachment))
                else:
                    # validate name
                    if not 'name' in attachment:
                        phase.error(SetupParserError(
                            'Setup file defines an attachment without a name: '
                            '%s' % attachment))
                    elif not isinstance(attachment['name'], basestring):
                        phase.error(SetupParserError(
                            'Setup file defines an attachment with non-string '
                            'name: %s' % attachment['name']))

                    if not 'comment' in attachment:
                        phase.error(SetupParserError(
                            'Setup file defines an attachment without a '
                            'comment: %s' % attachment['comment']))

    def _load_attachments(self, phase, data, setup_file):
        if not 'attachments' in data:
            return
        for attachment in data['attachments']:
            setup_file.attachments[attachment['name']] = Attachment(
                attachment['name'],
                attachment['comment'])


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
        for card in setup_file.cards.itervalues():
            action_ids[card] = len(action_ids) + 1
        for reason in setup_file.reasons.itervalues():
            action_ids[reason] = len(action_ids) + 1
        for milestone in setup_file.milestones.itervalues():
            action_ids[milestone] = len(action_ids) + 1
        for comment in setup_file.comments.itervalues():
            action_ids[comment] = len(action_ids) + 1
        for attachment in setup_file.attachments.itervalues():
            action_ids[attachment] = len(action_ids) + 1

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
        for card in setup_file.cards.itervalues():
            actions.append(self._create_card(setup_file, action_ids, card))
        for reason in setup_file.reasons.itervalues():
            actions.append(self._create_reason(setup_file, action_ids, reason))
        for milestone in setup_file.milestones.itervalues():
            actions.append(self._create_milestone(
                setup_file, action_ids, milestone))
        for comment in setup_file.comments.itervalues():
            actions.append(self._create_comment(
                setup_file, action_ids, comment))
        for attachment in setup_file.attachments.itervalues():
            actions.append(self._create_attachment(
                setup_file, action_ids, attachment))

        # second pass: link all these objects together
        for view in setup_file.views.itervalues():
            actions.append(self._update_view(setup_file, action_ids, view))
        for lane in setup_file.lanes.itervalues():
            actions.append(self._update_lane(setup_file, action_ids, lane))
        for user in setup_file.users.itervalues():
            actions.append(self._update_user(setup_file, action_ids, user))
        for card in setup_file.cards.itervalues():
            actions.append(self._update_card(setup_file, action_ids, card))
        for reason in setup_file.reasons.itervalues():
            actions.append(self._update_reason(setup_file, action_ids, reason))
        for milestone in setup_file.milestones.itervalues():
            actions.append(self._update_milestone(
                setup_file, action_ids, milestone))
        for comment in setup_file.comments.itervalues():
            actions.append(self._update_comment(
                setup_file, action_ids, comment))
        for attachment in setup_file.attachments.itervalues():
            actions.append(self._update_attachment(
                setup_file, action_ids, attachment))

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
        props.append(properties.TextProperty('email', user.email))
        props.append(properties.ListProperty(
            'roles', [properties.TextProperty('roles', x)
                      for x in user.roles]))
        if user.avatar:
            props.append(properties.TextProperty('avatar', user.avatar))
        return actions.CreateAction(action_id, 'user', props)

    def _create_card(self, setup_file, action_ids, card):
        action_id = action_ids[card]
        props = []
        props.append(properties.TextProperty('title', card.title))
        if card.description:
            props.append(properties.TextProperty(
                'description', card.description))
        return actions.CreateAction(action_id, 'card', props)

    def _create_reason(self, setup_file, action_ids, reason):
        action_id = action_ids[reason]
        props = []
        props.append(properties.TextProperty('short-name', reason.short_name))
        props.append(properties.TextProperty('name', reason.name))
        if reason.description:
            props.append(properties.TextProperty(
                'description', reason.description))
        return actions.CreateAction(action_id, 'reason', props)

    def _create_milestone(self, setup_file, action_ids, milestone):
        action_id = action_ids[milestone]
        props = []
        props.append(properties.TextProperty(
            'short-name', milestone.short_name))
        props.append(properties.TextProperty('name', milestone.name))
        if milestone.description:
            props.append(properties.TextProperty(
                'description', milestone.description))
        props.append(properties.TimestampProperty(
            'deadline', milestone.deadline))
        return actions.CreateAction(action_id, 'milestone', props)

    def _create_comment(self, setup_file, action_ids, comment):
        action_id = action_ids[comment]
        props = []
        props.append(properties.TextProperty('comment', comment.content))
        return actions.CreateAction(action_id, 'comment', props)

    def _create_attachment(self, setup_file, action_ids, attachment):
        action_id = action_ids[attachment]
        props = []
        props.append(properties.TextProperty('name', attachment.name))
        return actions.CreateAction(action_id, 'attachment', props)

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
            'update-%s' % action_id, None, action_id, props)

    def _update_lane(self, setup_file, action_ids, lane):
        props = []
        views = [x for x in setup_file.views.itervalues()
                 if x.lanes and lane.name in x.lanes]

        references = []
        for view in views:
            action_id = action_ids[view]
            references.append(properties.ReferenceProperty(
                'views', {'action': action_id}))

        props.append(properties.ListProperty('views', references))

        if lane.cards:
            cards = [x for x in setup_file.cards.itervalues()
                     if x.id in lane.cards]
            references = []
            for card in cards:
                action_id = action_ids[card]
                references.append(properties.ReferenceProperty(
                    'cards', {'action': action_id}))
            props.append(properties.ListProperty('cards', references))

        action_id = action_ids[lane]
        return actions.UpdateAction(
            'update-%s' % action_id, None, action_id, props)

    def _update_user(self, setup_file, action_ids, user):
        props = []
        default_view = [x for x in setup_file.views.itervalues()
                        if x.name == user.default_view][0]
        action_id = action_ids[default_view]
        props.append(properties.ReferenceProperty(
            'default-view', {'action': action_id}))

        action_id = action_ids[user]
        return actions.UpdateAction(
            'update-%s' % action_id, None, action_id, props)

    def _update_card(self, setup_file, action_ids, card):
        props = []

        # add creator reference
        creator = [x for x in setup_file.users.itervalues()
                   if x.name == card.creator][0]
        ref = properties.ReferenceProperty(
            'creator', {'action': action_ids[creator]})
        props.append(ref)

        # add lane reference
        lane = [x for x in setup_file.lanes.itervalues()
                if x.name == card.lane][0]
        ref = properties.ReferenceProperty(
            'lane', {'action': action_ids[lane]})
        props.append(ref)

        # add reason reference
        reason = [x for x in setup_file.reasons.itervalues()
                  if x.short_name == card.reason][0]
        ref = properties.ReferenceProperty(
            'reason', {'action': action_ids[reason]})
        props.append(ref)

        # add milestone reference
        if card.milestone:
            milestone = [x for x in setup_file.milestones.itervalues()
                         if x.short_name == card.milestone][0]
            ref = properties.ReferenceProperty(
                'milestone', {'action': action_ids[milestone]})
            props.append(ref)

        # add assignee references
        if card.assignees:
            references = []
            for name in card.assignees:
                assignee = [x for x in setup_file.users.itervalues()
                            if x.name == name][0]
                action_id = action_ids[assignee]
                references.append(properties.ReferenceProperty(
                    'assignees', {'action': action_id}))
            props.append(properties.ListProperty('assignees', references))

        if card.comments:
            references = []
            for comment_id in card.comments:
                comment = [x for x in setup_file.comments.itervalues()
                           if x.id == comment_id][0]
                action_id = action_ids[comment]
                references.append(properties.ReferenceProperty(
                    'comments', {'action': action_id}))
            props.append(properties.ListProperty('comments', references))

        action_id = action_ids[card]
        return actions.UpdateAction(
            'update-%s' % action_id, None, action_id, props)

    def _update_reason(self, setup_file, action_ids, reason):
        if reason.work_items:
            # TODO:
            #   This is a reference to a remote repository, currently
            #   unsupported by python-consonant.
            pass
        action_id = action_ids[reason]
        return actions.UpdateAction(
            'update-%s' % action_id, None, action_id, [])

    def _update_milestone(self, setup_file, action_ids, milestone):
        props = []

        action_id = action_ids[milestone]
        return actions.UpdateAction(
            'update-%s' % action_id, None, action_id, props)

    def _update_comment(self, setup_file, action_ids, comment):
        props = []

        # add author reference
        author = [x for x in setup_file.users.itervalues()
                  if x.name == comment.author][0]
        ref = properties.ReferenceProperty(
            'author', {'action': action_ids[author]})
        props.append(ref)

        # add attachment reference
        if comment.attachment:
            attachment = [x for x in setup_file.attachments.itervalues()
                          if x.name == comment.attachment][0]
            ref = properties.ReferenceProperty(
                'attachment', {'action': action_ids[attachment]})
            props.append(ref)

        # add card reference
        card = [x for x in setup_file.cards.itervalues()
                if x.id == comment.card][0]
        ref = properties.ReferenceProperty(
            'card', {'action': action_ids[card]})
        props.append(ref)

        action_id = action_ids[comment]
        return actions.UpdateAction(
            'update-%s' % action_id, None, action_id, props)

    def _update_attachment(self, setup_file, action_ids, attachment):
        props = []

        comment = [x for x in setup_file.comments.itervalues()
                   if x.id == attachment.comment][0]
        ref = properties.ReferenceProperty(
            'comment', {'action': action_ids[comment]})
        props.append(ref)

        action_id = action_ids[attachment]
        return actions.UpdateAction(
            'update-%s' % action_id, None, action_id, props)
