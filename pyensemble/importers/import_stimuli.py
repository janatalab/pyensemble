# import_stimuli.py

# Imports stimuli into the Stimulus table
import os, re

from pyensemble.models import Stimulus
import django.forms as forms

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Field, Submit

from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse

import csv, io

import pdb

# Define our form
class StimulusImportForm(forms.Form):
    file = forms.FileField(label='Select a .csv file to import')

    def __init__(self, *args, **kwargs):
        self.helper = FormHelper()
        self.helper.form_class = 'importform'
        self.helper.form_method = 'post'

        self.helper.add_input(Submit('submit', 'Submit'))
        super(StimulusImportForm, self).__init__(*args, **kwargs)

# Define our view
def import_file(request):
    template = 'pyensemble/importers/import_stimuli.html'

    if request.method == 'POST':
        form = StimulusImportForm(request.POST, request.FILES)

        if form.is_valid():
            content = process_file(request.FILES['file'].file)

            return render(request, 'pyensemble/importers/import_results.html',{'content',content})
    else:
        form = StimulusImportForm()

    context = {'form': form}

    return render(request, template, context)

def process_file(csv_file):
    #
    # This method hasn't been fully implemented yet
    #
    content = None

    csv_file = io.TextIOWrapper(csv_file)  # python 3 only
    dialect = csv.Sniffer().sniff(csv_file.read(1024), delimiters=";,")
    csv_file.seek(0)
    reader = csv.reader(csv_file, dialect)

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

    return content

def import_from_dir(dirname, recursive=True):
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
