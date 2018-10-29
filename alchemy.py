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
    uuid = Column(String(length=100), nullable=False)
    accepted_tou = Column(Boolean, default=False)
    proposal_submitted_id = Column(Integer, ForeignKey('reviews.proposal_id'))
    #first_name = Column(String(250), nullable=False)
    #last_name = Column(String(250), nullable=False)
    #email = Column(String(250))
    reviews = relationship('Review', foreign_keys='Review.referee_id')
    proposals = relationship('Proposal', secondary='reviews', 
    backref='referees', foreign_keys='[Review.referee_id, Review.proposal_id]')
    feedback = Column(Text, default='')
    finalized_submission = Column(Boolean, default=False)
    reviews_received = relationship('Review', foreign_keys='Referee.proposal_submitted_id')
    def __repr__(self):
        return "<Referee {0}>".format(self.uuid)
    
    def completed_all_reviews(self):
        return all([review.is_complete() for review in self.reviews])

#class ProposalSubmitted(Base):
#    __tablename__ = 'proposal_submitted'
#
#    id = Column(Integer, primary_key=True)
#    referee_id = 
#    proposal_id = Column(Integer, ForeignKey('proposals.id'))


class Proposal(Base):
    __tablename__  = 'proposals'

    id = Column(Integer, primary_key=True)
    eso_id = Column(String(length=20)) # such as 103.x-0123
    title = Column(String(length=256))
    abstract = Column(Text()) 

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
    # close relationship = 1
    # direct competitor = 2
    conflicted = Column(Integer, default=0)

    proposal = relationship('Proposal', foreign_keys=[proposal_id])
    referee = relationship('Referee', foreign_keys=[referee_id])

    # update self's properties based on received JSON document
    def update_from_json(self, json):
        properties = ['referee_id', 'proposal_id', 'comment', 'ref_knowledge', 'score', 'conflicted']
        for prop in properties:
            if prop not in json: 
                raise TypeError('JSON missing one or more required properties.')

            value = json[prop]
            if prop in ['referee_id', 'proposal_id']:
                if int(value) != getattr(self, prop):
                    raise ValueError(prop+' of submitted JSON does not match review.')
                else:
                    continue
            elif prop == 'comment':
                value = None if value == '' else value
            elif prop == 'score':
                value = None if value == '' else float(value)
            elif prop in ['ref_knowledge', 'conflicted']: 
                value = None if value == '' else int(value)

            setattr(self, prop, value)
    

    def to_json(self):
        review_json = {}
        properties = ['id', 'referee_id', 'proposal_id', 'comment', 'ref_knowledge', 'score', 'conflicted']
        for prop in properties: 
            review_json[prop] = getattr(self, prop)
        if self.proposal != None: # only works if review was fetched from DB
            review_json['proposal_eso_id'] = self.proposal.eso_id
        # review_json['last_updated'] = self.last_updated.isoformat(' ')
        review_json['last_updated'] = self.last_updated.timestamp() # POSIX timestamp; javascript will convert
        
        return review_json


    # comment must be a string
    # ref_knowledge must be 1-3
    # score must be 1.0 (outstanding) - 5.0 (rejected)
    # blank fields are OK
    # being conflicted overrides other constraints
    def is_valid(self):
        if self.conflicted in [1, 2]:
            return True
        comment_valid = self.comment == None or isinstance(self.comment, str)
        ref_knowledge_valid = self.ref_knowledge == None or (isinstance(self.ref_knowledge, int) and self.ref_knowledge >= self.MIN_REF_KNOWLEDGE and self.ref_knowledge <= self.MAX_REF_KNOWLEDGE)
        score_valid = self.score == None or (isinstance(self.score, float) and self.score >= self.MIN_SCORE and self.score <= self.MAX_SCORE)
        return comment_valid and ref_knowledge_valid and score_valid
    

    # conflict => complete
    def is_complete(self):
        if self.conflicted in [1, 2]:
            return True
        comment_filled = isinstance(self.comment, str) and len(self.comment) >= self.MIN_COMMENT
        ref_knowledge_filled = self.ref_knowledge != None
        score_filled = self.score != None
        # todo: conflicts
        return self.is_valid() and comment_filled and ref_knowledge_filled and score_filled



    
class ReviewRating(Base):
    __tablename__ = 'review_rating'

    MIN_RATING = 1
    MAX_RATING = 4

    id = Column(Integer, primary_key=True)
    referee_id = Column(Integer, ForeignKey('referees.id'))
    proposal_id = Column(Integer, ForeignKey('proposals.id'))
    review_rating = Column(Integer)

    def is_valid(self):
        rating_is_valid = isinstance(self.review_rating, int) and self.review_rating >= self.MIN_RATING and self.review_rating <= self.MAX_RATING
        rating_is_valid = rating_is_valid or self.review_rating == None # an empty review rating is OK; it means the PI changed their mind
        return isinstance(self.referee_id, int) and isinstance(self.proposal_id, int) and rating_is_valid
    
    def create_from_json(self, json):
        properties = ['referee_id', 'proposal_id', 'review_rating']
        for prop in properties:
            if prop not in json: 
                raise TypeError('JSON missing one or more required properties.')

            value = int(json[prop])
            if prop == 'review_rating' and value == 0:
                value = None

            setattr(self, prop, value)

    def update_from_json(self, json):
        rating = int(json['review_rating'])
        self.review_rating = rating if rating > 0 else None
    
    def to_json(self):
        rating_json = {}
        properties = ['id', 'referee_id', 'proposal_id', 'review_rating']
        for prop in properties: 
            rating_json[prop] = getattr(self, prop)
        if self.review_rating == None:
            rating_json['review_rating'] = 0
        
        return rating_json

