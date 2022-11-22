# cleaners.py

from pyensemble.models import Question, DataFormat

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

# Attach the proper data format (char) to questions that have textarea as their HTML field data
def fix_text_df():
    # Get the char dataformat instance
    char_df = DataFormat.objects.get(df_type='char')

    # Get our questions that have textarea as the html_field_type
    questions = Question.objects.filter(html_field_type='textarea')

    print(f"Modifying data format for {questions.count()} questions")

    for q in questions:
        print(f"Question: {q.text}\nFormat: {q.data_format.df_type}\n")

        # Assign the char data format
        q.data_format = char_df

        # Save
        q.save()