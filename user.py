from db import db
from flask_login import UserMixin

class user(UserMixin, db.Model):
    __tablename__ = 'cadastro'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(75))
    sobreNome = db.Column(db.String(75))
    nome_completo = db.Column(db.String(150), unique=True)

    Telefone = db.Column(db.String(13), nullable=False)
    email = db.Column(db.String(), unique=True)
    senha = db.Column(db.String())

    # def __str__(self):
    #     print(id)
