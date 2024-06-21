from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail





db = SQLAlchemy()
DB_NAME = "database.db"

MAIL_SERVER = 'smtp.gmail.com'  # Replace with your SMTP server address
MAIL_PORT = 587                 # Default port for SMTP over TLS
MAIL_USE_TLS = True             # Use secure connection (TLS)
MAIL_USERNAME = 'chatappreset@gmail.com'     # Your email address used for sending
MAIL_PASSWORD = 'esla bcvf xvmy opdm'  # Your email password


def create_app():
    app = Flask(__name__, static_url_path='/static')    
    
 
    
    app.config['SECRET_KEY'] = 'password1050'
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_NAME}'
    app.config['UPLOAD_FOLDER'] = 'static/uploads'
    app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024 #100MB
    
    app.config['MAIL_SERVER'] = 'smtp.gmail.com'
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USERNAME'] = 'chatappreset@gmail.com'
    app.config['MAIL_PASSWORD'] = 'esla bcvf xvmy opdm'

    mail = Mail(app)
    app.mail=mail
    
    db.init_app(app)
    
    from .views import views
    from .auth import auth

    app.register_blueprint(views, url_prefix='/')
    app.register_blueprint(auth, url_prefix='/')


    from .models import User

    #creating db
    with app.app_context():
        db.create_all()


    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(id):
        return User.query.get(int(id))


    return app