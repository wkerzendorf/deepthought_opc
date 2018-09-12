import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from alchemy import Referee, Base, Proposal, Review
import cherrypy
from cp_sqlalchemy import SQLAlchemyTool, SQLAlchemyPlugin

from jinja2 import Environment, FileSystemLoader

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
        reviews = self.db.query(Referee).filter_by(uuid=ref_id).one().reviews
        template = env.get_template('review_all.html.j2')

        return template.render(reviews=reviews)


@cherrypy.expose
class ReviewSaverService(object):
    
    @cherrypy.tools.accept(media="application/json")
    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def PUT(self):
        review_json = cherrypy.request.json
        # todo: get Authorization header (how in cherrypy?) and check against DB first (else return 401 Unauthorized)
        # todo: make sure that review.referee_id == user (else return 401 Unauthorized)
        try:
            review = Review.from_json(review_json)
            if not review.is_valid():
                raise ValueError('Review has one or more invalid values (e.g., score out of range).')
        except TypeError as e: # raised if JSON is missing an element
            cherrypy.response.status = 400
            response = {'Error': e.args[0]}
            return response
        except ValueError as e:
            cherrypy.response.status = 422
            response = {'Error': e.args[0]}
            return response

        try: 
        #     review.save() ??? 
        #     review = Review.fetch(...) ?
            saved_json = review.to_json()
            saved_json['last_updated'] = '2020-01-10 14:00:00'
            response = {'review': saved_json, 'is_complete': review.is_complete()}
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