from flask import Flask, abort, flash, make_response, redirect, request, render_template, session, url_for
from functools import wraps
import json
import jwt
import logging
import os
import requests
import settings
import xml.etree.ElementTree as ET

# define our webapp
app = Flask(__name__)

#configuration from settings.py
app.secret_key = settings.SESSION_KEY
app.config['API_HOST'] = settings.API_HOST
app.config['AUTHORIZED_GROUP'] = settings.AUTHORIZED_GROUP
app.config['BIBS_API_KEY'] = settings.BIBS_API_KEY
app.config['USERS_API_KEY'] = settings.USERS_API_KEY
app.config['GET_BY_BARCODE'] = settings.GET_BY_BARCODE
app.config['USERS'] = settings.USERS
app.config['LOG_FILE'] = settings.LOG_FILE

# xpaths for fields that need updating
app.config['XPATH'] = {
    'alt_call' : './/item_data/alternative_call_number',
    'alt_call_type' : './/item_data/alternative_call_number_type',
    'barcode' : './/item_data/barcode',
    'int_note' : './/item_data/internal_note_1',
    'mms_id' : './/mms_id',
    'title' : './/title',
}

# audit log
audit_log = logging.getLogger('audit')
audit_log.setLevel(logging.INFO)
file_handler = logging.FileHandler(app.config['LOG_FILE'])
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter('%(asctime)s\t%(message)s'))
audit_log.addHandler(file_handler)

# login wrapper
def auth_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'username' in session:
            return f(*args, **kwargs)
        elif app.config['ENV'] == 'development':
            session['username'] = 'devuser'
            return f(*args, **kwargs)
        else:
            return redirect(url_for('login'))
    return decorated

# error handlers
@app.errorhandler(400)
def page_not_found(e):
    return render_template('400.html'), 400

@app.errorhandler(403)
def page_not_found(e):
    return render_template('403.html'), 403

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def page_not_found(e):
    return render_template('500.html'), 500

# routes and controllers
@app.route('/')
@auth_required
def index():
    return render_template("index.html")

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        response_code = _alma_authenticate(username, password)
        if response_code == 204:
            authorized = _alma_authorize(request.form['username'])
            if authorized:
                session['username'] = username
                return redirect(url_for('index'))
            else:
                return abort(403)
        else:
            flash('User not found, check username and password')
            return redirect(url_for('login'))
    else:
        return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return render_template('logout.html')

@app.route('/update-field/alt-call')
@auth_required
def update_alt_call():
    field_name = 'Alternative Call Number'
    return render_template('find_item.html',
                           get_input_function='get_alt_call_input',
                           field_name=field_name)

@app.route('/update-field/alt-call/get-input', methods=['POST'])
@auth_required
def get_alt_call_input():
    field_name = 'Alternative Call Number' 
    barcode = request.form['barcode']
    # try to find the item in alma or return an error
    try:
        item = _alma_get(app.config['API_HOST'] +
                         app.config['GET_BY_BARCODE'].format(barcode))
    except requests.exceptions.RequestException as e:
        abort(400)
    item_record = item.decode(encoding='utf-8')
    item_root = _parse_item(item_record)
    # grab some fields from retrieved item to show operator
    try:
        retrieved_barcode = item_root.find(app.config['XPATH']['barcode']).text
        retrieved_title = item_root.find(app.config['XPATH']['title']).text.strip('/')
    except:
        return abort(500)
    return render_template('get_input.html', 
                           barcode=barcode,
                           field_name=field_name,
                           item=item_record,
                           update_function='update_alt_call_field',
                           retrieved_barcode=retrieved_barcode,
                           retrieved_title=retrieved_title)

@app.route('/update-field/alt-call/update', methods=['POST'])
@auth_required
def update_alt_call_field():
    field = 'alt_call'
    barcode = request.form['barcode']
    new_val = request.form['new_val']
    item_record = request.form['item-record']

    updated_result =  _update_field(item_record, field, new_val)
    # save the result of the post transaction as a message to be displayed on the next page
    if updated_result:
        flash("Changed {} for {} to {}".format(field, barcode, new_val))
        return redirect(url_for('update_alt_call'))
    else:
        return updated_result

# internal note update
@app.route('/update-field/int-note')
@auth_required
def update_int_note():
    field_name = 'Internal Note'
    return render_template('find_item.html',
                           get_input_function='get_int_note_input',
                           field_name=field_name)

@app.route('/update-field/int-note/get-input', methods=['POST'])
@auth_required
def get_int_note_input():
    field_name = 'Internal Note' 
    barcode = request.form['barcode']
    # try to find the item in alma or return an error
    try:
        item = _alma_get(app.config['API_HOST'] +
                         app.config['GET_BY_BARCODE'].format(barcode))
    except requests.exceptions.RequestException as e:
        abort(400)
    item_record = item.decode(encoding='utf-8')
    item_root = _parse_item(item_record)
    # grab some fields from retrieved item to show operator
    try:
        retrieved_barcode = item_root.find(app.config['XPATH']['barcode']).text
        retrieved_title = item_root.find(app.config['XPATH']['title']).text
    except:
        abort(500)
    return render_template('get_input.html', 
                           barcode=barcode,
                           field_name=field_name,
                           item=item_record,
                           update_function='update_int_note_field',
                           retrieved_barcode=retrieved_barcode,
                           retrieved_title=retrieved_title)

@app.route('/update-field/int-note/update', methods=['POST'])
@auth_required
def update_int_note_field():
    field = 'int_note'
    barcode = request.form['barcode']
    new_val = request.form['new_val']
    item_record = request.form['item-record']

    updated_result =  _update_field(item_record, field, new_val)
    # save the result of the post transaction as a message to be displayed on the next page
    if updated_result:
        flash("Changed {} for {} to {}".format(field, barcode, new_val))
        return redirect(url_for('update_int_note'))
    else:
        return updated_result

def fetch(item):
    record = _alma_get(app.config['API_HOST'] + app.config['GET_BY_BARCODE'].format(item))
    return record

# local functions
def _alma_authenticate(username, password):
    headers = {
              'Authorization' : 'apikey ' + app.config['USERS_API_KEY'],
              'Exl-User-Pw' : password
             }
    r = requests.post(app.config['API_HOST'] + app.config['USERS'].format(username),
                      headers=headers)
    return r.status_code

def _alma_authorize(username):
    r = _alma_get(app.config['API_HOST'] +
                  app.config['USERS'].format(username), 
                  api='users',
                  fmt='json') 
    if r['user_group']['value'] == app.config['AUTHORIZED_GROUP']:
        return True
    else:
        return False

def _alma_get(resource, params=None, api='bibs', fmt='xml'):
    '''
    makes a generic alma api call, pass in a resource
    '''
    if api == 'bibs':
        key = app.config['BIBS_API_KEY']
    elif api == 'users':
        key = app.config['USERS_API_KEY']
    else:
        abort(500)
    params = params or {}
    params['apikey'] = key
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
               'Authorization' : 'apikey ' + app.config['BIBS_API_KEY']}
    r = requests.put(resource,
                     headers=headers,
                     params=params,
                     data=payload)
    r.raise_for_status()
    if fmt == 'json':
        return r.json()
    else:
        return r.content

def _parse_item(item_record):
    '''
    Returns Element tree from string
    '''
    try:
        root = ET.fromstring(item_record)
        return root
    except ET.ParseError as e:
        return e.args[0]
    

def _update_field(item_record, field, new_val):
    '''
    updates a feild in marcxml record pass in record as xml,
    field name to be updated (must also be configured in XPATH
    setting), and the new value the field should be updated to.
    '''
    item_root = _parse_item(item_record)
    # get id
    mms_id = item_root.find(app.config['XPATH']['mms_id']).text
    # update field
    item_root.find(app.config['XPATH'][field]).text = new_val
    # if field is alt call, enforce alt call type
    if field == 'alt_call':
        try:
            enforced = _enforce_call_type(item_root)
        except:
            return "could not enforce call type, aborting"

    #try to post the modified item record back up to Alma or return an error
    item_link = item_root.attrib['link']
    updated_item = ET.tostring(item_root, encoding="utf-8")

    try:
        result = _alma_put(item_link, payload=updated_item)
        audit_log.info('{operator}\t{mms_id}\t{type}\t{value}'.format(operator=session['username'],
                                                                mms_id=mms_id,
                                                                type=field,
                                                                value=new_val))
        return result
    except requests.exceptions.RequestException as e:
        abort(400)


def _enforce_call_type(item_root):
    ac_type = item_root.find(app.config['XPATH']['alt_call_type'])
    ac_type.attrib['desc'] = "Other scheme"
    ac_type.text = "8"


# run this app
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
