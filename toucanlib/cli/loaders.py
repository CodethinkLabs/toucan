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

import consonant
import pygit2
import time
import yaml

from consonant.store import properties
from consonant.transaction import actions, transaction
from consonant.util import expressions, gitcli
from consonant.util.phase import Phase

import toucanlib


class ObjectLoaderError(Exception):

    """Errors that occur when loading object data."""

    pass


class ObjectLoader():

    """Loader for object data."""

    def __init__(self, data_file, service, commit):
        self.service = service
        self.commit = commit
        self.name_gen = toucanlib.cli.names.NameGenerator()
        self.data_file = data_file
        self.data = {}

    def load(self, phase):
        """Load data as yaml."""

        try:
            stream = open(self.data_file, 'r')
            self.data = yaml.load(stream)
            stream.close()
        except Exception, e:
            phase.error(e)

    def create(self, klass, phase):
        """Create a transaction to add the described object to the store."""

        act = []

        begin_action = actions.BeginAction('begin', self.commit.sha1)
        act.append(begin_action)

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
        act.append(creator(action_id))

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
        act += updater(action_id)

        author = pygit2.Signature(
            gitcli.subcommand(self.service.repo, ['config', 'user.name']),
            gitcli.subcommand(self.service.repo, ['config', 'user.email']))

        # make the commit action
        commit_action = actions.CommitAction(
            'commit', 'refs/heads/master',
            '%s <%s>' % (author.name, author.email), time.strftime('%s %z'),
            '%s <%s>' % (author.name, author.email), time.strftime('%s %z'),
            'Add a %s: %s' % (klass, self.data))
        act.append(commit_action)

        # apply transaction
        t = transaction.Transaction(act)

        self.service.apply_transaction(t)

    def _create_view(self, action_id):
        props = []
        props.append(properties.TextProperty('name', self.data['name']))
        if self.data.get('description', ''):
            props.append(properties.TextProperty(
                'description', self.data['description']))
        return actions.CreateAction(action_id, 'view', props)

    def _create_lane(self, action_id):
        props = []
        props.append(properties.TextProperty('name', self.data['name']))
        if self.data.get('description', ''):
            props.append(properties.TextProperty(
                'description', self.data['description']))
        return actions.CreateAction(action_id, 'lane', props)

    def _create_user(self, action_id):
        props = []
        props.append(properties.TextProperty('name', self.data['name']))
        props.append(properties.TextProperty('email', self.data['email']))
        props.append(properties.ListProperty(
            'roles', [properties.TextProperty('roles', x)
                      for x in self.data['roles']]))
        return actions.CreateAction(action_id, 'user', props)

    def _create_card(self, action_id):
        props = []
        props.append(properties.TextProperty('title', self.data['title']))
        if self.data.get('description', ''):
            props.append(properties.TextProperty(
                    'description', self.data['description']))
        return actions.CreateAction(action_id, 'card', props)

    def _create_reason(self, action_id):
        props = []
        props.append(properties.TextProperty(
                'short-name', self.data['short-name']))
        props.append(properties.TextProperty('name', self.data['name']))
        if self.data.get('description', ''):
            props.append(properties.TextProperty(
                    'description', self.data['description']))
        return actions.CreateAction(action_id, 'reason', props)

    def _create_milestone(self, action_id):
        props = []
        props.append(properties.TextProperty(
            'short-name', self.data['short-name']))
        props.append(properties.TextProperty('name', self.data['name']))
        if self.data.get('description', ''):
            props.append(properties.TextProperty(
                'description', self.data['description']))
        props.append(properties.TimestampProperty(
            'deadline', self.data['deadline']))
        return actions.CreateAction(action_id, 'milestone', props)

    def _create_comment(self, action_id):
        props = []
        props.append(properties.TextProperty('comment', self.data['comment']))
        return actions.CreateAction(action_id, 'comment', props)

    def _create_attachment(self, action_id):
        props = []
        props.append(properties.TextProperty('name', self.data['name']))
        return actions.CreateAction(action_id, 'attachment', props)

    def _update_view(self, action_id):
        view = self.data
        acts = []
        references = []
        lane_class = consonant.store.objects.ObjectClass('lane', [])
        lanes = self.service.objects(self.commit, lane_class)
        for name in view['lanes']:
            lane = [x for x in lanes if x['name'] == name
                    or name in self.name_gen.long_names(x)][0]
            uuid = lane.uuid
            references.append(properties.ReferenceProperty(
                'lanes', {'uuid': uuid}))
            # handle bidirectional reference
            lane_views = lane['views']
            lane_views.append(properties.ReferenceProperty(
                'views', {'action': action_id}))
            lane_props = [properties.ListProperty('views', lane_views)]
            acts.append(actions.UpdateAction(
                'update-%s' % uuid, uuid, None, lane_props))

        props = [properties.ListProperty('lanes', references)]
        acts.append(actions.UpdateAction(
            'update-%s' % action_id, None, action_id, props))
        return acts

    def _update_lane(self, action_id):
        lane = self.data
        acts = []
        props = []
        view_class = consonant.store.objects.ObjectClass('view', [])
        views = [x for x in self.service.objects(self.commit, view_class)
                 if x['name'] and x['name'] in lane['views']]

        references = []
        for view in views:
            references.append(properties.ReferenceProperty(
                'views', {'uuid': view.uuid}))
            # handle bidirectional reference
            view_lanes = view.properties['lanes'].value
            view_lanes.append(properties.ReferenceProperty(
                'lanes', {'action': action_id}))
            view_props = [properties.ListProperty('lanes', view_lanes)]
            acts.append(actions.UpdateAction(
                'update-%s' % view.uuid, view.uuid, None, view_props))

        props.append(properties.ListProperty('views', references))
        if lane.get('cards', []):
            card_class = consonant.store.objects.ObjectClass('card', [])
            cards = [x for x in self.service.objects(self.commit, card_class)
                     if lane['name'] == x['lane']
                     or lane['name'] in self.name_gen.long_names(x)]

            references = []
            for card in cards:
                uuid = card.uuid
                references.append(properties.ReferenceProperty(
                    'cards', uuid))
                # handle bidirectional reference
                card_lane = card.properties['lane'].value
                card_props = [properties.ReferenceProperty(
                    'lane', {'action': action_id})]
                acts.append(actions.UpdateAction(
                    'update-%s' % uuid, uuid, None, card_props))

            props.append(properties.ListProperty('cards', references))

        acts.append(actions.UpdateAction(
            'update-%s' % action_id, None, action_id, props))
        return acts

    def _update_user(self, action_id):
        return [actions.UpdateAction(
            'update-%s' % action_id, None, action_id, [])]

    def _update_card(self, action_id):
        card = self.data
        acts = []
        props = []

        # add creator reference
        creator_class = consonant.store.objects.ObjectClass('user', [])
        creator = [x for x in self.service.objects(self.commit, creator_class)
                   if x['name'] == card['creator']
                   or card['creator'] in self.name_gen.long_names(x)][0]
        ref = properties.ReferenceProperty('creator', {'uuid': creator.uuid})
        props.append(ref)

        # add lane reference
        lane_class = consonant.store.objects.ObjectClass('lane', [])
        lane = [x for x in self.service.objects(self.commit, lane_class)
                if x['name'] == card['lane']
                or card['lane'] in self.name_gen.long_names(x)][0]
        ref = properties.ReferenceProperty('lane', {'uuid': lane.uuid})
        props.append(ref)
        # handle bidirectional reference
        lane_cards = lane.get('cards', [])
        lane_cards.append(properties.ReferenceProperty(
            'cards', {'action': action_id}))
        lane_props = [properties.ListProperty('cards', lane_cards)]
        acts.append(actions.UpdateAction(
            'update-%s' % lane.uuid, lane.uuid, None, lane_props))

        # add reason reference
        reason_class = consonant.store.objects.ObjectClass('reason', [])
        reasons = [x for x in self.service.objects(self.commit, reason_class)
                  if x['short-name'] == card['reason']
                  or card['reason'] in self.name_gen.long_names(x)]
        reason = reasons[0]
        ref = properties.ReferenceProperty('reason', {'uuid': reason.uuid})
        props.append(ref)

        # add milestone reference
        if card.get('milestone', ''):
            m = consonant.store.objects.ObjectClass('milestone', [])
            milestones = self.service.objects(self.commit, m)
            milestone = [x for x in milestones
                         if x['short-name'] == card['milestone']
                         or card['milestone']
                         in self.name_gen.long_names(x)][0]
            ref = properties.ReferenceProperty(
                'milestone', {'uuid': milestone.uuid})
            props.append(ref)

        # add assignee references
        if card.get('assignees', []):
            references = []
            for name in card['assignees']:
                u = consonant.store.objects.ObjectClass('user', [])
                assignee = [x for x in self.service.objects(self.commit, u)
                            if x['name'] == name
                            or name in self.name_gen.long_names(x)][0]
                references.append(properties.ReferenceProperty(
                    'assignees', {'uuid': assignee.uuid}))
            props.append(properties.ListProperty('assignees', references))

        acts.append(actions.UpdateAction(
            'update-%s' % action_id, None, action_id, props))

        return acts

    def _update_reason(self, action_id):
        # TODO:
        #   This is a reference to a remote repository, currently
        #   unsupported by python-consonant.
        pass
        return [actions.UpdateAction(
            'update-%s' % action_id, None, action_id, [])]

    def _update_milestone(self, action_id):
        acts = []
        props = []
        acts.append(actions.UpdateAction(
            'update-%s' % action_id, None, action_id, props))

        return acts

    def _update_comment(self, action_id):
        comment = self.data
        acts = []
        props = []

        # add author reference
        user_class = consonant.store.objects.ObjectClass('user', [])
        author = [x for x in self.service.objects(self.commit, user_class)
                  if x['name'] == comment['author']
                  or comment['author'] in self.name_gen.long_names(x)][0]
        ref = properties.ReferenceProperty('author', {'uuid': author.uuid})
        props.append(ref)

        # add card reference
        card_class = consonant.store.objects.ObjectClass('card', [])
        card = [x for x in self.service.objects(self.commit, card_class)
                if self.name_gen.card_id(x) == comment['card']
                or comment['card'] in self.name_gen.long_names(x)][0]
        ref = properties.ReferenceProperty('card', {'uuid': card.uuid})
        props.append(ref)
        # handle bidirectional reference
        card_comments = card.properties.get('comments', [])
        card_comments.append(properties.ReferenceProperty(
                'comments', {'action': action_id}))
        card_props = [properties.ListProperty('comments', card_comments)]
        acts.append(actions.UpdateAction(
            'update-%s' % card.uuid, card.uuid, None, card_props))

        acts.append(actions.UpdateAction(
            'update-%s' % action_id, None, action_id, props))

        return acts

    def _update_attachment(self, action_id):
        attachment = self.data
        acts = []
        props = []

        # add comment reference
        comment_class = consonant.store.objects.ObjectClass('comment', [])
        comment = [x for x in self.service.objects(self.commit, comment_class)
                   if self.name_gen.comment_id(x) == attachment['comment']
                   or attachment['comment']
                   in self.name_gen.long_names(x)][0]
        ref = properties.ReferenceProperty('comment', {'uuid': comment.uuid})
        props.append(ref)
        # handle bidirectional reference
        comment_attach = properties.ReferenceProperty(
            'attachment', {'action': action_id})
        comment_props = [comment_attach]
        acts.append(actions.UpdateAction(
            'update-%s' % comment.uuid, comment.uuid, None, comment_props))

        acts.append(actions.UpdateAction(
            'update-%s' % action_id, None, action_id, props))

        return acts

    def validate(self, klass, phase):
        """Validate the input data as if it is a <klass>.

        Returns a boolean indicating success or failure.

        """

        validator = {
            'attachment': self._validate_attachment,
            'card': self._validate_card,
            'comment': self._validate_comment,
            'lane': self._validate_lane,
            'milestone': self._validate_milestone,
            'reason': self._validate_reason,
            'user': self._validate_user,
            'view': self._validate_view
        }[klass]

        return validator(phase)

    def _validate_attachment(self, phase):
        """Validate the input as an attachment.

        Returns a boolean indicating success or failure.

        """

        attachment = self.data

        if not isinstance(attachment, dict):
            phase.error(ObjectLoaderError(
                'Input file defines a non-dict attachment: %s'
                % attachment))
            return False
        else:
            # validate name
            if not 'name' in attachment:
                phase.error(ObjectLoaderError(
                    'Input file defines an attachment without a name: '
                    '%s' % attachment))
                return False
            elif not isinstance(attachment['name'], basestring):
                phase.error(ObjectLoaderError(
                    'Input file defines an attachment with non-string '
                    'name: %s' % attachment['name']))
                return False

            # validate comment
            if not 'comment' in attachment:
                phase.error(ObjectLoaderError(
                    'Input file defines an attachment with no comment: '
                    '%s' % attachment))
                return False
            elif not isinstance(attachment['comment'], int):
                phase.error(ObjectLoaderError(
                    'Input file defines an attachment with non-int '
                    'comment reference: %s' % attachment['comment']))
                return False
            else:
                c = consonant.store.objects.ObjectClass('comment', [])
                comments = self.service.objects(self.commit, c)
                n = self.name_gen
                matches = [x for x in comments
                           if n.comment_id(x) == attachment['comment']
                           or attachment['comment'] in n.long_names(x)]
                if not matches:
                    phase.error(ObjectLoaderError(
                        'Input file defines an attachment with '
                        'non-existant comment reference: %s' % comment))
                    return False
        return True

    def _validate_card(self, phase):
        """Validate the input as a card.

        Returns a boolean indicating success or failure.

        """

        card = self.data

        if not isinstance(card, dict):
            phase.error(ObjectLoaderError(
                'Input file defines a non-dict card: %s' % card))
            return False
        else:
            title = self._validate_card_title(phase, card)
            creator = self._validate_card_creator(phase, card)
            description = self._validate_card_description(phase, card)
            lane = self._validate_card_lane(phase, card)
            milestone = self._validate_card_milestone(phase, card)
            reason = self._validate_card_reason(phase, card)
            assignees = self._validate_card_assignees(phase, card)
            result = title and creator and description and lane and \
                milestone and reason and assignees
        return result

    def _validate_card_title(self, phase, card):
        # validate card title
        if not 'title' in card:
            phase.error(ObjectLoaderError(
                'Input file defines a card without a title: %s' % card))
            return False
        elif not isinstance(card['title'], basestring):
            phase.error(ObjectLoaderError(
                'Input file defines a card with non-string '
                'title: %s' % card['title']))
            return False
        return True

    def _validate_card_creator(self, phase, card):
        # validate card creator
        if not 'creator' in card:
            phase.error(ObjectLoaderError(
                'Input file defines a card without a creator: %s' % card))
            return False
        elif not isinstance(card['creator'], basestring):
            phase.error(ObjectLoaderError(
                'Input file defines a card with non-string '
                'creator: %s' % card['creator']))
            return False
        else:
            user_class = consonant.store.objects.ObjectClass('user', [])
            users = self.service.objects(self.commit, user_class)
            matches = [x for x in users if x['name'] == card['creator']
                       or card['creator'] in self.name_gen.long_names(x)]
            if not matches:
                phase.error(ObjectLoaderError(
                    'Input file defines a card that refers to a '
                    'non-existent user: %s' % card))
                return False
        return True

    def _validate_card_description(self, phase, card):
        # validate card description
        if 'description' in card and \
            not isinstance(card['description'], basestring):
            phase.error(ObjectLoaderError(
                'Input file defines a card with non-string '
                'description: %s' % card['description']))
            return False
        return True

    def _validate_card_lane(self, phase, card):
        # validate card lane
        if not 'lane' in card:
            phase.error(ObjectLoaderError(
                'Input file defines a card without a lane: %s' % card))
            return False
        elif not isinstance(card['lane'], basestring):
            phase.error(ObjectLoaderError(
                'Input file defines a card with non-string '
                'lane: %s' % card['lane']))
            return False
        else:
            lane_class = consonant.store.objects.ObjectClass('lane', [])
            lanes = self.service.objects(self.commit, lane_class)
            matches = [x for x in lanes if x['name'] == card['lane']
                       or card['lane'] in self.name_gen.long_names(x)]
            if not matches:
                phase.error(ObjectLoaderError(
                    'Input file defines a card that refers to a '
                    'non-existent lane: %s' % card))
                return False
        return True

    def _validate_card_milestone(self, phase, card):
        # validate card milestone
        if 'milestone' in card:
            if not isinstance(card['milestone'], basestring):
                phase.error(ObjectLoaderError(
                    'Input file defines a card with non-string '
                    'milestone reference: %s' % card['milestone']))
                return False
            else:
                m = consonant.store.objects.ObjectClass('milestone', [])
                milestones = self.service.objects(self.commit, m)
                matches = [x for x in milestones
                           if card['milestone']
                           in self.name_gen.long_names(x)]
                if not matches:
                    phase.error(ObjectLoaderError(
                        'Input file defines a card that refers to a '
                        'non-existent milestone: %s' % card))
                    return False
        return True

    def _validate_card_reason(self, phase, card):
        # validate card reason
        if not 'reason' in card:
            phase.error(ObjectLoaderError(
                'Input file defines a card without a reason: %s' % card))
            return False
        elif not isinstance(card['reason'], basestring):
            phase.error(ObjectLoaderError(
                'Input file defines a card with non-string '
                'reason reference: %s' % card['reason']))
            return False
        else:
            reason_class = consonant.store.objects.ObjectClass('reason', [])
            reasons = self.service.objects(self.commit, reason_class)
            matches = [x for x in reasons if x['short-name'] == card['reason']
                       or card['reason'] in self.name_gen.long_names(x)]
            if not matches:
                phase.error(ObjectLoaderError(
                    'Input file defines a card that refers to a '
                    'non-existent reason: %s' % card))
                return False
        return True

    def _validate_card_assignees(self, phase, card):
        # validate card assignees
        if 'assignees' in card:
            if not isinstance(card['assignees'], list):
                phase.error(ObjectLoaderError(
                    'Input file defines a card with non-list '
                    'assignees: %s' % card))
                return False
            else:
                for assignee in card['assignees']:
                    if not isinstance(assignee, basestring):
                        phase.error(ObjectLoaderError(
                            'Input file defines a card with '
                            'non-string assignee: %s' % card))
                        return False
                    else:
                        u = consonant.store.objects.ObjectClass('user', [])
                        users = self.service.objects(self.commit, u)
                        matches = [x for x in users if x['name'] == assignee
                                   or assignee in self.name_gen.long_names(x)]
                        if not matches:
                            phase.error(ObjectLoaderError(
                                'Input file defines a card that refers to a '
                                'non-existent user: %s' % card))
                            return False
        return True

    def _validate_comment(self, phase):
        """Validate the input as a comment.

        Returns a boolean indicating success or failure.

        """

        comment = self.data

        if not isinstance(comment, dict):
            phase.error(ObjectLoaderError(
                'Input file defines a non-dict comment: %s' % comment))
            return False
        else:
            # validate comment
            if not 'comment' in comment:
                phase.error(ObjectLoaderError(
                    'Input file defines a comment without a comment: %s' %
                    comment))
                return False
            elif not isinstance(comment['comment'], basestring):
                phase.error(ObjectLoaderError(
                    'Input file defines a comment with non-string '
                    'comment: %s' % comment['comment']))
                return False

            # validate author
            if not 'author' in comment:
                phase.error(ObjectLoaderError(
                    'Input file defines a comment without an author: %s' %
                    comment))
                return False
            elif not isinstance(comment['author'], basestring):
                phase.error(ObjectLoaderError(
                    'Input file defines a comment with non-string '
                    'author reference: %s' % comment['author']))
                return False
            else:
                user_class = consonant.store.objects.ObjectClass('user', [])
                users = self.service.objects(self.commit, user_class)
                matches = [x for x in users if x['name'] == comment['author']
                           or comment['author'] in self.name_gen.long_names(x)]
                if not matches:
                    phase.error(ObjectLoaderError(
                        'Input file defines a comment with a '
                        'non-existant author: %s' % comment))
                    return False

            # validate card
            if not 'card' in comment:
                phase.error(ObjectLoaderError(
                    'Input file defines a comment without a card: %s' %
                    comment))
                return False
            elif not isinstance(comment['card'], basestring):
                phase.error(ObjectLoaderError(
                    'Input file defines a comment with non-string card '
                    'reference: %s' % comment['card']))
                return False
            else:
                card_class = consonant.store.objects.ObjectClass('card', [])
                cards = self.service.objects(self.commit, card_class)
                matches = [x for x in cards
                           if self.name_gen.card_id(x) == comment['card']
                           or comment['card'] in self.name_gen.long_names(x)]
                if not matches:
                    phase.error(ObjectLoaderError(
                        'Input file defines a comment with a '
                        'non-existant card: %s' % comment))
                    return False
        return True

    def _validate_lane(self, phase):
        """Validate the input as a lane.

        Returns a boolean indicating success or failure.

        """

        lane = self.data

        if not isinstance(lane, dict):
            phase.error(ObjectLoaderError(
                'Input file defines a non-dict lane: %s' % lane))
            return False
        else:
            # validate the lane name
            if not 'name' in lane:
                phase.error(ObjectLoaderError(
                    'Input file defines a lane without a name: %s' %
                    lane))
                return False
            elif not isinstance(lane['name'], basestring):
                phase.error(ObjectLoaderError(
                    'Input file defines a non-string lane name: %s' %
                    lane['name']))
                return False

            # validate the lane description
            if 'description' in lane \
                    and not isinstance(
                        lane['description'], basestring):
                phase.error(ObjectLoaderError(
                    'Input file defines a non-string lane '
                    'description: %s' % lane['description']))
                return False

            if 'cards' in lane:
                if not isinstance(lane['cards'], list):
                    phase.error(ObjectLoaderError(
                        'Input file defines a non-list cards entry '
                        'in a lane: %s' % lane['cards']))
                    return False
                else:
                    for card in lane['cards']:
                        if not isinstance(card, int):
                            phase.error(ObjectLoaderError(
                                'Input file defines a non-int card '
                                'reference in a lane: %s' % card))
                            return False
                        card_class = consonant.store.objects.ObjectClass(
                            'card', [])
                        cards = self.service.objects(self.commit, card_class)
                        matches = [x for x in cards
                                   if card in self.name_gen.long_names(x)]
                        if not matches:
                            phase.error(ObjectLoaderError(
                                'Input file defines a lane with a '
                                'non-existant card: %s' % card))
                            return False
        return True

    def _validate_milestone(self, phase):
        """Validate the input as a milestone.

        Returns a boolean indicating success or failure.

        """

        milestone = self.data

        if not isinstance(milestone, dict):
            phase.error(ObjectLoaderError(
                'Input file defines a non-dict milestone: %s' % milestone))
            return False
        else:
            # validate shortname
            if not 'short-name' in milestone:
                phase.error(ObjectLoaderError(
                    'Input file defines a milestone without a short-name'
                    ': %s' % milestone))
                return False
            elif not isinstance(milestone['short-name'], basestring):
                phase.error(ObjectLoaderError(
                    'Input file defines a milestone with non-string '
                    'short-name: %s' % milestone['short-name']))
                return False

            # validate name
            if not 'name' in milestone:
                phase.error(ObjectLoaderError(
                    'Input file defines a milestone without a name: %s' %
                    milestone))
                return False
            elif not isinstance(milestone['name'], basestring):
                phase.error(ObjectLoaderError(
                    'Input file defines a milestone with non-string '
                    'name: %s' % milestone['name']))
                return False

            # validate description
            if 'description' in milestone:
                if not isinstance(milestone['description'], basestring):
                    phase.error(ObjectLoaderError(
                        'Input file defines a milestone with non-string'
                        ' description: %s' % milestone['description']))
                    return False

            # validate deadline
            if not 'deadline' in milestone:
                phase.error(ObjectLoaderError(
                    'Input file defines a milestone without a deadline:'
                    ' %s' % milestone))
                return False
            elif not isinstance(milestone['deadline'], basestring):
                phase.error(ObjectLoaderError(
                    'Input file defines a milestone with non-string '
                    'deadline: %s' % milestone['deadline']))
                return False
        return True

    def _validate_reason(self, phase):
        """Validate the input as a reason.

        Returns a boolean indicating success or failure.

        """

        reason = self.data

        if not isinstance(reason, dict):
            phase.error(ObjectLoaderError(
                'Input file defines a non-dict reason: %s' % reason))
            return False
        else:
            # validate shortname
            if not 'short-name' in reason:
                phase.error(ObjectLoaderError(
                    'Input file defines a reason without a short-name: '
                    '%s' % reason))
                return False
            elif not isinstance(reason['short-name'], basestring):
                phase.error(ObjectLoaderError(
                    'Input file defines a reason with non-string '
                    'short-name: %s' % reason['short-name']))
                return False

            # validate name
            if not 'name' in reason:
                phase.error(ObjectLoaderError(
                    'Input file defines a reason without a name: %s' % reason))
                return False
            elif not isinstance(reason['name'], basestring):
                phase.error(ObjectLoaderError(
                    'Input file defines a reason with non-string '
                    'name: %s' % reason['name']))
                return False

            # validate description
            if 'description' in reason:
                if not isinstance(reason['description'], basestring):
                    phase.error(ObjectLoaderError(
                        'Input file defines a reason with non-string '
                        'description: %s' % reason['description']))
                    return False

            # validate work-items
            # TODO:
            #   These are references to an remote store, which is
            #   currently unsupported by python-consonant.
        return True

    def _validate_user(self, phase):
        """Validate the input as a user.

        Returns a boolean indicating success or failure.

        """

        user = self.data

        if not isinstance(user, dict):
            phase.error(ObjectLoaderError(
                'Input file defines a non-dict user: %s' % user))
            return False
        else:
            # validate user name
            if not 'name' in user:
                phase.error(ObjectLoaderError(
                    'Input file defines a user without a name: %s' % user))
                return False
            elif not isinstance(user['name'], basestring):
                phase.error(ObjectLoaderError(
                    'Input file defines a non-string user name: %s' %
                    user['name']))
                return False

            # validate user email
            if not 'email' in user:
                phase.error(ObjectLoaderError(
                    'Input file defines a user without an email '
                    'address: %s' % (user)))
                return False
            elif not isinstance(user['email'], basestring):
                phase.error(ObjectLoaderError(
                    'Input file defines a non-string user email: %s' %
                    user['email']))
                return False

            # validate user roles
            if not 'roles' in user:
                phase.error(ObjectLoaderError(
                    'Input file defines a user with no roles: %s' %
                    user))
                return False
            elif not isinstance(user['roles'], list):
                phase.error(ObjectLoaderError(
                    'Input file defines a non-list user roles '
                    'entry: %s' % user['roles']))
                return False
            else:
                for role in user['roles']:
                    if not isinstance(role, basestring):
                        phase.error(ObjectLoaderError(
                            'Input file defines a non-string '
                            'user role: %s' % role))
                        return False

            # validate user default-view
            if 'default-view' in user:
                if not isinstance(user['view'], basestring):
                    phase.error(ObjectLoaderError(
                        'Input file defines a user with non-string '
                        'default-view: %s' % card['lane']))
                    return False
                else:
                    v = consonant.store.objects.ObjectClass('view', [])
                    views = self.service.objects(self.commit, v)
                    matches = [x for x in views
                               if x['name'] == user['default-view']
                               or user['view'] in self.name_gen.long_names(x)]
                    if not matches:
                        phase.error(ObjectLoaderError(
                            'Input file defines a user that refers to a '
                            'non-existent default-view: %s' % user))
                        return False

            # validate user avatar
            if 'avatar' in user and not isinstance(user['avatar'], basestring):
                phase.error(ObjectLoaderError(
                    'Input file defines a user with a non-string avatar: %s' %
                    user['avatar']))

        return True

    def _validate_view(self, phase):
        """Validate the input as a view.

        Returns a boolean indicating success or failure.

        """

        view = self.data

        if not isinstance(view, dict):
            phase.error(ObjectLoaderError(
                'Input file defines a non-dict view: %s' % view))
            return False
        else:
            # validate the view name
            if not 'name' in view:
                phase.error(ObjectLoaderError(
                    'Input file defines a view without a name: %s' % view))
                return False
            elif not isinstance(view['name'], basestring):
                phase.error(ObjectLoaderError(
                    'Input file defines a non-string view name: %s' %
                    view['name']))
                return False

            # validate the view description
            if 'description' in view \
                    and not isinstance(
                        view['description'], basestring):
                phase.error(ObjectLoaderError(
                    'Input file defines a non-string view '
                    'description: %s' % view['description']))
                return False

            # validate the lane references in the view
            if not 'lanes' in view:
                phase.error(ObjectLoaderError(
                    'Input file defines a view with no lanes: %s' % view))
                return False
            elif not isinstance(view['lanes'], list):
                phase.error(ObjectLoaderError(
                    'Input file defines a view with a non-list '
                    'lanes entry: %s' % view))
                return False
            else:
                for lane in view['lanes']:
                    if not isinstance(lane, basestring):
                        phase.error(ObjectLoaderError(
                            'Input file defines a view with a '
                            'non-string lane name reference: %s' % lane))
                        return False
                    else:
                        l = consonant.store.objects.ObjectClass('lane', [])
                        lanes = self.service.objects(self.commit, l)
                        matches = [x for x in lanes if x['name'] == lane
                                   or lane in self.name_gen.long_names(x)]
                        if not matches:
                            phase.error(ObjectLoaderError(
                                'Input file defines a view that '
                                'refers to a non-existent lane: %s' % lane))
                            return False
        return True


class Phase():

    """Error tracker for the validator."""

    def error(self, exception):
        """Print the exception raised, and continue execution."""

        print "%s\n" % exception
