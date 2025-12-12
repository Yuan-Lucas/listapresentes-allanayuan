from db import db

class Produto(db.Model):
    __tablename__ = 'produtos'

    id = db.Column(db.Integer, primary_key=True)

    Nome = db.Column(db.String(150), unique=True)
    Nome_abreviado = db.Column(db.String(75))
    Img_link = db.Column(db.String())

    Funcao = db.Column(db.String(), nullable=True)
    Caracteristicas = db.Column(db.String(), nullable=True)
    Cores_disponiveis = db.Column(db.String(), nullable=True)
    
    coresDiferentes = db.Column(db.Boolean, nullable=True)

    Marca = db.Column(db.String(), nullable=True)
    Tamanho = db.Column(db.String(), nullable=True)
    
    Quantidade = db.Column(db.Integer, nullable=False)
    
    Status = db.Column(db.String(), nullable=False, default='Disponível')

    def __str__(self):
        print(id)

