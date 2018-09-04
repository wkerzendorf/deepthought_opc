import os
import sys
import datetime
from sqlalchemy import Column, ForeignKey, Integer, String, Text, DateTime, Float, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine

Base = declarative_base()


class Referee(Base):
    __tablename__ = 'referees'
    # Here we define columns for the table person
    # Notice that each column is also a normal Python instance attribute.
    id = Column(Integer, primary_key=True)
    uuid = Column(String(100), nullable=False)
    accepted_tou = Column(Boolean, default=False)
    #first_name = Column(String(250), nullable=False)
    #last_name = Column(String(250), nullable=False)
    #email = Column(String(250))
    reviews = relationship('Review')
    proposals = relationship('Proposal', secondary='reviews', 
    backref='referees')
    

    def __repr__(self):
        return "<Referee {0}>".format(self.uuid)

class Proposal(Base):
    __tablename__  = 'proposals'

    id = Column(Integer, primary_key=True)
    eso_id = Column(String(10)) # such as 103.x-0123
    title = Column(String)
    abstract = Column(String) 

    def __repr__(self):
        return "<Proposal {0} Title: {1}>".format(self.eso_id, self.title)

class Review(Base):
    __tablename__ = 'reviews'

    id = Column(Integer, primary_key=True)
    referee_id = Column(Integer, ForeignKey('referees.id'))
    proposal_id = Column(Integer, ForeignKey('proposals.id'))
    comment = Column(Text)
    ref_knowledge = Column(Integer)
    score = Column(Float)
    last_updated = Column(DateTime, onupdate=datetime.datetime.now)

    proposal = relationship('Proposal')
    referee = relationship('Referee')




    