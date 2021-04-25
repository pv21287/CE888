from . import app
from flask import render_template
import json, plotly
from wrangling_scripts.wrangle_data import plot_data

@app.route('/')
@app.route('/index/')
def index():

    figures = plot_data()

    # plot ids for the html id tag
    ids = ['figure-{}'.format(i) for i, _ in enumerate(figures)]

    # Convert the plotly figures to JSON for javascript in html template
    figuresJSON = json.dumps(figures, cls=plotly.utils.PlotlyJSONEncoder)

    return render_template('index.html', ids=ids, figuresJSON=figuresJSON)
