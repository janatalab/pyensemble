# tasks.py

import os, io
import csv, json

from django.conf import settings

from pyensemble.models import Stimulus, Attribute, StimulusXAttribute

import pdb

def clean_string(item):
    return item if item else ''

def clean_boolean(item):
    if item == 'T':
        value = True
    elif item == 'F':
        value = False
    else:
        value=None
    return value

def process_stimulus_table(data):
    result = {
        'num_submitted': 0,
        'num_existing': 0,
        'num_written': 0,
        'failed': [],
    }

    file = data['file']

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

        # Get our file reader
        reader = csv.reader(txt_file, dialect)

        # Get the column headers
        columns = next(reader)

        # NOTE: Microsoft Excel might preprend junk to the first column name when saving out to a .csv file, which will prevent the information from the column being written to the stimulus table. If exporting from Excel to a .csv file, open the .csv file in a basic text editor and save it out again to get rid of the hidden characters.

        # Verify that we have location and name columns
        if 'name' not in columns:
            raise ValueError("The .csv file must have a column named 'name'.")

        if 'location' not in columns:
            raise ValueError("The .csv file must have a column named 'location' which contains the name of the actual stimulus file.")

        # Get a dictionary of column indexes
        cid = {col:idx for idx, col in enumerate(columns)}

        # Determine which of the columns correspond to fields in the Stimulus table
        fields = [f.name for f in Stimulus._meta.fields]

        # Get columns that are also fields in the Stimulus table
        valid_columns = list(set(columns) & set(fields))

        # Get any attribute columns
        attribute_cols = []
        for col in columns:
            if col.startswith('attribute'):
                attribute_cols.append(col)

        # Iterate over the rows
        nstim=0
        for row in reader:
            nstim +=1
            name = row[cid['name']]

            print(f"Processing stimulus {nstim}: {name}")

            # Create the data that we're going to write to the db
            entry = {}
            for cname in valid_columns:
                entry.update({cname: row[cid[cname]]})

            # Prepend our location_root to our location information
            entry['location'] = os.path.join(data['location_root'], entry['location'])

            # Get or create the Stimulus object
            stimulus, created = Stimulus.objects.get_or_create(**entry)

            if created:
                result['num_written'] += 1
            else:
                result['num_existing'] += 1

            # Deal with copying the file from local storage to destination storage

            # Link any specified attribute info
            for attribute in attribute_cols:
                attrib_parts = attribute.split('__')

                # Get our attribute nmae
                attrib_name = attrib_parts[1]

                # Get the attribute entry
                attrib, _ = Attribute.objects.get_or_create(name=attrib_name)

                # Get the attribute data value type
                try:
                    attrib_value_type = attrib_parts[2]
                except:
                    attrib_value_type = 'text'

                # Create or get our stimulus x attribute object
                sxa, _ = StimulusXAttribute.objects.get_or_create(
                    stimulus=stimulus, 
                    attribute=attrib, 
                )

                # Update the value
                attribute_value = row[cid[attribute]]
                if attrib_value_type == 'text':
                    sxa.attribute_value_text = attribute_value
                elif attrib_value_type == 'double':
                    sxa.attribute_value_double = attribute_value

                # Save the sxa entry with the value
                sxa.save()

        result['num_submitted'] = nstim

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
        'failed': [],
    }

    for entry in entries:
        # Remove our stimulus ID (primary key)
        for key in ["id", "stimulus_id"]:
            entry.pop(key, None)

        try:
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
                location = clean_string(entry['location']),
            )
        except:
            result['failed'].append(entry)

            if settings.DEBUG:
                pdb.set_trace()


        if created:
            result['num_written'] += 1
        else:
            result['num_existing'] += 1

    return result
