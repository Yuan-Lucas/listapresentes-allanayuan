from flask import render_template, Flask, request, session, redirect, url_for, abort, flash    
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

from db import db
from user import user
from produto import Produto
from assinatura import Assinatura
from criptografia import Hash

import os
import time
from pathlib import Path

app = Flask(__name__)
app.secret_key = 'KANKAN'

app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///listaPresente.db"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

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
    assinados_ids = [a.produto_id for a in assinaturas_user]

    # Se não assinou nada, retornar lista vazia
    if not assinados_ids:
        return render_template('lista.html', info_produto={}, assinados=[])


    # Montar infos de cada produto
    cores_por_produto = {}
    for a in assinaturas_user:
        cores_por_produto[a.produto_id] = a.cores.split(",") 

    # Buscar somente produtos assinados
    produtos_assinados = Produto.query.filter(Produto.id.in_(assinados_ids)).all()
    for produto in produtos_assinados:
        cores_assinadas = cores_por_produto.get(produto.id, [])
        
        dict_info[produto.id] = {
            "nome": produto.Nome,
            "cores": ",".join(cores_assinadas),
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
        assinados=assinados_ids
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

            # Verifica campos obrigatórios
            if not all([nome, sobrenome, telefone, senha]):
                flash("Preencha todos os campos do cadastro.", "error")
                return redirect(url_for('login'))

            # Nome formatado
            nome_completo_bruto = f"{nome} {sobrenome}"
            nome_user = " ".join(n.strip().lower() for n in nome_completo_bruto.split() if n.strip())

            # 🔍 VERIFICA SE USUÁRIO JÁ EXISTE
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
            nome_user = ''            
            for nome in request.form.get('nomeSobrenome').split(' '):
                if nome.strip() != "" and nome.strip() != " ":
                    nome_user += nome.strip().lower() + " "
            nome_user = nome_user.strip()
            senha = Hash(request.form.get('senhaLogin'))        
            # try:
            #     usuario = db.session.query(user).filter_by(nome_completo=nome_user, senha = senha).first()
            #     login_user(usuario)
            #     if not usuario:
            #         return render_template('login.html')
                
            #     return redirect(url_for('index'))
            # except:
            #     return "Login ou senha incorretos"
            # Não usar try/except aqui – queremos ver erros reais no console
            usuario = db.session.query(user).filter_by(
                nome_completo=nome_user,
                senha=senha
            ).first()
            
            # Primeiro verifica se achou
            if not usuario:
                flash("Login ou senha incorretos.")
                return render_template('login.html')
            
            # Depois faz login
            login_user(usuario)
            
            return redirect(url_for('index'))

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
            flash("Produto indisponível", "error")
            return redirect(url_for('produto', id=id))

        # Criar assinatura
        assinatura = Assinatura(
            produto_id=produto.id,
            user_id=current_user.id,
            cores=",".join(cores)
        )
        
        produto.Quantidade -= 1
        if produto.Quantidade == 0:
            produto.Status = "Indisponível"

        # Se o produto tem cores diferentes
        if produto.coresDiferentes:
            list_corDisponivel = produto.Cores_disponiveis.split(',')

            # Remover apenas cores selecionadas
            for cor in cores:
                if cor in list_corDisponivel:
                    list_corDisponivel.remove(cor)

            # Atualizar string de cores
            produto.Cores_disponiveis = ",".join(list_corDisponivel)

        # Registrar assinatura e salvar alterações
        db.session.add(assinatura)
        db.session.commit()
        
        flash("Produto assinado com sucesso!", "success")
        return redirect(url_for('index'))
    
    return render_template('produto.html', info_produto=dict_info, id=id)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))


if __name__ == '__main__':
    with app.app_context():
        db.create_all()

    app.run(debug=True , port=5000)
