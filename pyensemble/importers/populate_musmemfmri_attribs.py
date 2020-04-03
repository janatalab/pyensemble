# populate_musmemfmri_attribs.py

from pyensemble.models import Attribute, AttributeXAttribute, StimulusXAttribute

# Go through CSV files that have the desired mappings for attributes

with open(fname,'rt', encoding='ISO-8859-1') as f:
    reader = csv.reader(f)

    # Get the column headers
    columns = next(reader)

    # Get a dictionary of column indexes
    cid = {col:idx for idx, col in enumerate(columns)}

    # Iterate over the rows
    for row in reader:
        nattrib +=1
        name = row[cid['name']]

        print(f"Processing stimulus {nattrib}: {name}")

        # Get or create the Genre object
        attrib, created = Attribute.objects.get_or_create(
            name=row[cid['name']],
            )


# Go through CSV files that have the desired mappings for attrib_x_attrib

with open(fname,'rt', encoding='ISO-8859-1') as f:
    reader = csv.reader(f)

    # Get the column headers
    columns = next(reader)

    # Get a dictionary of column indexes
    cid = {col:idx for idx, col in enumerate(columns)}

    # Iterate over the rows
    for row in reader:
        nattrib +=1
        parent = row[cid['parent_id']]

        print(f"Processing stimulus {nattrib}: {name}")

        # Get or create the parent attrib object
        parent_attrib, created = Attribute.objects.get(pk=parent)

        child_attrib, created = Attribute.objects.get(pk=child)

        axa = AttributeXAttribute.objects.get_or_create(attribute_id_child=child, attribute_id_parent=parent, mapping_name='',)

