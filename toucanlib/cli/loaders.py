# Copyright (C) 2014 Codethink Limited.
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


"""Load object data from files, validate it and use it in transactions."""

import cliapp
import consonant
import pygit2
import time
import yaml

from consonant.store import properties
from consonant.transaction import actions, transaction
from consonant.util import expressions, gitcli

import toucanlib


class ObjectLoaderError(Exception):

    """Errors that occur when loading object data."""

    pass


class ObjectLoader():

    """Loader for object data."""

    def __init__(self, data_file, service, commit):
        """Initialise an ObjectLoader."""
        self.service = service
        self.commit = commit
        self.name_gen = toucanlib.cli.names.NameGenerator()
        self.resolver = toucanlib.cli.names.NameResolver(
            self.service, self.commit)
        self.data_file = data_file
        self.data = {}

    def load(self):
        """Load data as yaml."""
        try:
            with open(self.data_file, 'r') as stream:
                self.data = yaml.load(stream)
            if self.data:
                return True
            else:
                return False
        except Exception, e:
            with open(self.data_file, 'r') as stream:
                data = stream.read()
            raise cliapp.AppException(
                'Input yaml was not valid yaml: %s' % data)

    def create(self, klass, phase):
        """Create a transaction to add the described object to the store."""
        acts = []

        begin_action = actions.BeginAction('begin', self.commit.sha1)
        acts.append(begin_action)

        # assign action id for object
        action_id = 'add-%s' % klass

        # create object
        creators = {
            'attachment': self._create_attachment,
            'card': self._create_card,
            'comment': self._create_comment,
            'lane': self._create_lane,
            'milestone': self._create_milestone,
            'reason': self._create_reason,
            'user': self._create_user,
            'view': self._create_view
        }

        creator = creators[klass]
        acts.append(creator(action_id))

        # update object
        updaters = {
            'attachment': self._update_attachment,
            'card': self._update_card,
            'comment': self._update_comment,
            'lane': self._update_lane,
            'milestone': self._update_milestone,
            'reason': self._update_reason,
            'user': self._update_user,
            'view': self._update_view
        }

        updater = updaters[klass]
        acts += updater(action_id, phase)

        author = pygit2.Signature(
            gitcli.subcommand(self.service.repo, ['config', 'user.name']),
            gitcli.subcommand(self.service.repo, ['config', 'user.email']))

        # make the commit action
        commit_action = actions.CommitAction(
            'commit', 'refs/heads/master',
            '%s <%s>' % (author.name, author.email), time.strftime('%s %z'),
            '%s <%s>' % (author.name, author.email), time.strftime('%s %z'),
            'Add a %s: %s' % (klass, self.data))
        acts.append(commit_action)

        # apply transaction
        t = transaction.Transaction(acts)

        self.service.apply_transaction(t)

    def _create_view(self, action_id):
        props = []
        if self.data.get('name', ''):
            props.append(properties.TextProperty('name', self.data['name']))
        if self.data.get('description', ''):
            props.append(properties.TextProperty(
                'description', self.data['description']))
        return actions.CreateAction(action_id, 'view', props)

    def _create_lane(self, action_id):
        props = []
        if self.data.get('name', ''):
            props.append(properties.TextProperty('name', self.data['name']))
        if self.data.get('description', ''):
            props.append(properties.TextProperty(
                'description', self.data['description']))
        return actions.CreateAction(action_id, 'lane', props)

    def _create_user(self, action_id):
        props = []
        if self.data.get('name', ''):
            props.append(properties.TextProperty('name', self.data['name']))
        if self.data.get('email', ''):
            props.append(properties.TextProperty('email', self.data['email']))
        if self.data.get('roles', ''):
            props.append(properties.ListProperty(
                'roles', [properties.TextProperty('roles', x)
                          for x in self.data['roles']]))
        return actions.CreateAction(action_id, 'user', props)

    def _create_card(self, action_id):
        props = []
        if self.data.get('title', ''):
            props.append(properties.TextProperty('title', self.data['title']))
        if self.data.get('description', ''):
            props.append(properties.TextProperty(
                'description', self.data['description']))
        return actions.CreateAction(action_id, 'card', props)

    def _create_reason(self, action_id):
        props = []
        if self.data.get('short-name', ''):
            props.append(properties.TextProperty(
                'short-name', self.data['short-name']))
        if self.data.get('name', ''):
            props.append(properties.TextProperty('name', self.data['name']))
        if self.data.get('description', ''):
            props.append(properties.TextProperty(
                'description', self.data['description']))
        return actions.CreateAction(action_id, 'reason', props)

    def _create_milestone(self, action_id):
        props = []
        if self.data.get('short-name', ''):
            props.append(properties.TextProperty(
                'short-name', self.data['short-name']))
        if self.data.get('name', ''):
            props.append(properties.TextProperty('name', self.data['name']))
        if self.data.get('description', ''):
            props.append(properties.TextProperty(
                'description', self.data['description']))
        if self.data.get('deadline'):
            props.append(properties.TimestampProperty(
                'deadline', self.data['deadline']))
        return actions.CreateAction(action_id, 'milestone', props)

    def _create_comment(self, action_id):
        props = []
        if self.data.get('comment', ''):
            props.append(properties.TextProperty(
                'comment', self.data['comment']))
        return actions.CreateAction(action_id, 'comment', props)

    def _create_attachment(self, action_id):
        props = []
        if self.data.get('name', ''):
            props.append(properties.TextProperty('name', self.data['name']))
        return actions.CreateAction(action_id, 'attachment', props)

    def _update_view(self, action_id, phase):
        view = self.data
        acts = []
        props = []
        if view.get('lanes', None) is not None:
            references = []
            try:
                lanes = self.resolver.resolve_patterns(view['lanes'], 'lane')
                for lane in lanes:
                    references.append(properties.ReferenceProperty(
                        'lanes', {'uuid': lane.uuid}))
                    # handle bidirectional reference
                    lane['views'].append(properties.ReferenceProperty(
                        'views', {'action': action_id}))
                    lane_props = [properties.ListProperty(
                        'views', lane['views'])]
                    acts.append(actions.UpdateAction(
                        'update-%s' % lane.uuid, lane.uuid, None, lane_props))
                    props.append(properties.ListProperty('lanes', references))
            except KeyError:
                phase.error(ObjectLoaderError(
                    'The "lanes" property references a non-existent object.'))
            except Exception, e:
                phase.error(e)
        acts.append(actions.UpdateAction(
            'update-%s' % action_id, None, action_id, props))
        return acts

    def _update_lane(self, action_id, phase):
        lane = self.data
        acts = []
        props = []

        if lane.get('views', None) is not None:
            references = []
            try:
                views = self.resolver.resolve_patterns(lane['views'], 'view')
                for view in views:
                    references.append(properties.ReferenceProperty(
                        'views', {'uuid': view.uuid}))
                    # handle bidirectional reference
                    view['lanes'].append(properties.ReferenceProperty(
                        'lanes', {'action': action_id}))
                    view_props = [properties.ListProperty(
                        'lanes', view['lanes'])]
                    acts.append(actions.UpdateAction(
                        'update-%s' % view.uuid, view.uuid, None, view_props))
                props.append(properties.ListProperty('views', references))
            except KeyError:
                phase.error(ObjectLoaderError(
                    'The "views" property references a non-existent object.'))
            except Exception, e:
                phase.error(e)

        if lane.get('cards', None) is not None:
            references = []
            try:
                cards = self.resolver.resolve_patterns(lane['cards'], 'card')
                for card in cards:
                    references.append(properties.ReferenceProperty(
                        'cards', {'uuid': card.uuid}))
                    # handle bidirectional reference
                    card_props = [properties.ReferenceProperty(
                        'lane', {'action': action_id})]
                    acts.append(actions.UpdateAction(
                        'update-%s' % card.uuid, card.uuid, None, card_props))
                props.append(properties.ListProperty('cards', references))
            except KeyError:
                phase.error(ObjectLoaderError(
                    'The "cards" property references a non-existent object.'))
            except Exception, e:
                phase.error(e)
        acts.append(actions.UpdateAction(
            'update-%s' % action_id, None, action_id, props))
        return acts

    def _update_user(self, action_id, phase):
        user = self.data
        acts = []
        props = []

        if user.get('default-view', None) is not None:
            try:
                views = self.resolver.resolve_patterns(
                    user['default-view'], 'view')
                view = views.pop()
                ref = properties.ReferenceProperty(
                    'default-view', {'uuid': view.uuid})
                props.append(ref)
            except KeyError:
                phase.error(ObjectLoaderError(
                    'The "default-view" property references a non-existent '
                    'object.'))
            except Exception, e:
                phase.error(e)

        acts.append(actions.UpdateAction(
            'update-%s' % action_id, None, action_id, props))

        return acts

    def _update_card(self, action_id, phase):
        card = self.data
        acts = []
        props = []

        # add creator reference
        if card.get('creator', None) is not None:
            try:
                creators = self.resolver.resolve_patterns(
                    card['creator'].lower().split(' ')[0], 'user')
                creator = creators.pop()
                ref = properties.ReferenceProperty(
                    'creator', {'uuid': creator.uuid})
                props.append(ref)
            except KeyError:
                phase.error(ObjectLoaderError(
                    'The "creator" property references a non-existent '
                    'object.'))
            except Exception, e:
                phase.error(e)

        # add lane reference
        if card.get('lane', None) is not None:
            try:
                lanes = self.resolver.resolve_patterns(
                    card['lane'].lower(), 'lane')
                lane = lanes.pop()
                ref = properties.ReferenceProperty('lane', {'uuid': lane.uuid})
                # handle bidirectional reference
                lane_cards = lane.get('cards', [])
                lane_cards.append(properties.ReferenceProperty(
                    'cards', {'action': action_id}))
                lane_props = [properties.ListProperty('cards', lane_cards)]
                acts.append(actions.UpdateAction(
                    'update-%s' % lane.uuid, lane.uuid, None, lane_props))
                props.append(ref)
            except KeyError:
                phase.error(ObjectLoaderError(
                    'The "lane" property references a non-existent object.'))
            except Exception, e:
                phase.error(e)

        # add reason reference
        if card.get('reason', None) is not None:
            try:
                reasons = self.resolver.resolve_patterns(
                    card['reason'].lower(), 'reason')
                reason = reasons.pop()
                ref = properties.ReferenceProperty(
                    'reason', {'uuid': reason.uuid})
                props.append(ref)
            except KeyError:
                phase.error(ObjectLoaderError(
                    'The "reason" property references a non-existent object.'))
            except Exception, e:
                phase.error(e)

        # add milestone reference
        if card.get('milestone', None) is not None:
            try:
                milestones = self.resolver.resolve_patterns(
                    card['milestone'].lower(), 'milestone')
                milestone = milestones.pop()
                ref = properties.ReferenceProperty(
                    'milestone', {'uuid': milestone.uuid})
                props.append(ref)
            except KeyError:
                phase.error(ObjectLoaderError(
                    'The "milestone" property references a non-existent '
                    'object.'))
            except Exception, e:
                phase.error(e)

        # add assignee references
        if card.get('assignees', None) is not None:
            references = []
            try:
                assignees = self.resolver.resolve_patterns(
                    card['assignees'], 'user')
                for assignee in assignees:
                    references.append(properties.ReferenceProperty(
                        'assignees', {'uuid': assignee.uuid}))
                props.append(properties.ListProperty('assignees', references))
            except KeyError:
                phase.error(ObjectLoaderError(
                    'The "assignees" property references a non-existent '
                    'object.'))
            except Exception, e:
                phase.error(e)

        acts.append(actions.UpdateAction(
            'update-%s' % action_id, None, action_id, props))

        return acts

    def _update_reason(self, action_id, phase):
        # TODO:
        #   This is a reference to a remote repository, currently
        #   unsupported by python-consonant.
        return [actions.UpdateAction(
            'update-%s' % action_id, None, action_id, [])]

    def _update_milestone(self, action_id, phase):
        return [actions.UpdateAction(
            'update-%s' % action_id, None, action_id, [])]

    def _update_comment(self, action_id, phase):
        comment = self.data
        acts = []
        props = []

        # add author reference
        if comment.get('author', None) is not None:
            try:
                authors = self.resolver.resolve_patterns(
                    comment['author'].lower().split(' ')[0], 'user')
                author = authors.pop()
                ref = properties.ReferenceProperty(
                    'author', {'uuid': author.uuid})
                props.append(ref)
            except KeyError:
                phase.error(ObjectLoaderError(
                    'The "author" property references a non-existent object.'))
            except Exception, e:
                phase.error(e)

        # add card reference
        if comment.get('card', None) is not None:
            try:
                cards = self.resolver.resolve_patterns(comment['card'], 'card')
                card = cards.pop()
                ref = properties.ReferenceProperty('card', {'uuid': card.uuid})
                # handle bidirectional reference
                card_comments = card.get('comments', [])
                card_comments.append(properties.ReferenceProperty(
                    'comments', {'action': action_id}))
                card_props = [properties.ListProperty(
                    'comments', card_comments)]
                acts.append(actions.UpdateAction(
                    'update-%s' % card.uuid, card.uuid, None, card_props))

                props.append(ref)
                acts.append(actions.UpdateAction(
                    'update-%s' % action_id, None, action_id, props))
            except KeyError:
                phase.error(ObjectLoaderError(
                    'The "card" property references a non-existent object.'))
            except Exception, e:
                phase.error(e)

        return acts

    def _update_attachment(self, action_id, phase):
        attachment = self.data
        acts = []
        props = []

        # add comment reference
        if attachment.get('comment', None) is not None:
            try:
                comments = self.resolver.resolve_patterns(
                    attachment['comment'], 'comment')
                comment = comments.pop()
                ref = properties.ReferenceProperty(
                    'comment', {'uuid': comment.uuid})
                # handle bidirectional reference
                comment_attach = properties.ReferenceProperty(
                    'attachment', {'action': action_id})
                comment_props = [comment_attach]
                acts.append(actions.UpdateAction(
                    'update-%s' % comment.uuid,
                    comment.uuid,
                    None,
                    comment_props))
                props.append(ref)
            except KeyError:
                phase.error(ObjectLoaderError(
                    'The "comment" property references a non-existent '
                    'object.'))
            except Exception, e:
                phase.error(e)
        acts.append(actions.UpdateAction(
            'update-%s' % action_id, None, action_id, props))

        return acts
