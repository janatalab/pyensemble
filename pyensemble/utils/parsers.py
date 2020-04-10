# parsers.py
import re

def parse_function_spec(function_str):
    # Extracts the function/module name and list of arguments that are passed to that function.
    # Works on either MATLAB or Python style function specifications

    # Parse into a dictionary containing the function name and the parameters
    m = re.match('^(?P<func_name>[\w\.]*)\((?P<params>.*)\)$', function_str)
    specdict = m.groupdict()

    # Detect whether we are dealing with a MATLAB or Python style function 
    # If the params string contains equals signs or if the first parameter is 'request', then we are definitely dealing with Python. Otherwise assume we are dealing with MATLAB, though that need not be strictly be true
    if re.search('=',specdict['params']) or re.match('^request',specdict['params']):
        language = 'python'
    else:
        language = 'matlab'
    specdict['language'] = language

    # Further process the parameters to convert into args and kwargs
    params = specdict['params']

    params_array = params.split(',')

    args=[]
    kwargs={}

    for param in params_array:
        keyval = re.match('^(?P<key>\w*)=(?P<val>\w*)',param)

        if keyval:
            kwargs.update({keyval.groupdict()['key']:keyval.groupdict()['val']})
        else:
            args.append(param)


    specdict.update({'args':args,'kwargs':kwargs})
    return specdict