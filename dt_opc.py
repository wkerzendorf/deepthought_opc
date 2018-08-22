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
        template = env.get_template('review_all')

        return template.render(reviews=reviews)



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