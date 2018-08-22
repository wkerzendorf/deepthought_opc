import os
import sys
from sqlalchemy import Column, ForeignKey, Integer, String, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine

Base = declarative_base()

def get_data_review(prop_id, referee_id):
    return {'comment':'test', 'ranking':4, 'similarity':3}

def get_reviewer_per_proposal(ref_id):
    return ['sdfsdf', 'sdfsd', 'sdfsdf', 'sdfsdf']

class Review(Base):
    __tablename__ = 'reviews'

    id = Column(Integer, )
    referee_id = Column(Integer, ForeignKey('referees.id'))
    proposal_id = Column(Integer, ForeignKey('proposals.id'))
    comment = Column(Text)
    ref_knowledge = Column(Integer)
    last_updated = Column(Datetime, onupdate=datetime.datetime.now)

class Referee(Base):
    __tablename__ = 'referees'
    # Here we define columns for the table person
    # Notice that each column is also a normal Python instance attribute.
    id = Column(Integer, primary_key=True)
    uid = Column(String(100), nullable=False)
    first_name = Column(String(250), nullable=False)
    last_name = Column(String(250), nullable=False)
    reviews = relationship('Review')
    proposals = relationship('Proposal', secondary=Review, back_populates='referees')

class Proposal(Base):
    __tablename__  = 'proposals'

    id = Column(Integer, primary_key=True)
    #103.x-0123
    uid = Column(String(10))






    