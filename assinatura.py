from db import db
from datetime import datetime, timezone

class Assinatura(db.Model):
    __tablename__ = 'assinatura'

    id = db.Column(db.Integer, primary_key=True)

    produto_id = db.Column(db.Integer, db.ForeignKey('produtos.id'), nullable=False)
    
    user_id = db.Column(db.Integer, db.ForeignKey('cadastro.id'), nullable=False)
    
    cores = db.Column(db.String(200))
    
    timestamp = db.Column(db.DateTime, default=datetime.now(timezone.utc))

    def __str__(self):
        print(id)