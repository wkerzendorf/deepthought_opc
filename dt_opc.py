import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from alchemy import Referee, Base, Proposal, Review
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
    def index(self):
        cherrypy.session.load()
        if cherrypy.session.get('ref_id', None) is not None:
            raise cherrypy.HTTPRedirect("/display")
        available_referees = self.db.query(Referee).all()
        
        template = env.get_template('index.html.j2')

        return template.render(ref_id=None, some_id="Your DPR ID", available_referees=[])

    @cherrypy.expose
    def login(self, ref_id=None):
        if ref_id is None: # i.e., route visited without form submission...
            if cherrypy.session.get('ref_id', None) is not None: # user already logged in
                raise cherrypy.HTTPRedirect("/display")
            else:
                raise cherrypy.HTTPRedirect("/")
        cherrypy.session['ref_id'] = ref_id
        raise cherrypy.HTTPRedirect("/display")

    @cherrypy.expose
    def agreement(self): # display the agreement text and form
        self.logged_out_redirect()
        ref_id = cherrypy.session['ref_id']
        referee = self.db.query(Referee).filter_by(uuid=ref_id).one()
        if referee.accepted_tou: # no need to agree if already done
            raise cherrypy.HTTPRedirect("/display")
        template = env.get_template('agreement.html.j2')

        return template.render(ref_id=ref_id)
    
    @cherrypy.expose
    def process_agreement(self, agree=None): # record the referee's agreement and redirect to display
        self.logged_out_redirect()
        if agree not in [1, "1"]:
            raise cherrypy.HTTPRedirect("/agreement")
        ref_id = cherrypy.session['ref_id']
        referee = self.db.query(Referee).filter_by(uuid=ref_id).one()
        referee.accepted_tou = True
        self.db.commit()
        raise cherrypy.HTTPRedirect("/display")

    @cherrypy.expose
    def display(self, error=None):
        self.logged_out_redirect()
        ref_id = cherrypy.session['ref_id']
        referee = self.db.query(Referee).filter_by(uuid=ref_id).one()
        if not referee.accepted_tou: # must agree
            raise cherrypy.HTTPRedirect("/agreement")
        if referee.finalized_submission: # if they've finished, they can't see proposals/reviews anymore
            raise cherrypy.HTTPRedirect("/complete")

        id_and_password = ref_id+':'+ref_id
        user_token = base64.b64encode(id_and_password.encode('ascii')).decode('ascii')
        reviews = self.db.query(Referee).filter_by(uuid=ref_id).one().reviews
        template = env.get_template('review_all.html.j2')
        all_complete = all([review.is_complete() for review in reviews])

        return template.render(ref_id=ref_id, user_token=user_token, reviews=reviews, all_complete=all_complete, tz=datetime.timezone.utc, error=error)
    
    @cherrypy.expose
    def get_pdf(self, proposal):
        # careful testing this part, firefox seems to cache download files (even if you cancel out of them)
        self.logged_out_redirect()
        ref_id = cherrypy.session['ref_id']
        referee = self.db.query(Referee).filter_by(uuid=ref_id).one()
        forbidden_filename = os.path.abspath('pdf/403.pdf')
        if not referee.accepted_tou or referee.finalized_submission:
            # cherrypy.log('not accepted_tou or finalized submission')
            return serve_file(forbidden_filename, content_type='application/pdf', disposition='attachment')

        referee_proposal_ids = [prop.eso_id for prop in referee.proposals]
        # cherrypy.log(', '.join(referee_proposal_ids))
        if proposal in referee_proposal_ids:
            pdf_filename = os.path.abspath('proposals/'+proposal+'.pdf')
            return serve_file(pdf_filename, content_type='application/pdf', disposition='attachment')
        else:
            return serve_file(forbidden_filename, content_type='application/pdf', disposition='attachment')

    @cherrypy.expose
    def finalize(self, feedback):
        self.logged_out_redirect()
        ref_id = cherrypy.session['ref_id']
        referee = self.db.query(Referee).filter_by(uuid=ref_id).one()
        if not referee.accepted_tou:
            raise cherrypy.HTTPRedirect("/agreement")
        if not referee.completed_all_reviews():
            raise cherrypy.HTTPRedirect("/display")
        
        referee.feedback = feedback
        referee.finalized_submission = True
        self.db.commit()

        raise cherrypy.HTTPRedirect("/complete")
    
    # route for after "submit all" has been pressed, or finalized referees logging back in:
    @cherrypy.expose
    def complete(self):
        self.logged_out_redirect()
        ref_id = cherrypy.session['ref_id']
        referee = self.db.query(Referee).filter_by(uuid=ref_id).one()
        if not referee.finalized_submission:
            raise cherrypy.HTTPRedirect("/display")
        template = env.get_template('complete.html.j2')
        return template.render(ref_id=ref_id)

    
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
class ReviewSaverService(object):
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
        
        submitted_review_json = cherrypy.request.json
        # ensure that submitted review matches db and is valid:
        try:
            if 'id' not in submitted_review_json:
                raise TypeError('Review missing id.')
            review = self.db.query(Review).get(submitted_review_json['id'])
            review.update_from_json(submitted_review_json)
            if review.referee.uuid != cherrypy.session['ref_id']:
                raise ValueError('Review does not belong to this referee.')
            if not review.referee.accepted_tou:
                raise ValueError('Referee has not accepted the confidentiality terms.')
            if not review.is_valid():
                raise ValueError('Review has one or more invalid values (e.g., score out of range).')
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
            self.db.commit()
            review = self.db.query(Review).get(submitted_review_json['id'])
            saved_json = review.to_json()
            response = {'review': saved_json, 'is_complete': review.is_complete()}
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
    conf = {
        'global' : {
            'tools.proxy.on':True,
            'server.socket_host' : '0.0.0.0',
            'server.socket_port' : 8081,
            'server.thread_pool' : 8
        },
        '/': {
            'error_page.404': error404 # nicer error msg for undefined routes
        },
        '/save_review': {
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
    
    with open('credentials.json') as f:
        credentials = json.load(f)
    runEnv = credentials['env'] # test = sqlite; development + production = mysql
    dsn = credentials[runEnv]['writer'] # in the format <engine>://<connection_string>

    cherrypy.tools.db = SQLAlchemyTool()

    # sqlalchemy_plugin = SQLAlchemyPlugin(cherrypy.engine, Base, 'sqlite:///dt_opc_test.db')
    sqlalchemy_plugin = SQLAlchemyPlugin(cherrypy.engine, Base, dsn)
    sqlalchemy_plugin.subscribe()
    sqlalchemy_plugin.create()
    webapp = DTOPC()
    webapp.save_review = ReviewSaverService()
    cherrypy.quickstart(webapp, '/', conf)