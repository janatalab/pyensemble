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
    code = int(request.POST['code'])
    request_sent_ms = int(request.POST['timestamp'])
    request_received_ms = timezone.now()

    PORT.setData(code)
    set_code_ms = timezone.now()

    # Wait briefly
    time.sleep(PULSE_DURATION_SEC)

    # Turn off the code
    PORT.setData(CLEAR_PINS)
    cleared_code_ms = timezone.now()

    request.session['timing_test'].append({
        'request_sent_ms': request_sent_ms,
        'request_received_ms': request_received_ms.timestamp()*1000,
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
    context = {}

    # Create a Pandas dataframe from the timing data
    data = pd.DataFrame(request.session['timing_test'])
    context['num_events'] = data.shape[0]

    # Calculate the differences
    diffdata = data.diff()

    context['min'] = diffdata.max().to_dict()
    context['max'] = diffdata.max().to_dict()
    context['mean'] = diffdata.mean().to_dict()
    context['std'] = diffdata.std().to_dict()

    pdb.set_trace()

    return render(request, template, context)