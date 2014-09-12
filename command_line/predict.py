#!/usr/bin/env python
#
# dials.predict.py
#
#  Copyright (C) 2013 Diamond Light Source
#
#  Author: James Parkhurst
#
#  This code is distributed under the BSD license, a copy of which is
#  included in the root directory of this package.

from __future__ import division

class Script(object):
  '''A class for running the script.'''

  def __init__(self):
    '''Initialise the script.'''
    from dials.util.options import OptionParser
    from libtbx.phil import parse

    # The script usage
    usage = "usage: %prog [options] [param.phil] "\
            "{sweep.json | image1.file [image2.file ...]}"

    phil_scope = parse('''
      output = predicted.pickle
        .type = str
        .help = "The filename for the predicted reflections"

      force_static = False
        .type = bool
        .help = "For a scan varying model, force static prediction"

      buffer_size = 0
        .type = int
        .help = "Calculate predictions within a buffer zone of n images either"
                "size of the scan"

      dmin = None
        .type = float
        .help = "Minimum d-spacing of predicted reflections"

        include scope dials.algorithms.profile_model.profile_model.phil_scope
    ''', process_includes=True)

    # Create the parser
    self.parser = OptionParser(
      usage=usage,
      phil=phil_scope,
      read_experiments=True)

  def run(self):
    '''Execute the script.'''
    from dials.util.command_line import Command
    from dials.array_family import flex
    from dials.algorithms.profile_model.profile_model import ProfileModelList
    from dials.util.options import flatten_experiments

    # Parse the command line
    params, options = self.parser.parse_args(show_diff_phil=True)

    # Check the number of experiments
    experiments = flatten_experiments(params.input.experiments)
    if len(experiments) == 0:
      self.parser.print_help()
      return

    predicted_all = flex.reflection_table()

    for i_expt, expt in enumerate(experiments):
      if params.buffer_size > 0:
        # Hack to make the predicter predict reflections outside of the range
        # of the scan
        scan = expt.scan
        image_range = scan.get_image_range()
        oscillation = scan.get_oscillation()
        scan.set_image_range((image_range[0]-params.buffer_size,
                              image_range[1]+params.buffer_size))
        scan.set_oscillation((oscillation[0]-params.buffer_size*oscillation[1],
                              oscillation[1]))

      # Populate the reflection table with predictions
      predicted = flex.reflection_table.from_predictions(
        expt,
        force_static=params.force_static,
        dmin=params.dmin)
      predicted['id'] = flex.int(len(predicted), i_expt)
      predicted_all.extend(predicted)
    if len(params.profile) > 0:
      profile_model = ProfileModelList.load(params)
      predicted_all.compute_bbox(experiments, profile_model)

    # Save the reflections to file
    Command.start('Saving {0} reflections to {1}'.format(
        len(predicted_all), params.output))
    predicted_all.as_pickle(params.output)
    Command.end('Saved {0} reflections to {1}'.format(
        len(predicted_all), params.output))


if __name__ == '__main__':
  from dials.util import halraiser
  try:
    script = Script()
    script.run()
  except Exception as e:
    halraiser(e)
