#   Copyright 2013 David Malcolm <dmalcolm@redhat.com>
#   Copyright 2013 Red Hat, Inc.
#
#   This is free software: you can redistribute it and/or modify it
#   under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful, but
#   WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#   General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see
#   <http://www.gnu.org/licenses/>.

# Parser for the .plist files emitted by the clang-static-analyzer,
# when "-plist" is passed as an option to "scan-build" or "clang"

# Developed against output from clang-3.0-14.fc17

import glob
import os
import plistlib
from pprint import pprint
import sys

from firehose.report import Message, Function, Point, \
    File, Location, Generator, Metadata, Analysis, Issue, Sut, Trace, \
    State, Notes

def parse_scandir(resultdir, analyzerversion=None, sut=None):
    """
    Given a path to a directory of scan-build output, parse it and
    yield Analysis instances
    """
    for filename in glob.glob(os.path.join(resultdir, 'report-*.plist')):
        for analysis in parse_plist(filename, analyzerversion, sut):
            yield analysis

def parse_plist(pathOrFile, analyzerversion=None, sut=None, file_=None, stats=None):
    """
    Given a .plist file emitted by clang-static-analyzer (e.g. via
    scan-build), parse it and return an Analysis instance
    """
    plist = plistlib.readPlist(pathOrFile)
    # We now have the .plist file as a hierarchy of dicts, lists, etc

    # Handy debug dump:
    if 0:
        pprint(plist)

    # A list of filenames, apparently referenced by index within
    # diagnostics:
    files = plist['files']

    generator = Generator(name='clang-analyzer',
                          version=analyzerversion)
    metadata = Metadata(generator, sut, file_, stats)
    analysis = Analysis(metadata, [])

    for diagnostic in plist['diagnostics']:
        if 0:
            pprint(diagnostic)

        cwe = None

        # TODO: we're not yet handling the following:
        #   diagnostic['category']
        #   diagnostic['type']

        message = Message(text=diagnostic['description'])

        loc = diagnostic['location']
        location = Location(file=File(givenpath=files[loc.file],
                                      abspath=None),

                            # FIXME: doesn't tell us function name
                            # TODO: can we patch this upstream?
                            function=None,

                            point=Point(int(loc.line),
                                        int(loc.col)))

        notes = None

        trace = make_trace(files, diagnostic['path'])

        issue = Issue(cwe,
                      None, # FIXME: can we get at the test id?
                      location, message, notes, trace)

        analysis.results.append(issue)

    return analysis

def make_trace(files, path):
    """
    Construct a Trace instance from the .plist's 'path' list
    """
    trace = Trace([])
    for node in path:
        # e.g.:
        #  {'extended_message': "Value stored to 'ret' is never read",
        #   'kind': 'event',
        #   'location': {'col': 2, 'file': 0, 'line': 130},
        #   'message': "Value stored to 'ret' is never read",
        #   'ranges': [[{'col': 8, 'file': 0, 'line': 130},
        #               {'col': 29, 'file': 0, 'line': 130}]]}

        # TODO: we're not yet handling the following:
        #   node['extended_message']
        #   node['kind']
        #   node['ranges']

        loc = node['location']
        location = Location(file=File(givenpath=files[loc.file],
                                      abspath=None),

                            # FIXME: doesn't tell us function name
                            # TODO: can we patch this upstream?
                            function=Function(''),

                            point=Point(int(loc.line),
                                        int(loc.col)))

        notes = Notes(node['message'])
        trace.add_state(State(location, notes))
    return trace

analyzerversion = 'clang-3.0-14.fc17.x86_64' # FIXME

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("provide either the path to scan-build results directory, or to that of a .plist file as the only argument")
    else:
        path = sys.argv[1]
        if path.endswith('.plist'):
            analysis = parse_plist(path, analyzerversion)
            print(analysis.to_xml().write(sys.stdout))
            print
        else:
            for result in parse_scandir(path, analyzerversion):
                print(result.to_xml().write(sys.stdout))
                print