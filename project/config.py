import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

SECRET_KEY = os.environ['SECRET_KEY']
STATIC_FOLDER = 'static'
TEMPLATES_FOLDER = 'templates'
#SECURITY_PASSWORD_SALT = 'edndre'

#Database
SQLALCHEMY_DATABASE_URI = os.environ['DATABASE_URL']
SQLALCHEMY_TRACK_MODIFICATIONS = False

# AWS Secrets
#AWS_SECRET_KEY = environ.get('AWS_SECRET_KEY')
#AWS_KEY_ID = environ.get('AWS_KEY_ID')