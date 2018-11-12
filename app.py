from flask import Flask, flash, redirect, request, render_template, session, url_for
from functools import wraps
import json
import jwt
import requests
import settings
import xml.etree.ElementTree as ET

# define our webapp
app = Flask(__name__)

#configuration from settings.py
app.secret_key = settings.SESSION_KEY
app.config['API_HOST'] = settings.API_HOST
app.config['API_KEY'] = settings.API_KEY
app.config['GET_BY_BARCODE'] = settings.GET_BY_BARCODE
app.config['SHARED_SECRET'] = settings.SHARED_SECRET

# login wrapper
def auth_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not 'username' in session:
            abort(403)
        else:
            return f(*args, **kwargs)
    return decorated

# routes and controllers
@app.route('/')
def index():
    return render_template("index.html")

@app.route('/login')
def login():
    if 'username' in session:
        return redirect(url_for('index'))
    else:
        return render_template('login.html')

@app.route('/login/n', methods=['GET'])
def new_login():
    session.clear()
    if 'wrt' in request.cookies:
        encoded_token =  request.cookies['wrt']
        user_data = jwt.decode(encoded_token, app.config['SHARED_SECRET'], algorithms=['HS256'])
        if 'fines_payment' in user_data['authorizations']:
            session['username'] = user_data['primary_id']
            session['user_home'] = user_data['inst']
            session['display_name'] = user_data['full_name']
            return redirect(url_for('index'))
        else:
            abort(403)
    else:
        return "no login cookie"

@app.route('/logout')
@auth_required
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/add-alt-call')
def add_alt_call():
    return render_template('find_alt_call_item.html')

@app.route('/add-alt-call/add-call', methods=['POST'])
def get_new_call():
    barcode = request.form['barcode']
    return render_template('update_alt_call_item.html', barcode=barcode)

@app.route('/add-alt-call/update', methods=['POST'])
def update_alt_call():
    # collect barcodes from form on previous page
    barcode = request.form['barcode']
    new_alt_call = request.form['alt-call'] 
    # try to find the item in alma or return an error
    try:
        item = _alma_get(app.config['API_HOST'] + app.config['GET_BY_BARCODE'].format(barcode))
    except requests.exceptions.RequestException as e:
        return e.args[0]
    
    # parse the item as XML
    root = ET.fromstring(item)
    # update alt call
    root.find('.//item_data/alternative_call_number').text = new_alt_call
    # enforce alt call type
    ac_type = root.find('.//item_data/alternative_call_number_type')
    ac_type.attrib['desc'] = "Other scheme"
    ac_type.text = "8"
    #try to post the modified item record back up to Alma or return an error
    item_link = root.attrib['link']
    updated_item = ET.tostring(root, encoding="utf-8")

    try:
        _alma_put(item_link, payload=updated_item)       
    except requests.exceptions.RequestException as e:
        return e.args[0]

    # save the result of the post transaction as a message to be displayed on the next page
    flash("Changed alt call for item {} to {}".format(barcode, new_alt_call))
    return redirect(url_for('add_alt_call'))
# begin add internal note functions
@app.route('/add-int-note')
def add_int_note():
    return render_template('find_int_note_item.html')

@app.route('/add-int-note/add-note', methods=['POST'])
def get_new_note():
    barcode = request.form['barcode']
    return render_template('update_int_note_item.html', barcode=barcode)

@app.route('/add-int-note/update', methods=['POST'])
def update_int_note():
    # collect barcodes from form on previous page
    barcode = request.form['barcode']
    new_int_note = request.form['int-note'] 
    # try to find the item in alma or return an error
    try:
        item = _alma_get(app.config['API_HOST'] + app.config['GET_BY_BARCODE'].format(barcode))
    except requests.exceptions.RequestException as e:
        return e.args[0]
    
    # parse the item as XML
    root = ET.fromstring(item)
    # update int note
    root.find('.//item_data/internal_note_1').text = new_int_note
    #try to post the modified item record back up to Alma or return an error
    item_link = root.attrib['link']
    updated_item = ET.tostring(root, encoding="utf-8")

    try:
        _alma_put(item_link, payload=updated_item)       
    except requests.exceptions.RequestException as e:
        return e.args[0]

    # save the result of the post transaction as a message to be displayed on the next page
    flash("Changed internal note 1 for item {} to {}".format(barcode, new_int_note))
    return redirect(url_for('add_int_note'))
@app.route('/test/<item>')

#end internal note functions
def fetch(item):
    record = _alma_get(app.config['API_HOST'] + app.config['GET_BY_BARCODE'].format(item))
    return record

# local functions
def _alma_get(resource, params=None, fmt='xml'):
    '''
    makes a generic alma api call, pass in a resource
    '''
    params = params or {}
    params['apikey'] = app.config['API_KEY']
    params['format'] = fmt
    r = requests.get(resource, params=params) 
    r.raise_for_status()
    if fmt == 'json':
        return r.json()
    else:
        return r.content

def _alma_put(resource, payload=None, params=None, fmt='xml'): 
    '''
    makes a generic put request to alma api. puts xml data.
    '''
    payload = payload or {}
    params = params or {}
    params['format'] = fmt
    headers = {'Content-type': 'application/xml',
               'Authorization' : 'apikey ' + app.config['API_KEY']}
    r = requests.put(resource,
                     headers=headers,
                     params=params,
                     data=payload)
    r.raise_for_status()
    if fmt == 'json':
        return r.json()
    else:
        return r.content

# run this app
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")