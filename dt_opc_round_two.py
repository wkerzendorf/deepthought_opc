import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from alchemy import Referee, Base, Proposal, Review, ReviewRating
import cherrypy
from cherrypy.lib.static import serve_file
from cp_sqlalchemy import SQLAlchemyTool, SQLAlchemyPlugin

import datetime
from jinja2 import Environment, FileSystemLoader

import base64
import json

path = os.path.abspath(os.path.dirname(__file__))
env = Environment(loader=FileSystemLoader(os.path.join(path, 'templates')))
def review_is_complete(review): # defined here to make the method accessible in jinja
    return review.is_complete()
env.filters['is_complete'] = review_is_complete

class DTOPC(object):
    _cp_config = {'tools.sessions.on': True, 
                'tools.sessions.timeout': 60,
                'tools.db.on': True}

    def __init__(self, db_name='dt_opc_test.db'):
        pass
        # an Engine, which the Session will use for connection
        # resources
        #self.engine = create_engine('sqlite:///{0}'.format(db_name))

        # create a configured "Session" class
        #Session = sessionmaker(bind=self.engine)

        # create a Session
        #self.session = Session()

    @property
    def db(self):
        return cherrypy.request.db
    
    # for certain routes, if the user is not logged in, send them to index:
    def logged_out_redirect(self):
        if cherrypy.session.get('ref_id', None) is None: 
            raise cherrypy.HTTPRedirect("/")

    @cherrypy.expose
    def index(self, error=None):
        cherrypy.session.load()
        if cherrypy.session.get('ref_id', None) is not None:
            raise cherrypy.HTTPRedirect("/show_reviews_for_pi")
        available_referees = self.db.query(Referee).all()
        
        template = env.get_template('index.html.j2')

        return template.render(ref_id=None, error=error, available_referees=[])

    @cherrypy.expose
    def login(self, ref_id=None):
        if ref_id is None: # i.e., route visited without form submission...
            if cherrypy.session.get('ref_id', None) is not None: # user already logged in
                raise cherrypy.HTTPRedirect("/show_reviews_for_pi")
            else:
                raise cherrypy.HTTPRedirect("/")
        
        ref_id = ref_id.strip()
        referee = self.db.query(Referee).filter_by(uuid=ref_id).one_or_none()
        if referee is None:
            return self.index(error="Invalid ID. Please check for typographical mistakes and try again. Note that IDs are case sensitive.")
        cherrypy.session['ref_id'] = ref_id
        raise cherrypy.HTTPRedirect("/show_reviews_for_pi")

    @cherrypy.expose
    def show_reviews_for_pi(self, error=None):
        self.logged_out_redirect()
        ref_id = cherrypy.session['ref_id']
        referee = self.db.query(Referee).filter_by(uuid=ref_id).one()

        id_and_password = ref_id+':'+ref_id
        user_token = base64.b64encode(id_and_password.encode('ascii')).decode('ascii')
        # TODO: way to get PI's proposal using their ref_id
        pi_proposal = 1
        reviews_for_pi = self.db.query(Review).filter_by(proposal_id=pi_proposal)
        
        # fetch ratings the PI has already made, for display
        ratings_of_pi = self.db.query(ReviewRating).filter_by(proposal_id=pi_proposal)
        ratings = {rating.referee_id: rating.review_rating for rating in ratings_of_pi}

        template = env.get_template('show_reviews_for_pi.html.j2')

        return template.render(ref_id=ref_id, user_token=user_token, reviews_for_pi=reviews_for_pi, ratings=ratings)

    
    @cherrypy.expose
    def logout(self):
        cherrypy.session.delete()
        template = env.get_template('logout.html.j2')
        return template.render(ref_id=None)

    @cherrypy.expose
    def error_404(self):
        template = env.get_template('404.html.j2')
        return template.render()
        



@cherrypy.expose
class ReviewRatingSaverService(object):
    @property
    def db(self):
        return cherrypy.request.db
    
    @cherrypy.tools.accept(media="application/json")
    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def PUT(self):
        if 'ref_id' not in cherrypy.session:
            cherrypy.response.status = 401
            response = {'Error': 'Your session has expired. Please log in again.'}
            return response 
        if 'Authorization' not in cherrypy.request.headers:
            cherrypy.response.status = 401
            response = {'Error': 'Missing user token.'}
            return response 

        token = cherrypy.request.headers['Authorization'][6:] # see https://en.wikipedia.org/wiki/Basic_access_authentication
        token = base64.b64decode(token).decode('ascii')
        expected_token = cherrypy.session['ref_id']+":"+cherrypy.session['ref_id']
        if expected_token != token:
            cherrypy.response.status = 403
            response = {'Error': 'Submitted user token does not match session user.'}
            return response 
        
        submitted_json = cherrypy.request.json
        review_id = submitted_json['review_id']
        rating_json = submitted_json['review_rating']
        # ensure that submitted review matches db and is valid:
        try:
            # if 'id' not in submitted_review_json:
            #     raise TypeError('Review missing id.')
            # review = self.db.query(ReviewRating).get(submitted_review_json['id'])
            # upset rating; i.e. update existing rating or insert it if it doesn't already exist
            new_rating = False
            review_rating = self.db.query(ReviewRating).filter(ReviewRating.proposal_id == rating_json['proposal_id']).filter(ReviewRating.referee_id == rating_json['referee_id']).first()
            if not review_rating:
                new_rating = True
                review_rating = ReviewRating()
                review_rating.create_from_json(rating_json)
            else:
                review_rating.update_from_json(rating_json)

            # TODO ensure that ref_id matches pi of review
            if not review_rating.is_valid():
                raise ValueError('Rating is invalid (must be 1-4) and IDs must be filled.')
        except TypeError as e: # raised if JSON is missing an element
            self.db.rollback()
            cherrypy.response.status = 400
            response = {'Error': e.args[0]}
            return response
        except ValueError as e: # raised if invalid or an id doesn't match
            self.db.rollback()
            reason = e.args[0]
            unauthorized_reasons = ['Review does not belong to this referee.', 'Referee has not accepted the confidentiality terms.']
            cherrypy.response.status = 403 if reason in unauthorized_reasons else 422
            response = {'Error': reason}
            return response

        # save the updated review and return JSON:
        try: 
            if new_rating:
                self.db.add(review_rating)
            self.db.commit()
            rating = self.db.query(ReviewRating).filter(ReviewRating.proposal_id == rating_json['proposal_id']).filter(ReviewRating.referee_id == rating_json['referee_id']).first()
            saved_json = rating.to_json()
            response = {'review_id': review_id, 'review_rating': saved_json}
            return response
        except Exception as e:
            self.db.rollback()
            cherrypy.response.status = 500
            response = {'Error': e.args[0]}
            return response
        
def error404(status, message, traceback, version):
    template = env.get_template('404.html.j2')
    return template.render()

if __name__ == '__main__':
    with open('credentials.json') as f:
        credentials = json.load(f)
    run_env = credentials['env'] # test = sqlite; development + production = mysql

    conf = {
        'global' : {
            'tools.proxy.on':True,
            'server.socket_host' : '0.0.0.0',
            'server.socket_port' : credentials[run_env]['cherrypy_port'],
            'server.thread_pool' : 8
        },
        '/': {
            'error_page.404': error404 # nicer error msg for undefined routes
        },
        '/save_review_rating': {
            'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
            'tools.response_headers.on': True,
            'tools.response_headers.headers': [('Content-Type', 'application/json')]
        },
        '/css' : {
            'tools.staticdir.on'  : True,
            'tools.staticdir.dir' : os.path.join(path, 'css')
        },
        '/img' : {
            'tools.staticdir.on'  : True,
            'tools.staticdir.dir' : os.path.join(path, 'img')
        },
        '/js' : {
            'tools.staticdir.on'  : True,
            'tools.staticdir.dir' : os.path.join(path, 'js')
        },
        '/pdf' : {
            'tools.staticdir.on'  : True,
            'tools.staticdir.dir' : os.path.join(path, 'pdf')
        },
        '/favicon.ico' : {
            'tools.staticfile.on'  : True,
            'tools.staticfile.filename' : os.path.join(path, 'favicon.ico')
        }
    }
    
    dsn = credentials[run_env]['writer'] # in the format <engine>://<connection_string>

    cherrypy.tools.db = SQLAlchemyTool()

    # sqlalchemy_plugin = SQLAlchemyPlugin(cherrypy.engine, Base, 'sqlite:///dt_opc_test.db')
    sqlalchemy_plugin = SQLAlchemyPlugin(cherrypy.engine, Base, dsn)
    sqlalchemy_plugin.subscribe()
    sqlalchemy_plugin.create()
    webapp = DTOPC()
    webapp.save_review_rating = ReviewRatingSaverService()
    cherrypy.quickstart(webapp, '/', conf)
