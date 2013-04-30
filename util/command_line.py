#
# command_line.py
#
#  Copyright (C) 2013 Diamond Light Source
#
#  Author: James Parkhurst
#
#  This code is distributed under the BSD license, a copy of which is
#  included in the root directory of this package.
from __future__ import division

def parse_range_list_string(string):
    """Parse a string in the following ways:
    string: 1, 2, 3        -> [1, 2, 3]
    string: 1 - 6          -> [1, 2, 3, 4, 5, 6]
    string: 1 - 6, 7, 8, 9 -> [1, 2, 3, 4, 5, 6, 7, 8, 9]
    """
    items = string.split(',')
    for i in range(len(items)):
        items[i] = items[i].split("-")
        if len(items[i]) == 1:
            items[i] = [int(items[i][0])]
        elif len(items[i]) == 2:
            items[i] = range(int(items[i][0]), int(items[i][1]) + 1)
        else:
            raise SyntaxError
    items = [item for sublist in items for item in sublist]
    return set(items)

def interactive_console(namespace):
    """ Enter an interactive console session. """
    try:
        from IPython import embed
        embed(user_ns = namespace)
    except ImportError:
        print "IPython not available"


class ProgressBarTimer:
    """ A simple timer for the progress bar. """

    def __init__(self):
        """ Init the progress bar timer. """
        from time import time
        self._last_time = time()
        self._last_perc = 0
        self._update_period = 0.5
        self._n_seconds_left = -1

    def update(self, percent):
        """ Update the timer. """
        from time import time

        # Get the current time diff between last time
        curr_time = time()
        diff_time = curr_time - self._last_time

        # Only update after certain period or at 100%
        if percent < 0: percent = 0
        if percent > 100: percent = 100
        if diff_time >= self._update_period or percent >= 100:

            # Check the difference in percentage and calculate
            # number of seconds remaining
            diff_perc = percent - self._last_perc
            if (diff_perc == 0):
                self._n_seconds_left = 0
            else:
                self._n_seconds_left = diff_time * (100 - percent) / diff_perc

        # Return number of seconds
        return self._n_seconds_left

class ProgressBar:
    """ A command line progress bar. """

    def __init__(self, title=None, spinner=True, bar=True, estimate_time=True,
                 indent=0, length=80):
        """ Init the progress bar parameters. """

        # Set the parameters
        self._title = title
        self._indent = indent
        self._spinner = spinner
        self._estimate_time = estimate_time
        self._bar = bar
        self._length = length

        self._timer = ProgressBarTimer()
        self._start_time = self._timer._last_time

        # Print 0 percent
        self.update(0)

    def update(self, fpercent):
        """ Update the progress bar with a percentage. """
        import sys
        from math import ceil

        # Get integer percentage
        percent = int(fpercent)
        if percent < 0: percent = 0
        if percent > 100: percent = 100

        # Add a percentage counter
        right_str = ''
        left_str = '\r'
        left_str += ' ' * self._indent

        # Add a title if given
        if self._title:
            left_str += self._title + ': '

        left_str += '{0: >3}%'.format(percent)

        # Add a spinner
        if self._spinner:
            left_str += ' '
            left_str += '[ {0} ]'.format('-\|/'[percent % 4])

        # Add a timer
        if self._estimate_time:
            n_seconds_left = self._timer.update(fpercent)
            if n_seconds_left < 0:
                n_seconds_left = '?'
            else:
                n_seconds_left = int(ceil(n_seconds_left))
            right_str = ' ' + 'est: {0}s'.format(n_seconds_left) + right_str

        # Add a bar
        if self._bar:
            bar_length = self._length - (len(left_str) + len(right_str)) - 5
            n_char = int(percent * bar_length / 100)
            n_space = bar_length - n_char
            left_str += ' '
            left_str += '[ {0}>{1} ]'.format('=' * n_char, ' ' * n_space)

        # Append strings
        progress_str = left_str + right_str

        # Print progress string to stdout
        sys.stdout.write(progress_str)
        sys.stdout.flush()

    def finished(self, string=None):
        """ The progress bar is finished. """
        if string:
            self._title = string
        else:
            string = ''

        ''' Print the 'end of comand' string.'''
        from sys import stdout
        from time import time


        if self._estimate_time:
            # Get the time string
            time_string = '{0:.2f}s'.format(time() - self._start_time)

            # Truncate the string
            max_length = self._length - self._indent - len(time_string) - 1
            string = string[:max_length]

            # Add an indent and a load of dots and then the time string
            dot_length = 1 + max_length - len(string)
            string = (' ' * self._indent) + string
            string = string + '.' * (dot_length)
            string = string + time_string

        else:

            # Truncaet the string
            max_length = self._length - self._indent
            string = string[:max_length]

            # Add a load of dots
            dot_length = max_length - len(string)
            string = (' ' * self._indent) + string
            string = string + '.' * (dot_length)

        # Write the string to stdout
        stdout.write('\r' + string + '\n')
        stdout.flush()

class Command(object):
    '''Class to nicely print out a command with timing info.'''

    # Variables available in class methods
    indent = 0
    max_length = 80
    print_time = True

    @classmethod
    def start(self, string):
        ''' Print the 'start command' string.'''
        from sys import stdout
        from time import time
        #from termcolor import colored

        # Truncate the string to the maximum length
        max_length = self.max_length - self.indent - 3
        string = string[:max_length]
        string = (' ' * self.indent) + string + '...'

        # Write the string to stdout
        stdout.write(string)
        stdout.flush()

        # Get the command start time
        self._start_time = time()

    @classmethod
    def end(self, string):
        ''' Print the 'end of comand' string.'''
        from sys import stdout
        from time import time
        #from termcolor import colored

        # Check if we want to print the time or not
        if self.print_time:

            # Get the time string
            time_string = '{0:.2f}s'.format(time() - self._start_time)

            # Truncate the string
            max_length = self.max_length - self.indent - len(time_string) - 1
            string = string[:max_length]

            # Add an indent and a load of dots and then the time string
            dot_length = 1 + max_length - len(string)
            string = (' ' * self.indent) + string
            string = string + '.' * (dot_length)
            string = string + time_string

        else:

            # Truncaet the string
            max_length = self.max_length - self.indent
            string = string[:max_length]

            # Add a load of dots
            dot_length = max_length - len(string)
            string = (' ' * self.indent) + string
            string = string + '.' * (dot_length)

        # Write the string to stdout
        stdout.write('\r' + string + '\n')
        stdout.flush()


if __name__ == '__main__':
    import time

    p = ProgressBar()

    for j in range(100):
        p.update(j)
        time.sleep(0.05)

    p.finished()

    Command.start("Starting to do a command")
    time.sleep(1)
    Command.end("Ending the command")
