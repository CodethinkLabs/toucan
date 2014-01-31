# Copyright (C) 2013-2014 Codethink Limited.
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


"""Command implementations for the Toucan command line interface."""


import cliapp
import consonant
import os
import pygit2
import sys
import subprocess
import tempfile
import time

import toucanlib

from consonant.store import properties
from consonant.transaction import actions, transaction, validation
from consonant.util.phase import Phase
from consonant.util import gitcli


class SetupCommand(object):

    """Command to create a new Toucan board from a setup file."""

    def __init__(self, app, setup_file, target_dir):
        """Initialise a SetupCommand."""
        self.app = app
        self.setup_filename = setup_file
        self.target_dir = target_dir

    def run(self):
        """Perform the board setup."""
        # parse the setup file
        parser = toucanlib.cli.setup.SetupParser()
        setup_file = parser.parse(open(self.setup_filename, 'r'))

        # create the target directory
        try:
            os.makedirs(self.target_dir)
        except OSError, e:
            raise cliapp.AppException(
                'Failed to create the target directory: %s' % e.strerror)

        # initialise the Git repository
        repo = pygit2.init_repository(self.target_dir)

        # perform the actual board setup
        setup = toucanlib.cli.setup.SetupRunner()
        setup.run(repo, setup_file)


class ListCommand(object):

    """Command to list objects in a Toucan board."""

    def __init__(self, app, service_url, patterns):
        """Initialise a ListCommand."""
        self.app = app
        self.service_url = service_url
        self.patterns = patterns

    def run(self):
        """List objects in the Toucan board."""
        # obtain a Consonant service for the service URL
        factory = consonant.service.factories.ServiceFactory()
        service = factory.service(self.service_url)

        # resolve master into its latest commit
        commit = service.ref('master').head

        # resolve input patterns into objects
        resolver = toucanlib.cli.names.NameResolver(service, commit)
        objects = resolver.resolve_patterns(self.patterns, None)

        # render objects to the standard output
        renderer = toucanlib.cli.rendering.ListRenderer(service)
        renderer.render(self.app.output, objects)


class ShowCommand(object):

    """Command to show information about objects in a Toucan board. """

    def __init__(self, app, service_url, patterns):
        """Initialise a ShowCommand."""
        self.app = app
        self.service_url = service_url
        self.patterns = patterns

    def run(self):
        """Show detailed information about objects."""
        # Get a consonant service for the provided URL
        factory = consonant.service.factories.ServiceFactory()
        service = factory.service(self.service_url)

        # Get the latest commit from this service
        commit = service.ref('master').head

        # resolve the input patterns into object
        resolver = toucanlib.cli.names.NameResolver(service, commit)
        objects = resolver.resolve_patterns(self.patterns, None)

        # render the objects to stdout
        renderer = toucanlib.cli.rendering.ShowRenderer(service, commit)
        renderer.render(self.app.output, objects)

        # if there were no objects, inform the user
        if not objects:
            self.app.output.write(
                'No objects found matching %s.\n' % self.patterns)


class AddCommand(object):

    """Command to add an object to a toucan board."""

    def __init__(self, app, service_url, klass):
        """Initialise an AddCommand."""
        self.app = app
        self.service_url = service_url
        self.klass = klass

    def run(self):
        """Add an object to a board."""
        # get a Consonant service
        factory = consonant.service.factories.ServiceFactory()
        service = factory.service(self.service_url)

        # get the latest commit
        commit = service.ref('master').head

        # create a temporary file
        with tempfile.NamedTemporaryFile() as f:
            renderer = toucanlib.cli.rendering.TemplateRenderer(service)
            renderer.render(f, self.klass)
            f.flush()

            # get initial input
            self._run_editor(f.name)

            # create an object loader to parse the input
            loader = toucanlib.cli.loaders.ObjectLoader(
                f.name, service, commit)

            with Phase() as phase:
                if loader.load():
                    created = False
                    while not created:
                        try:
                            loader.create(self.klass, phase)
                            create = True
                            self.app.output.write("Added a %s.\n" % self.klass)
                            return True
                        except Exception, e:
                            self._retry(renderer, f.name, e, loader, phase)
                            if not loader.load():
                                self.app.output.write(
                                    'Cancelled addition of %s.\n' % self.klass)
                                return False
                else:
                    self.app.output.write(
                        'Cancelled addition of %s.\n' % self.klass)
                    return False

    def _retry(self, renderer, name, e, loader, phase):
        self.app.output.write(
            "Error adding %s, please revise input.\n" % self.klass)
        # Re-open the temporary file.
        # This will only work on UNIX systems, and a better
        # solution should be found in future. Without doing
        # this, some editors (gedit) cause no data to be
        # written to the file and no exceptions to be raised.
        with open(name, 'w+') as f:
            for error in phase.errors:
                f.write('# %s:\n#    %s\n' % (error.__class__.__name__, error))
            phase.errors = []
            f.write('#\n')
            try:
                for error in e.errors:
                    f.write('# %s:\n' % error.__class__.__name__)
                    for line in str(error).split(', '):
                        f.write('#    %s\n' % line)
            except Exception, error:
                f.write('# %s: %s\n' % (e.__class__.__name__, e))
            f.write('#\n')
            renderer.render(f, self.klass, loader.data)
            f.flush()
        self._run_editor(name)

    def _run_editor(self, file_path):
        editor = os.environ.get('EDITOR')
        if editor:
            command = editor.split()
            command.append(file_path)
            subprocess.check_call(command)
        else:
            subprocess.check_call(['vi', file_path])


class MoveCommand(object):

    """Command to move a card to a lane in a Toucan board."""

    def __init__(self, app, service_url, card, lane):
        """Initialise a MoveCommand."""
        self.app = app
        self.service_url = service_url
        self.card = card
        self.lane = lane
        self.name_gen = toucanlib.cli.names.NameGenerator()

    def run(self):
        """Move a card to a lane in a board."""
        # get a Consonant service
        factory = consonant.service.factories.ServiceFactory()
        service = factory.service(self.service_url)

        # get the latest commit
        commit = service.ref('master').head

        # get the specified card and lane
        klass = service.klass(commit, 'card')
        cards = [x for x in service.objects(commit, klass)
                 if self.name_gen.presentable_name(x) == self.card]
        if not len(cards):
            self.app.output.write(
                'Did not move card: %s does not exist.' % self.card)
            return False
        klass = service.klass(commit, 'lane')
        lanes = [x for x in service.objects(commit, klass)
                 if self.name_gen.presentable_name(x) == self.lane]
        if not len(lanes):
            self.app.output.write(
                'Did not move card: %s does not exist.' % self.lane)
            return False
        card = cards[0]
        lane = lanes[0]

        # check that the card is not already in the specfied lane
        original_lane = service.resolve_reference(card['lane'])
        if original_lane == lane:
            self.app.output.write(
                'Did not move card: %s is already in %s.' %
                (self.card, self.lane))
            return False
        else:
            self._move_card(service, commit, card, lane, original_lane)

            # confirm card movement
            old_lane_name = self.name_gen.presentable_name(original_lane)
            new_lane_name = self.name_gen.presentable_name(lane)
            card_name = self.name_gen.presentable_name(card)
            self.app.output.write(
                'Moved %s from %s to %s.\n' %
                (card_name, old_lane_name, new_lane_name))
            return True

    def _move_card(self, service, commit, card, lane, original_lane):
        act = []
        begin_action = actions.BeginAction('begin', commit.sha1)
        act.append(begin_action)

        # update lane reference
        ref = properties.ReferenceProperty('lane', {'uuid': lane.uuid})
        props = [ref]
        act.append(actions.UpdateAction(
            'move-%s' % card.uuid, card.uuid, None, props))

        # add card to new lane
        act += self._add_card_to_lane(service, commit, card, lane)

        # remove card from old lane
        act += self._remove_card_from_lane(
            service, commit, card, original_lane)

        # set commit signature
        author = pygit2.Signature(
            gitcli.subcommand(service.repo, ['config', 'user.name']),
            gitcli.subcommand(service.repo, ['config', 'user.email']))

        # make the commit action
        commit_action = actions.CommitAction(
            'commit', 'refs/heads/master',
            '%s <%s>' % (author.name, author.email), time.strftime('%s %z'),
            '%s <%s>' % (author.name, author.email), time.strftime('%s %z'),
            'Move %s from %s to %s' %
            (self.card, self.name_gen.presentable_name(original_lane),
             self.lane))
        act.append(commit_action)

        # apply transaction
        t = transaction.Transaction(act)

        service.apply_transaction(t)

    def _add_card_to_lane(self, service, commit, card, lane):
        act = []
        lane_cards = lane.get('cards', [])
        lane_cards.append(properties.ReferenceProperty(
            'cards', {'uuid': card.uuid}))
        lane_props = [properties.ListProperty('cards', lane_cards)]
        act.append(actions.UpdateAction(
            'update-%s' % lane.uuid, lane.uuid, None, lane_props))

        return act

    def _remove_card_from_lane(self, service, commit, card, lane):
        act = []
        card_refs = lane.get('cards', [])
        lane_cards = [service.resolve_reference(r.value) for r in card_refs]
        new_cards = []
        for c in lane_cards:
            if c.uuid != card.uuid:
                new_cards.append(properties.ReferenceProperty(
                    'cards', {'uuid': c.uuid}))
        lane_props = [properties.ListProperty('cards', new_cards)]
        act.append(actions.UpdateAction(
            'update-%s' % lane.uuid, lane.uuid, None, lane_props))

        return act
