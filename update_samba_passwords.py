from flask import Flask, render_template, request, flash
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, ValidationError
import ldap
import subprocess
from google.cloud import secretmanager

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'  # Replace with your secret key

# Initialize Secret Manager client
client = secretmanager.SecretManagerServiceClient()

# Your GCP project ID
project_id = 'your-gcp-project-id'

# Form definition
class UserForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Submit')

    def validate_password(self, field):
        password = field.data
        if len(password) < 8:
            raise ValidationError('Password must be at least 8 characters.')
        if not any(char.isdigit() for char in password):
            raise ValidationError('Password must contain a number.')
        if not any(char.isupper() for char in password):
            raise ValidationError('Password must contain an uppercase letter.')

@app.route('/', methods=['GET', 'POST'])
def index():
    try:
        # Get the logged-in username
        username = get_logged_in_username()
    except ldap.LDAPError as e:
        flash(f"Error connecting to LDAP server: {str(e)}")
        return render_template('index.html', form=None)

    form = UserForm(username=username)
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        try:
            update_samba_password(username, password)
            set_secret(project_id, f'{username}-password', password)
            flash('Password updated successfully.', 'success')
        except Exception as e:
            flash(f"Error updating password: {str(e)}", 'error')
    return render_template('index.html', form=form)

def get_logged_in_username():
    # Connect to your LDAP server
    l = ldap.initialize("ldap://your.ldap.server")
    l.protocol_version = ldap.VERSION3
    l.simple_bind_s("user_dn", "password")

    # Get the logged-in username
    result = l.search_s("ou=users,dc=example,dc=com", ldap.SCOPE_SUBTREE, "(objectclass=person)")
    for dn, entry in result:
        if 'uid' in entry:
            return entry['uid'][0].decode('utf-8')

def update_samba_password(user, password):
    process = subprocess.Popen(['smbpasswd', '-a', user], stdin=subprocess.PIPE)
    process.communicate(input=f'{password}\n{password}\n'.encode())

def set_secret(project_id, secret_id, secret_value):
    # Build the resource name of the parent project
    parent = client.project_path(project_id)

    # Check if the secret already exists
    secrets = [secret for secret in client.list_secrets(request={'parent': parent}) if secret.name == f'{parent}/secrets/{secret_id}']

    if secrets:
        # Secret already exists, update it
        client.add_secret_version(request={'parent': f'projects/{project_id}/secrets/{secret_id}', 'payload': {'data': secret_value.encode('UTF-8')}})
    else:
        # Secret doesn't exist, create it
        client.create_secret(
            request={
                'parent': parent,
                'secret_id': secret_id,
                'secret': {'replication': {'automatic': {}}}
            }
        )
        client.add_secret_version(request={'parent': f'projects/{project_id}/secrets/{secret_id}', 'payload': {'data': secret_value.encode('UTF-8')}})

if __name__ == '__main__':
    app.run(port=5000, debug=True)  # Do not use debug mode in production
