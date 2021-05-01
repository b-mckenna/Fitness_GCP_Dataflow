'''reference the following code 
 https://github.com/GoogleCloudPlatform/DataflowSDK-examples/blob/1e098181a3b99fe8581ee924056d4de2062113b6/python/dataflow_examples/wordcount_minimal.py#L53
 '''

 from __future__ import absolute_import

 import argparse
 import logging
 import re

import apache_beam as beam
from apache_beam.io import ReadFromText
from apache_beam.io import WriteToText
from apache_beam.options.pipeline_options import PipelineOptions
from apache_beam.options.pipeline_options import SetupOptions
from beam_utils.sources import CsvFileSource

def run(argv=None):
	#part 1: define and run the pipeline
	parser = argparse.ArgumentParser()
	parser.add_argument('--input',
		dest='input',
		default='gs://df-codelabs-tutorial/export.csv',
		help='Input file to process')
	parser.add_argument('--output',
		default='gs://df-codelabs-tutorial/output.txt',
		help='Output file to write results to.')
	known_args, pipeline_args = parser.parse_known_args(argv)
	pipeline_args.extend([
		'--runner=DataflowRunner'
		'--project=gcp-project-final',
		'--staging_location=gs://df-codelabs-tutorial/staging',
		'--temp_location=gs://df-codelabs-tutorial/temp',
		'--job_name=fitflowexample'])

	#part 2: create the pipeline

pipeline_options = PipelineOptions(pipeline_args)
pipeline_options.view_as(SetupOptions).save_main_session = True
p = beam.Pipeline(options=pipeline_options)

# write your transformation here
lines = p | 'read' >> ReadFromText(known_args.input)
headers = lines[0]
output = headers | 'format' >> beam.

# lines = p | 'read' >> ReadFromText(known_args.input)
# format the data into a PCollection of strings
# write to text output

p.run().wait_until_finish()

if __name__ == '__main__':
	logging.getLogger().setLevel(logging.INFO)
	run()

