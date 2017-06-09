import os
from flask import Flask, request, redirect, url_for, flash
from flask import render_template
from werkzeug.utils import secure_filename

from cStringIO import StringIO
import sys

import sbml_diff
from sbml_diff import *

SERVER_DIR = '/code'
# SERVER_DIR = '.'
UPLOAD_FOLDER = SERVER_DIR + '/static/uploads'

ALLOWED_EXTENSIONS = {'sbml', 'xml'}

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.secret_key = 'super secret key'
app.config['SESSION_TYPE'] = 'filesystem'

all_colors = ["#e41a1c","#377eb8","#4daf4a","#984ea3","#ff7f00","#ffff33","#a65628","#f781bf","#999999"]


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS


def to_int(x):
    try:
        return int(x)
    except ValueError:
        return 0


def process_single(models, all_model_names, tmp_path, dir_name, reaction_label, display_stoichiometry, abstract, elided_species,
                   hide_rules, selected_model_num=False, use_sympy=False):

    old_stdout = sys.stdout
    sys.stdout = mystdout = StringIO()

    if selected_model_num is False:
        name = ""
        if abstract:
            output_formatter = sbml_diff.GenerateDot(all_colors, len(models), reaction_label=reaction_label,
                                                     show_stoichiometry=display_stoichiometry,
                                                     model_names=all_model_names)

            sd = sbml_diff.SBMLDiff(models, all_model_names, output_formatter, hide_rules=hide_rules, use_sympy=use_sympy)
            sd.diff_abstract_models(elided_species=elided_species)

        else:
            output_formatter = sbml_diff.GenerateDot(all_colors, len(models), reaction_label=reaction_label,
                                                     show_stoichiometry=display_stoichiometry,
                                                     model_names=all_model_names)
            sd = sbml_diff.SBMLDiff(models, all_model_names, output_formatter, hide_rules=hide_rules, use_sympy=use_sympy)
            sd.diff_models()

    else:
        name = str(selected_model_num) + "-"
        if abstract:
            output_formatter = sbml_diff.GenerateDot(all_colors, len(models), reaction_label=reaction_label,
                                                     selected_model=selected_model_num,
                                                     show_stoichiometry=display_stoichiometry,
                                                     model_names=all_model_names)
            sd = sbml_diff.SBMLDiff(models, all_model_names, output_formatter, hide_rules=hide_rules, use_sympy=use_sympy)
            sd.diff_abstract_models(elided_species=elided_species)

        else:
            output_formatter = sbml_diff.GenerateDot(all_colors, len(models), reaction_label=reaction_label,
                                                     selected_model=selected_model_num,
                                                     show_stoichiometry=display_stoichiometry,
                                                     model_names=all_model_names)
            sd = sbml_diff.SBMLDiff(models, all_model_names, output_formatter, hide_rules=hide_rules, use_sympy=use_sympy)
            sd.diff_models()

    graphviz = mystdout.getvalue()
    sys.stdout = old_stdout

    f = open(os.path.join(tmp_path, name + 'results.dot'), 'w')
    f.write(graphviz)
    f.close()

    # Get png
    from subprocess import call
    pr = ["dot", "-Tpng", "-o", SERVER_DIR + "/static/uploads/" + dir_name + "/" + name + "results.png",
          SERVER_DIR + "/static/uploads/" + dir_name + "/" + name + "results.dot"]
    call(pr)

    # Get pdf
    from subprocess import call
    pr = ["dot", "-Tpdf", "-o", SERVER_DIR + "/static/uploads/" + dir_name + "/" + name + "results.pdf",
          SERVER_DIR + "/static/uploads/" + dir_name + "/" + name + "results.dot"]
    call(pr)


def get_tables(models, file_names, tmp_path):
    old_stdout = sys.stdout

    sys.stdout = mystdout = StringIO()

    output_formatter = sbml_diff.GenerateDot(all_colors, len(models))
    sd = sbml_diff.SBMLDiff(models, file_names, output_formatter)

    sd.print_rate_law_table(output_format="html")
    f = open(os.path.join(tmp_path, 'rates.html'), 'w')
    f.write(mystdout.getvalue())
    f.close()
    mystdout.close()

    sys.stdout = mystdout = StringIO()
    sd.compare_params(output_format="html")
    sys.stdout = old_stdout
    rate_table = mystdout.getvalue()
    f = open(os.path.join(tmp_path, 'params.html'), 'w')
    f.write(rate_table)
    f.close()
    mystdout.close()

    sys.stdout = old_stdout


def process(uploads, tmp_path, dir_name, reaction_label, display_stoichiometry, abstract, elided_species, hide_rules, use_sympy):
    models = []

    for i in range(len(uploads)):
        f = open(os.path.join(tmp_path, uploads[i]), 'r')
        m = f.read()
        models.append(m)

    for i in range(0, len(uploads)):
        process_single(models, uploads, tmp_path, dir_name, reaction_label, display_stoichiometry, abstract, elided_species, hide_rules, i + 1, use_sympy=use_sympy)

    # all-in-one
    process_single(models, uploads, tmp_path, dir_name, reaction_label, display_stoichiometry, abstract, elided_species, hide_rules, use_sympy=use_sympy)

    get_tables(models, uploads, tmp_path)


@app.route('/upload', methods=['GET', 'POST'])
def upload_file():

    if request.method == 'POST':

        # Create a subdirectory in which to save results
        dir_name = str(max(map(lambda x: to_int(x), os.listdir(UPLOAD_FOLDER))) + 1)
        tmp_path = UPLOAD_FOLDER + "/" + dir_name
        os.mkdir(tmp_path)

        uploads = []
        for field_num in range(1,10):

            field_name = "file%s" % field_num
            if field_name not in request.files:
                continue

            f = request.files[field_name]

            if f and allowed_file(f.filename):
                filename = secure_filename(f.filename)
                filename = str(len(
                    uploads) + 1) + "_" + filename  # prefix number to file to record order of files (which affects colors)

                f.save(os.path.join(tmp_path, filename))
                uploads.append(filename)

        if len(uploads) == 0:
            os.rmdir(tmp_path)
            flash('No files uploaded')
            return redirect(request.url)
        else:

            reaction_label = "none"
            if "reaction_labels" in request.form and request.form["reaction_labels"] in ["none", "name", "rate",
                                                                                         "name+rate"]:
                reaction_label = request.form["reaction_labels"]

            use_sympy = False
            print request.form
            if "arrow_method" in request.form.keys() and request.form["arrow_method"] == "symbolic":
                use_sympy = True

            display_stoichiometry = False
            if "stoichiometry" in request.form and request.form["stoichiometry"] == "yes":
                display_stoichiometry = True

            hide_rules = False
            if "hide_rules" in request.form and request.form["hide_rules"] == "yes":
                hide_rules = True

            elided_species = []
            abstract = False
            if "abstract" in request.form and request.form["abstract"] == "yes":
                abstract = True
                if "elided_species" in request.form and request.form["elided_species"]:
                    elided_species = request.form["elided_species"].split(',')

            try:
                process(uploads, tmp_path, dir_name, reaction_label, display_stoichiometry, abstract, elided_species, hide_rules, use_sympy)

                return redirect(url_for('results',
                                        filename=dir_name))
            except RuntimeError, e:
                return render_template('sbml-diff-error.html', err=e.args[0])

    return render_template('upload.html')



@app.route('/results/<filename>')
def results(filename):
    # look up list of files
    path = os.path.join(UPLOAD_FOLDER, filename)
    if not os.path.exists(path):
        return redirect('/upload')

    files = os.listdir(path)
    files = filter(lambda f: ".xml" in f or ".sbml" in f, files)

    colors = all_colors
    if len(files) == 1:
        colors = ["black"]
    return render_template('results.html', filename=filename, files=files, fileNumbers=range(1, len(files) + 1), colors=colors)


# Routes for static pages
@app.route('/')
def page_homepage():
    return redirect('/upload')


@app.route('/sbml-diff')
def page_sbml_diff():
    return render_template('sbml-diff.html')


@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html')

@app.errorhandler(404)
def not_found(e):
    return render_template('404.html')


if __name__ == "__main__":
    app.run()
