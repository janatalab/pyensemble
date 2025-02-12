# forms.py
from django.conf import settings
import django.forms as forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit

from pyensemble.models import Stimulus, Attribute, StimulusXAttribute

from django.core.files.uploadedfile import InMemoryUploadedFile
import zipfile
import csv 

import io, os

from django.core.files.storage import FileSystemStorage

if settings.USE_AWS_STORAGE:
    from pyensemble.storage_backends import S3MediaStorage


import pdb


class ImportForm(forms.Form):
    file = forms.FileField(label='Select a .csv or .json file to import')

    def __init__(self, *args, **kwargs):
        self.helper = FormHelper()
        self.helper.form_class = 'importform'
        self.helper.form_method = 'post'

        self.helper.add_input(Submit('submit', 'Submit'))
        super(ImportForm, self).__init__(*args, **kwargs)


class ImportStimuliForm(forms.Form):
    file = forms.FileField(label='File:')
    location_root = forms.CharField(label='Directory path to prepend to location (optional)', required=False)

    def __init__(self, *args, **kwargs):
        self.helper = FormHelper()
        self.helper.form_class = 'importform'
        self.helper.form_method = 'post'

        self.allowable_media_extensions = ['.mp3','.wav','.aiff','.m4v','.jpg','.jpeg','.tiff','.gif']

        self.helper.add_input(Submit('submit', 'Submit'))
        super(ImportStimuliForm, self).__init__(*args, **kwargs)

    def parse_header(self, header_row):
        # Strip leading and trailing whitespace from column names
        columns = [c.strip() for c in header_row]

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

        header_info = {
            'columns': columns,
            'cid': cid,
            'valid_columns': valid_columns,
            'attributes': attribute_cols
        }

        return header_info


    def extract_and_save_stimuli(self):
        if settings.USE_AWS_STORAGE:
            storage = S3MediaStorage()
        else:
            storage = FileSystemStorage()

        result = {
            'num_submitted': 0,
            'num_existing': 0,
            'num_written': 0,
            'num_attributes_existing': 0,
            'num_attributes_written': 0,
            'num_uploaded': 0,
            'failed': [],
        }

        file = self.cleaned_data['file']

        # Get our filename and extension
        fstub, fext = os.path.splitext(file.name)

        # Wrap our input stream
        if fext in [".json", ".csv"]:
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
            header_row = next(reader)
            header_info = self.parse_header(header_row)

            cid = header_info['cid']
            valid_columns = header_info['valid_columns']
            attribute_cols = header_info['attributes']
    
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

        elif fext == '.zip':
            # Check if the uploaded file is a valid ZIP file
            if zipfile.is_zipfile(file):
                with zipfile.ZipFile(file, 'r') as zip_ref:
                    # Find the .csv file that contains the stimulus info and compile a list of media files
                    media_files = []
                    csv_file = None
                    for file_info in zip_ref.infolist():
                        if file_info.is_dir():
                            continue

                        elif file_info.filename.startswith('__MACOSX'):
                            continue

                        elif not file_info.filename.endswith('.csv'):
                            # Get our filename and extension
                            fstub, fext = os.path.splitext(file_info.filename)                
                            if fext in self.allowable_media_extensions:
                                media_files.append(file_info.filename)            
                            continue 

                        else:
                            csv_file = file_info.filename

                    # Make sure we found a .csv file
                    if not csv_file:
                        raise forms.ValidationError('The uploaded zip file must contain a .csv file with stimulus information')

                    # Read the csv file
                    csv_file_data = zip_ref.read(csv_file)

                    # Create an InMemoryUploadedFile for saving to the model
                    csv_file_obj = InMemoryUploadedFile(io.BytesIO(csv_file_data), 'file', csv_file, None, len(csv_file_data), None)

                    csv_content = csv_file_obj.read().decode('utf-8')

                    # Read the header information in the csv file
                    with io.StringIO(csv_content) as csv_file:
                        csv_reader = csv.reader(csv_file)
                        header_row = next(csv_reader)
                        header_info = self.parse_header(header_row)

                    # Read the contents of the CSV file, loading it into an array of dicts
                    with io.StringIO(csv_content) as csv_file:
                        # Create a CSV reader
                        csv_reader = csv.DictReader(csv_file)

                        # Convert the CSV data to a list of dictionaries
                        stimulus_data = [row for row in csv_reader]

                    # Now iterate over the stimulus data
                    result['num_submitted'] = len(stimulus_data)

                    for stimulus in stimulus_data:
                        currfile = stimulus['location'].strip()
                        stimname = stimulus['name']

                        # Verify that a file exists
                        found_file = False
                        for file_info in zip_ref.infolist():
                            if file_info.filename.startswith('__MACOSX'):
                                continue 

                            if file_info.filename.endswith(currfile):
                                stimname_in_zip = file_info.filename
                                found_file = True
                                break    

                        if not found_file:
                            result['failed'].append({'name': stimname, 'reason': f"File '{currfile}' not found in zipfile!"})
                            continue

                        # Load our stimulus file
                        stim_file_data = zip_ref.read(stimname_in_zip)

                        # Create an InMemoryUploadedFile for saving to the model
                        stim_file_obj = InMemoryUploadedFile(io.BytesIO(stim_file_data), 'file', currfile, None, len(stim_file_data), None)

                        # Create the data that we're going to write to the db
                        entry = {}
                        for cname in header_info['valid_columns']:
                            entry.update({cname: stimulus[cname].strip()})

                        # Prepend our location_root to our location information
                        entry['location'] = os.path.join(self.cleaned_data['location_root'], currfile) 


                        # Get or create the basic Stimulus object based on the name and location information that constitute the unique key for the stimulus
                        db_entry, created = Stimulus.objects.get_or_create(name=stimname, location=os.path.join(self.cleaned_data['location_root'], currfile))
                        
                        # Update the database entry with other attributes
                        for key, val in entry.items():
                            setattr(db_entry, key, val)

                        # Save the entry
                        db_entry.save()

                        # Copy the stimulus file if necessary    
                        if not db_entry.location.storage.exists(str(db_entry.location)):
                            storage.save(entry['location'], stim_file_obj)
                            result['num_uploaded'] += 1

                        if created:
                            result['num_written'] += 1
                        else:
                            result['num_existing'] += 1

                        # Link any specified attribute info
                        for attribute in header_info['attributes']:
                            attrib_parts = attribute.split('__')

                            # Get our attribute name
                            attrib_name = attrib_parts[1]

                            # Get the attribute entry
                            attrib, _ = Attribute.objects.get_or_create(name=attrib_name)

                            # Get the attribute data value type
                            try:
                                attrib_value_type = attrib_parts[2]
                            except:
                                attrib_value_type = 'text'

                            # Create or get our stimulus x attribute object
                            sxa, created = StimulusXAttribute.objects.get_or_create(
                                stimulus=db_entry, 
                                attribute=attrib, 
                            )

                            # Update the value
                            attribute_value = stimulus[attribute]
                            if attrib_value_type == 'text':
                                sxa.attribute_value_text = attribute_value
                            elif attrib_value_type == 'double':
                                sxa.attribute_value_double = attribute_value

                            # Save the sxa entry with the value
                            sxa.save()

                            if created:
                                result['num_attributes_written'] += 1
                            else:
                                result['num_attributes_existing'] += 1


            else:
                raise forms.ValidationError('The uploaded file is not a valid ZIP file.')


        elif fext in self.allowable_media_extensions:
            # Import and upload a single media file

            # Prepend our location_root to our location information
            location = os.path.join(self.cleaned_data['location_root'], file.name) 

            # Get or create the basic Stimulus object based on the name and location information that constitute the unique key for the stimulus
            db_entry, created = Stimulus.objects.get_or_create(
                name=fstub, 
                location=location
            )
            
            # Save the entry
            db_entry.save()

            # Copy the stimulus file if necessary    
            if not db_entry.location.storage.exists(str(db_entry.location)):
                storage.save(location, file.file)
                result['num_uploaded'] += 1

            if created:
                result['num_written'] += 1
            else:
                result['num_existing'] += 1


        return result