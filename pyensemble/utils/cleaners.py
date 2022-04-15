# cleaners.py

from pyensemble.models import Question

import ast

# Convert questions hashes that were stored as byte codes to hex strings
def fix_question_hashes():
    c = 0 # counter

    for q in Question.objects.all():
        # Update our counter
        c += 1

        # Get the question hash
        qhash = q._unique_hash

        # Check for empty string
        if not qhash:
            print(f'Q{c} has no unique_hash!')
            continue

        # Check whether the string begins with a b''
        if not (qhash[0] == "b" and qhash[1]=="'"):
            print(f'Q{c} not a byte-string: {qhash}')
            continue

        # Convert to a byte string
        converted = ast.literal_eval(qhash)

        # Verify we are dealing with bytes
        if not type(converted) == bytes:
            print(f'Q{c} not a byte-string: {qhash}')
            continue

        # Endcode the byte-string as hex
        hexval = converted.hex()
        print(f'Q{c}: {hexval}')

        # Replace the unique hash value
        q._unique_hash = hexval

        # Save the object
        q.save()