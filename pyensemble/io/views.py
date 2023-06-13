import pdb

import time

import pandas as pd

from .parallel import ParallelPort

from .forms import CodeForm, TimingTestForm, PortAddressForm

from django.utils import timezone
from django.shortcuts import render, redirect
from django.http import HttpResponse

PORT = None
DEFAULT_ADDRESS = "0xEFF8"
CLEAR_PINS = 0
PULSE_DURATION_SEC = 0.005

def home(request):
    template = "io/home.html"

    context = {}

    return render(request, template, context)


def _initialize_port(address=DEFAULT_ADDRESS):
    global PORT
    PORT = ParallelPort(address=address)


def test_port_addresses():
    PORT_ADDRESSES = ["0xEFF4", "0xEFF5", "0xEFF6", "0xEFF7", "0xEFF8", "0xEFF9", "0xEFFA", "0xEFFB", "0xEFFC",
                      "0xEFFD", "0xEFFE", "0xEFFF"]

    for address in PORT_ADDRESSES:
        _initialize_port(address=address)

        for pin in range(2,10):
            input("Press Enter to continue...")
            print(f"Testing pin {pin} on port {address} ...")
            PORT.setPin(pin, 1)

            time.sleep(PULSE_DURATION_SEC)

            PORT.setPin(pin, 0)


def send_stimid(request):
    template = "io/send_stimid.html"

    if request.method == 'POST':
        form = CodeForm(request.POST)

        if form.is_valid():
            send_code(form.cleaned_data['stimid'])

    else:
        form = CodeForm()

    context = {
        'form': form,
    }

    return render(request, template, context)


def send_code(request):
    # Get a timestamp for when this request came in
    server_request_received_ms = timezone.now()

    code = int(request.POST['code'])
    client_request_sent_ms = int(request.POST['timestamp'])

    PORT.setData(code)
    set_code_ms = timezone.now()

    # Wait briefly
    time.sleep(PULSE_DURATION_SEC)

    # Turn off the code
    PORT.setData(CLEAR_PINS)
    cleared_code_ms = timezone.now()

    request.session['timing_test'].append({
        'client_request_sent_ms': client_request_sent_ms,
        'server_request_received_ms': server_request_received_ms.timestamp() * 1000,
        'set_code_ms': set_code_ms.timestamp()*1000,
        'cleared_code_ms': cleared_code_ms.timestamp()*1000,
    })

    request.session.modified = True
    return HttpResponse()


def test_timing(request):
    template = "io/get_port_address.html"

    if request.method == 'POST':
        form = PortAddressForm(request.POST)

        if form.is_valid():
            # Set up our parallel port
            address = form.cleaned_data['address']
            _initialize_port(address=address)

            # Clear our session cache
            request.session['timing_test'] = []

            return redirect("pyensemble-io:run-timing-test", permanent=False)

    else:
        form = PortAddressForm(initial={'address': DEFAULT_ADDRESS})

    context = {'form': form}

    return render(request, template, context)


def run_timing_test(request):
    global PORT
    template = "io/timing_test.html"

    # Check whether our PORT is set
    if not PORT:
        return redirect("pyensemble-io:test-timing", permanent=False)

    # Get our form
    form = TimingTestForm()

    context = {'form': form}

    return render(request, template, context)


def end_test(request):
    template = "io/timing_test_results.html"
    tolerance_ms = 100
    context = {}

    # Create a Pandas dataframe from the timing data
    data = pd.DataFrame(request.session['timing_test'])
    context['num_events'] = data.shape[0]

    # Calculate the differences
    diffdata = data.diff()

    context['min'] = diffdata.min().to_dict()
    context['max'] = diffdata.max().to_dict()
    context['median'] = diffdata.median().to_dict()
    context['mean'] = diffdata.mean().to_dict()
    context['std'] = diffdata.std().to_dict()

    # Deal with outliers
    diff_from_median = diffdata - diffdata.median()

    outlier_mask = diff_from_median.abs() > tolerance_ms

    num_outliers = outlier_mask.sum()

    context['num_outliers'] = num_outliers.to_dict()

    diffdata['has_outlier'] = outlier_mask.any(axis=1)

    context['diffdata'] = diffdata

    # Calculate stats using clean data
    cleandata = diffdata[diffdata['has_outlier']==False]

    cleandata = cleandata.drop(['has_outlier'], axis=1)

    context['cleandata'] = cleandata

    context['cleaned'] = {
        'min': cleandata.min().to_dict(),
        'max': cleandata.max().to_dict(),
        'median': cleandata.median().to_dict(),
        'mean': cleandata.mean().to_dict(),
        'std': cleandata.std().to_dict(),
    }

    return render(request, template, context)