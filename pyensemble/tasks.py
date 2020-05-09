# tasks.py
import hashlib

from pyensemble.models import Subject

import pdb

def get_expsess_key(experiment_id):
    return f'experiment_{experiment_id}'

def hash_text(text):
    m = hashlib.md5()
    m.update(text.encode('utf-8'))
    return m.digest()

def fetch_subject_id(subject, scheme='nhdl'):
    subject_id=None
    exists = False
    last = subject['name_last'].lower()
    first = subject['name_first'].lower()
    dob = subject['dob']

    # We have to first create our subject root and then check for existing matches in the database. The reason we have to do it in this order is because of the encryption of the subject table.
    if scheme=='nhdl':
        subject_id_root = '%02d%s%s%02d'%(dob.month, str(last[0]+last[-1:]+first[0]), str(dob.year)[-2:], dob.day)

        # Get a list of all subjects with the same root
        subjects = Subject.objects.filter(subject_id__contains=subject_id_root)

        # Iterate over the existing subjects and see if we have a match
        for currsub in subjects:
            if currsub.name_last.lower() == last and currsub.name_first.lower() == first and currsub.dob == dob:
                return currsub.subject_id, True

        # If we found no match, create a new entry
        subject_id = subject_id_root+str(subjects.count()+1)
        return subject_id, False

    else:
        raise ValueError('unknown subject ID generator')

