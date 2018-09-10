import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from alchemy import Referee, Base, Proposal
import cherrypy
from cp_sqlalchemy import SQLAlchemyTool, SQLAlchemyPlugin

from jinja2 import Environment, FileSystemLoader

path = os.path.abspath(os.path.dirname(__file__))
env = Environment(loader=FileSystemLoader(os.path.join(path, 'templates')))

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
    @cherrypy.tools.json_out()
    def save_review(self, review_json):
        # todo: get Authorization header (how in cherrypy?) and check against DB first (else return 401 Unauthorized)
        # todo: make sure that review.referee_id == user (else return 401 Unauthorized)
        review = Review()
        review.proposal_id = review_json.proposal_id
        review.comment = review_json.comment
        review.ref_knowledge = review_json.ref_knowledge
        review.score = review_json.score
        # review.close_relationship = review_json.close_relationship
        # review.direct_competitor = review_json.direct_competitor
        # todo: make sure that review is valid (else return 422 Unprocessable entity)
        # try: 
        #     review.save() ??? 
        #     fetch saved review, turn it back into JSON (need Review.to_json() ?)
        #     return 200 OK, with fetched_review.to_json() as body
        # catch:
        #     return 500 Internal Error



if __name__ == '__main__':
    conf = {
        'global' : {
            'tools.proxy.on':True,
            'server.socket_host' : '0.0.0.0',
            'server.socket_port' : 8081,
            'server.thread_pool' : 8
        },
        '/css' : {
            'tools.staticdir.on'  : True,
            'tools.staticdir.dir' : os.path.join(path, 'css')
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
    cherrypy.quickstart(DTOPC(), '/', conf)