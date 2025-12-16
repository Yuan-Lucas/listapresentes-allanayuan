from flask import render_template, Flask, request, session, redirect, url_for, abort, flash, jsonify    
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash, check_password_hash

from db import db
from user import user
from produto import Produto
from assinatura import Assinatura
from criptografia import Hash

import os
import time
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", os.urandom(24))

DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL não configurada")

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

migrate = Migrate(app, db)


lm = LoginManager(app)
lm.init_app(app)
lm.login_view = 'login'

@lm.user_loader
def user_loader(id):
    return user.query.get(int(id))

@app.route('/')
def index():
    # Ordena colocando 'disponivel' primeiro, 'indisponivel' depois

    produtos = Produto.query.order_by(
        Produto.Status != "disponivel"
    ).all()

    dict_info = {}

    for p in produtos:
        status = "Selecione aqui" if p.Status == "disponivel" else p.Status
        dict_info[p.id] = [p.Img_link, p.Nome_abreviado, status]


    return render_template('index.html', info_produto = dict_info)

@app.route('/lista')
@login_required
def lista():
    dict_info = {}

    # Buscar assinaturas apenas do usuário atual
    assinaturas_user = Assinatura.query.filter_by(user_id=current_user.id).all()

    if not assinaturas_user:
        return render_template('lista.html', info_produto={}, assinados=[])

    # Montar infos de cada assinatura (não apenas por produto)
    for idx, assinatura in enumerate(assinaturas_user):
        produto = Produto.query.get(assinatura.produto_id)

        dict_info[f"{produto.id}_{idx}"] = {
            "nome": produto.Nome,
            "cores": assinatura.cores,   # cores específicas dessa assinatura
            "img": produto.Img_link,
            "caracteristicas": produto.Caracteristicas,
            "funcao": produto.Funcao,
            "marca": produto.Marca,
            "tamanho": produto.Tamanho,
            "quantidade": produto.Quantidade
        }

    return render_template(
        'lista.html',
        info_produto=dict_info,
        assinados=[a.produto_id for a in assinaturas_user]
    )
    
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        form_id = request.form.get('form_id')
        if form_id == "cadastroAtv":
            nome = request.form.get('nome')
            sobrenome = request.form.get('sobrenome')
            telefone = request.form.get('numero')
            email = request.form.get('email')
            senha = request.form.get('senhaCadastro')

            if not all([nome, sobrenome, telefone, senha]):
                flash("Preencha todos os campos do cadastro.", "error")
                return redirect(url_for('login'))

            # Nome formatado
            nome_completo_bruto = f"{nome} {sobrenome}"
            nome_user = " ".join(n.strip().lower() for n in nome_completo_bruto.split() if n.strip())

            usuario_existente = user.query.filter_by(nome_completo=nome_user).first()

            if usuario_existente:
                flash("Usuário já cadastrado. Tente fazer login.", "error")
                return redirect(url_for('login'))

            # Criar novo usuário
            senha_hash = Hash(senha)
            novo_usuario = user(
                nome=nome,
                sobreNome=sobrenome,
                Telefone=telefone,
                email=email,
                senha=senha_hash,
                nome_completo=nome_user
            )

            try:
                db.session.add(novo_usuario)
                db.session.commit()
                flash("Cadastro realizado com sucesso! Faça login.", "success")
                return redirect(url_for('login'))

            except Exception as e:
                db.session.rollback()
                flash("Erro ao cadastrar usuário.", "error")
                return redirect(url_for('login'))

        elif form_id == "loginAtv":
            # Verificação de login
            nome_bruto = request.form.get('nomeSobrenome', '')
            nome_user = " ".join(
                n.strip().lower()
                for n in nome_bruto.split()
                if n.strip()
            )

            senha_bruta = request.form.get('senhaLogin')
            
            if not senha_bruta:
                flash("Senha inválida.")
                return render_template('login.html')
                
            senha = Hash(senha_bruta)        

            usuario = db.session.query(user).filter_by(
                nome_completo=nome_user,
                senha=senha
            ).first()
            
            if not usuario:
                flash("Login ou senha incorretos.")
                return render_template('login.html')
            
            login_user(usuario)

            # pega o parâmetro 'next' da URL
            next_page = request.form.get('next') or request.args.get('next')
            # segurança: só redireciona se for uma rota interna
            if not next_page or next_page.startswith('/login'):
                next_page = url_for('index')
            if not next_page or not next_page.startswith('/'):
                next_page = url_for('index')

            return redirect(next_page)
            # return redirect(url_for('index'))

    return render_template('login.html')
               

@app.route('/produto/<int:id>', methods=['GET', 'POST'])
@login_required
def produto(id):
    produto = Produto.query.get_or_404(id)
    dict_info = {}
    informacoes = [
        produto.Caracteristicas, 
        produto.Funcao, 
        produto.Marca, 
        produto.Tamanho, 
    ]
    informacoes = [i for i in informacoes if i]

    dict_info[produto.id] = {
        "nome": produto.Nome,
        "cores": produto.Cores_disponiveis,
        "img": produto.Img_link,
        "list_info": informacoes,
        "quantidade": produto.Quantidade
    }

    if request.method == 'POST' and request.form.get('Assinar_func'):
        cores = request.form.getlist('cor_selecionada')

        if len(cores) < 1:
            flash("Selecione pelo menos 1 cor.")
            return redirect(url_for("produto", id=id))

        if len(cores) > 2:
            flash("Você só pode selecionar no máximo 2 cores.")
            return redirect(url_for("produto", id=id))
        
        if produto.Quantidade <= 0:
            return jsonify({"redirect": url_for("index")})

        if len(cores) > produto.Quantidade:
            flash(f"Você escolheu {len(cores)} cores, sendo que só tem {produto.Quantidade} produtos.")
            return redirect(url_for("produto", id=id))
        
        # Criar assinatura
        assinatura = Assinatura(
            produto_id=produto.id,
            user_id=current_user.id,
            cores=",".join(cores)
        )
        
        produto.Quantidade -= len(cores)
        if produto.Quantidade == 0:
            produto.Status = "Indisponível"

        if produto.coresDiferentes:
            list_corDisponivel = [c.strip() for c in produto.Cores_disponiveis.split(',') if c.strip()]

            for cor in cores:
                cor = cor.strip()
                try:
                    list_corDisponivel.remove(cor)
                except ValueError:
                    pass
            produto.Cores_disponiveis = ",".join(list_corDisponivel)

        # Registrar assinatura e salvar alterações
        db.session.add(assinatura)
        db.session.commit()
        
        return jsonify({"redirect": url_for("index")})
    
    return render_template('produto.html', info_produto=dict_info, id=id)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

if __name__ == '__main__':

    app.run(debug=True , port=8000)


