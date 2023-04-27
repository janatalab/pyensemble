# tasks.py

import os, io
import csv, json

from pyensemble.models import Stimulus

import pdb

def clean_string(item):
    return item if item else ''

def clean_boolean(item):
    if item=='T':
        value = True
    elif item=='F':
        value=False
    else:
        value=None
    return value

def process_stimulus_table(file):
    #
    # This method hasn't been fully implemented yet
    #
    result = {}

    # Get our filename and extension
    fstub, fext = os.path.splitext(file.name)

    # Wrap our input stream
    txt_file = io.TextIOWrapper(file.file)


    if fext == ".json":
        # Load in the json data
        data = json.load(txt_file)

        # Try to find the data 
        entries = None
        if isinstance(data, list):
            for d in data:
                if d['type'] == 'table':
                    if 'data' in d.keys():
                        entries = d['data']
                        break

        if entries:
            result = write_entries_to_db(entries)
        

    elif fext == '.csv':
        # Get the CSV dialect
        dialect = csv.Sniffer().sniff(txt_file.read(1024), delimiters=";,")

        # Rewind the file
        txt_file.seek(0)
        reader = csv.reader(txt_file, dialect)

        # Get the column headers
        columns = next(reader)

        # Make sure the column headers in the import file match Stimulus table fields (with the exception of the file_source column which specifies the path to the local file)

        # Get a dictionary of column indexes
        cid = {col:idx for idx, col in enumerate(columns)}

        # Iterate over the rows
        nstim=0
        for row in reader:
            nstim +=1
            name = row[cid['name']]

            print(f"Processing stimulus {nstim}: {name}")

            # Get or create the Stimulus object
            stimulus, created = Stimulus.objects.get_or_create(
                name=row[cid['name']],
                )

            # Deal with copying the file from local storage to destination storage
            # We probably want to update our Stimulus table so that we have not only the destination path, but also a FileField that can automatically handle URL creation 

    return result

# The import_stimuli_from_dir must be called on a server where the stimuli are locally stored.
# This method is not fully implemented
def import_stimuli_from_dir(dirname, recursive=True):
    for d,s,flist in os.walk(dirname):
        print(f'\nIn directory {d}')

        for fname in flist:
            # Skip files beginning with .
            if re.match('^\.',fname):
                continue

            print(f'\t{fname}')

            # Get our filename and the file extension (file type)
            fstub,fext = os.path.splitext(stim.name)

    # pdb.set_trace()



def write_entries_to_db(entries):
    result = {
        'num_submitted': len(entries),
        'num_existing': 0,
        'num_written': 0,
    }

    for entry in entries:
        # Remove our stimulus ID (primary key)
        for key in ["id", "stimulus_id"]:
            entry.pop(key, None)

        stimulus, created = Stimulus.objects.get_or_create(
            name = clean_string(entry['name']),
            artist = clean_string(entry['artist']),
            album = clean_string(entry['album']),
            description = clean_string(entry['description']),
            playlist = clean_string(entry['playlist']),
            genre = clean_string(entry['genre']),
            file_format = clean_string(entry['file_format']),
            size = entry['size'],
            duration = entry['duration'],
            year = entry['year'], 
            compression_bit_rate = entry['compression_bit_rate'],
            sample_rate = entry['sample_rate'],
            sample_size = entry['sample_size'],
            channels = entry['channels'],
            width = entry['width'],
            height = entry['height'],
            location = clean_string(entry['file_format']),
        )

        if created:
            result['num_written'] += 1
        else:
            result['num_existing'] += 1

    return result
