# analyis/views.py

import numpy as np
import pandas as pd

from django.contrib.auth.decorators import login_required

from django.http import HttpResponse
from django.shortcuts import render

from pyensemble.models import Session

from bokeh.models import ColumnDataSource, Grid, LinearAxis, DatetimeAxis, Plot, VBar, Dropdown, CustomJS
from bokeh.embed import components

import pdb

def index(request):
    return HttpResponse("Available analyses")

@login_required
def sessions(request,frequency='W'):
    # Get a QuerySet of completed sessions
    # Whether sessions must be completed or only started should be specified by frontend
    sessions = Session.objects.filter(end_datetime__isnull=False)

    # Convert to a Pandas dataframe
    session_df = pd.DataFrame(sessions.values('date_time'))

    # Set index to be the time values
    session_df.set_index('date_time', drop=False, inplace=True)

    # Create the histogram
    # The frequency should be dynamically controlled by frontend
    histdata = session_df.groupby(pd.Grouper(freq=frequency)).count()

    # Rename our column
    histdata.rename(columns={'date_time':'count'}, inplace=True)

    # Create a bokeh object with the histogram
    src = ColumnDataSource(histdata)

    menu = [('Monthly','M'),('Weekly','W'),('Daily','D')]
    dropdown = Dropdown(label="Frequency", menu=menu)
    dropdown.js_on_event("menu_item_click",CustomJS(code="window.open('/analysis/sessions/'+this.item+'/','_self')"))

    label = [x for (x,y) in menu if y==frequency][0]
    plot = Plot(
        title=f'Completed sessions ({label})', plot_width=600, plot_height=300,
        min_border=0, toolbar_location=None)

    glyph = VBar(x="date_time", top="count", bottom=0, width=0.5, fill_color="#b3de69")
    plot.add_glyph(src, glyph)

    xaxis = DatetimeAxis()
    plot.add_layout(xaxis, 'below')

    yaxis = LinearAxis()
    plot.add_layout(yaxis, 'left')

    plot.add_layout(Grid(dimension=0, ticker=xaxis.ticker))
    plot.add_layout(Grid(dimension=1, ticker=yaxis.ticker))

    # Render the div for our object
    script, divs = components({'dropdown':dropdown, 'plot':plot})

    # pdb.set_trace()
    context = {
        'script': script,
    }

    context.update(divs)

    return render(request,'analysis/sessions.html',context)

