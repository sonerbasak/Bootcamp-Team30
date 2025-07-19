# models.py dosyanızda WrongAnswer modeli:
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from database import Base # Base'in tanımlı olduğundan emin olun

class WrongAnswer(Base):
    __tablename__ = "wrong_answers"

    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("questions.id"), unique=True) # unique=True eklenmeli!
    user_answer_letter = Column(String)

    question = relationship("Question") # Question modeli ile ilişki

    def __repr__(self):
        return f"<WrongAnswer(id={self.id}, question_id={self.question_id})>"

# Question modeli
class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    city = Column(String, index=True)
    category = Column(String, index=True)
    question_text = Column(String)
    option_a = Column(String)
    option_b = Column(String)
    option_c = Column(String)
    option_d = Column(String)
    correct_answer_letter = Column(String)