import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from alchemy import Referee, Base, Proposal, Review
import cherrypy
from cp_sqlalchemy import SQLAlchemyTool, SQLAlchemyPlugin

from jinja2 import Environment, FileSystemLoader

import base64

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

    @cherrypy.expose
    def index(self):
        cherrypy.session.load()
        if cherrypy.session.get('ref_id', None) is not None:
            return self.display(cherrypy.session['ref_id'])
        available_referees = [item[0] for item in self.db.query(Referee.uuid).all()]
        return """<html>
          <head></head>
          <body>
            <form method="get" action="display">
              <input type="text" value="{0}" name="ref_id" />
              <button type="submit">Give it now!</button>
            </form>
            available referee ids
            {1}
          </body>
        </html>""".format(available_referees[3], str(available_referees))

    @cherrypy.expose
    def display(self, ref_id):
        cherrypy.session['ref_id'] = ref_id
        id_and_password = ref_id+':'+ref_id
        user_token = base64.b64encode(id_and_password.encode('ascii')).decode('ascii')
        reviews = self.db.query(Referee).filter_by(uuid=ref_id).one().reviews
        template = env.get_template('review_all.html.j2')

        return template.render(ref_id=ref_id, user_token=user_token, reviews=reviews)


@cherrypy.expose
class ReviewSaverService(object):
    @property
    def db(self):
        return cherrypy.request.db
    
    @cherrypy.tools.accept(media="application/json")
    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def PUT(self):
        if 'Authorization' not in cherrypy.request.headers:
            cherrypy.response.status = 401
            response = {'Error': 'Missing user token.'}
            return response 

        token = cherrypy.request.headers['Authorization'][6:] # see https://en.wikipedia.org/wiki/Basic_access_authentication
        token = base64.b64decode(token).decode('ascii')
        expected_token = cherrypy.session['ref_id']+":"+cherrypy.session['ref_id']
        if expected_token != token:
            cherrypy.response.status = 401
            response = {'Error': 'Submitted user token does not match session user.'}
            return response 
        
        submitted_review_json = cherrypy.request.json
        try:
            submitted_review = Review.from_json(submitted_review_json)
            if not submitted_review.is_valid():
                raise ValueError('Review has one or more invalid values (e.g., score out of range).')
        except TypeError as e: # raised if JSON is missing an element
            cherrypy.response.status = 400
            response = {'Error': e.args[0]}
            return response
        except ValueError as e:
            cherrypy.response.status = 422
            response = {'Error': e.args[0]}
            return response

        fetched_review = self.db.query(Review).filter_by(id=submitted_review.id).one()
        if fetched_review.referee_id != submitted_review.referee_id:
            cherrypy.response.status = 401
            response = {'Error': 'Review does not belong to this user.'}
            return response 
        if fetched_review.proposal_id != submitted_review.proposal_id:
            cherrypy.response.status = 422
            response = {'Error': 'Proposal IDs do not match. Please contact administrator.'}
            return response 

        try: 
        #     review.save() ??? 
        #     review = Review.fetch(...) ?
            # saved_json = submitted_review.to_json()
            saved_json = fetched_review.to_json()
            saved_json['last_updated'] = '2020-01-10 14:00:00'
            response = {'review': saved_json, 'is_complete': submitted_review.is_complete(), 'token': token}
            return response
        except Exception as e:
            cherrypy.response.status = 500
            response = {'Error': e.args[0]}
            return response
        


if __name__ == '__main__':
    conf = {
        'global' : {
            'tools.proxy.on':True,
            'server.socket_host' : '0.0.0.0',
            'server.socket_port' : 8081,
            'server.thread_pool' : 8
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


    }
    cherrypy.tools.db = SQLAlchemyTool()

    sqlalchemy_plugin = SQLAlchemyPlugin(cherrypy.engine, Base, 'sqlite:///dt_opc_test.db')
    sqlalchemy_plugin.subscribe()
    sqlalchemy_plugin.create()
    webapp = DTOPC()
    webapp.save_review = ReviewSaverService()
    cherrypy.quickstart(webapp, '/', conf)