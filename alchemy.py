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

    MIN_COMMENT = 20
    MIN_REF_KNOWLEDGE = 1
    MAX_REF_KNOWLEDGE = 3
    MIN_SCORE = 1.0
    MAX_SCORE = 5.0

    id = Column(Integer, primary_key=True)
    referee_id = Column(Integer, ForeignKey('referees.id'))
    proposal_id = Column(Integer, ForeignKey('proposals.id'))
    comment = Column(Text)
    ref_knowledge = Column(Integer)
    score = Column(Float)
    last_updated = Column(DateTime, onupdate=datetime.datetime.now)
    # todo: close_relationship = Column(Boolean, default=False)
    # todo: direct_competitor = Column(Boolean, default=False)

    proposal = relationship('Proposal')
    referee = relationship('Referee')

    @staticmethod
    def from_json(json):
        review = Review()
        # todo: add conflicts to list
        properties = ['id', 'referee_id', 'proposal_id', 'comment', 'ref_knowledge', 'score', 'last_updated']
        int_props = ['id', 'referee_id', 'proposal_id', 'ref_knowledge']
        for prop in properties:
            if prop not in json: 
                raise TypeError('JSON missing one or more required properties.')
            value = json[prop]
            if prop in int_props:
                value = None if value == '' else int(value)
            elif prop == 'score':
                value = None if value == '' else float(value)
            elif prop == 'comment': 
                value = None if value == '' else value

            setattr(review, prop, value)

        return review
    
    def to_json(self):
        json = {}
        properties = ['id', 'referee_id', 'proposal_id', 'comment', 'ref_knowledge', 'score', 'last_updated']
        for prop in properties: 
            json[prop] = getattr(self, prop)
        if self.proposal != None: # only works if review was fetched from DB
            json['proposal_eso_id'] = self.proposal.eso_id
        
        return json

    # comment must be a string
    # ref_knowledge must be 1-3
    # score must be 1.0 (outstanding) - 5.0 (rejected)
    # blank fields are OK
    # todo: True for either conflict (close_relationship, direct_competitor) eliminates these requirements
    def is_valid(self):
        comment_valid = self.comment == None or isinstance(self.comment, str)
        ref_knowledge_valid = self.ref_knowledge == None or (isinstance(self.ref_knowledge, int) and self.ref_knowledge >= self.MIN_REF_KNOWLEDGE and self.ref_knowledge <= self.MAX_REF_KNOWLEDGE)
        score_valid = self.score == None or (isinstance(self.score, float) and self.score >= self.MIN_SCORE and self.score <= self.MAX_SCORE)
        return comment_valid and ref_knowledge_valid and score_valid
    
    # todo: True for either conflict (close_relationship, direct_competitor) eliminates these requirements
    def is_complete(self):
        comment_filled = isinstance(self.comment, str) and len(self.comment) >= self.MIN_COMMENT
        ref_knowledge_filled = self.ref_knowledge != None
        score_filled = self.score != None
        # todo: conflicts
        return self.is_valid() and comment_filled and ref_knowledge_filled and score_filled
        




    