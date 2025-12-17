from flask import render_template, Flask, request, session, redirect, url_for, current_app, flash, jsonify    
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
import traceback

from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)

if not os.environ.get("SECRET_KEY"):
    raise RuntimeError("SECRET_KEY não configurada")
app.secret_key = os.environ["SECRET_KEY"]

app.config['PIX_KEY'] = os.environ.get('PIX_KEY')   
app.config['PIX_NAME'] = os.environ.get('PIX_NAME') 
app.config['PIX_BANK'] = os.environ.get('PIX_BANK') 
if not app.config['PIX_KEY']:
        app.logger.warning("PIX_KEY não configurada. Verifique as Environment Variables no Render.")

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL não configurada")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    "pool_pre_ping": True,
    "pool_recycle": 300,
}
migrate = Migrate(app, db)
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
        is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"

        form_id = request.form.get('form_id')

        if form_id == "cadastroAtv":
            nome = request.form.get('nome')
            sobrenome = request.form.get('sobrenome')
            telefone = request.form.get('numero')
            email = request.form.get('email')
            senha = request.form.get('senhaCadastro')

            if not all([nome, sobrenome, telefone, email,  senha]):
                flash("Preencha todos os campos do cadastro.", "error")
                return redirect(url_for('login'))

            # Nome formatado
            nome_completo_bruto = f"{nome} {sobrenome}"
            nome_user = " ".join(n.strip().lower() for n in nome_completo_bruto.split() if n.strip())

            usuario_existente = user.query.filter_by(nome_completo=nome_user).first()

            if usuario_existente:
                if is_ajax:
                    return jsonify({"error": "Usuário já cadastrado. Tente fazer login."}), 409
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

                if is_ajax:
                    return jsonify({"success": True}), 200

                # Confirmação rápida — busca o usuário recém-criado
                criado = user.query.filter_by(nome_completo=nome_user).first()
                if criado:
                    app.logger.info(f"Novo usuário criado: id={criado.id}, nome_completo={criado.nome_completo}")

                flash("Cadastro realizado com sucesso! Faça login.", "success")
                return redirect(url_for('login'))
            
            except Exception as e:
                # Remove qualquer sessão pendente
                db.session.rollback()
                # Log completo para o console/Render
                app.logger.error("Erro ao cadastrar usuário: %s", traceback.format_exc())
                # Mostra uma mensagem amigável no front
                flash("Erro ao cadastrar usuário. Verifique os logs do servidor.", "error")
                return redirect(url_for('login'))

        elif form_id == "loginAtv":
            # obter valores com defaults seguros
            nome_bruto = request.form.get('nomeSobrenome', '') or ''
            senha_bruta = request.form.get('senhaLogin', '') or ''

            # normalizar nome: remove espaços extras e coloca em lowercase
            nome_user = " ".join(part.strip().lower() for part in nome_bruto.split() if part.strip())

            # validações básicas
            if not nome_user or not senha_bruta:
                flash("Preencha nome e senha.", "error")
                return redirect(url_for('login'))

            senha = Hash(senha_bruta)

            # buscar usuário (nome_completo já armazenado em lowercase no cadastro)
            usuario = db.session.query(user).filter_by(
                nome_completo=nome_user,
                senha=senha
            ).first()

            if not usuario:
                if is_ajax:
                    return jsonify({"error": "Usuário ou senha incorretos."}), 401
                app.logger.info("Falha de login para nome_completo=%s", nome_user)

                flash("Login ou senha incorretos.", "error")

                return redirect(url_for('login'))

            # login bem-sucedido
            login_user(usuario)

            # pegar parâmetro 'next' e validar que é uma rota interna
            next_page = request.form.get('next') or request.args.get('next') or ''
            # segurança: só aceita caminhos relativos que começam com '/'
            if not next_page or not next_page.startswith('/') or next_page.startswith('//'):
                next_page = url_for('index')
            if is_ajax:
                return jsonify({"redirect": next_page}), 200

            return redirect(next_page)

    return render_template('login.html')
               

@app.route('/produto/<int:id>', methods=['GET', 'POST'])
@login_required
def produto(id):
    dict_info = {}

    if id == 0:
        dict_info[0] = {
            "nome": "Pix",
            "cores": "transparente",
            "img": "Imagens/produtos/Pix.png",
            "list_info": [
            ],
            "quantidade": "Sem limites"
        }
        return f"Desculpe pelo transtorno.\n Essa pagina ainda está em andamento \nCom prazo de finalização no dia 18/12/2025 às 01:00 AM"
    else:
        produto = Produto.query.get_or_404(id)

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
        is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"
        cores = [c.strip() for c in request.form.getlist('cor_selecionada') if c.strip()]

        def erro(msg, status=400, redirect_to="produto"):
            if is_ajax:
                return jsonify({"error": msg}), status
            flash(msg, "error")
            return redirect(url_for(redirect_to, id=id) if redirect_to == "produto" else url_for(redirect_to))

        # Validação 1
        if not cores:
            return erro("Selecione pelo menos 1 cor.")

        # Validação 2
        if len(cores) > 2:
            return erro("Você só pode selecionar no máximo 2 cores.")

        # Validação 3
        if produto.Quantidade <= 0:
            return erro("Produto sem estoque.", redirect_to="index")

        # Validação 4
        if len(cores) > produto.Quantidade:
            return erro(
                f"Você escolheu {len(cores)} cores, mas só existem {produto.Quantidade} disponíveis."
            )

        # Validação 5: cores válidas
        if produto.coresDiferentes:
            cores_disponiveis = [c.strip() for c in (produto.Cores_disponiveis or "").split(",") if c.strip()]
            for cor in cores:
                if cor not in cores_disponiveis:
                    return erro(f"A cor '{cor}' não está mais disponível.")

        # Criar assinatura
        assinatura = Assinatura(
            produto_id=produto.id,
            user_id=current_user.id,
            cores=",".join(cores)
        )

        produto.Quantidade -= len(cores)

        if produto.Quantidade == 0:
            produto.Status = "indisponivel"

        if produto.coresDiferentes:
            produto.Cores_disponiveis = ",".join(
                c for c in cores_disponiveis if c not in cores
            )

        try:
            db.session.add(assinatura)
            db.session.commit()
        except Exception:
            db.session.rollback()
            app.logger.error("Erro ao registrar assinatura:\n%s", traceback.format_exc())
            return erro("Erro ao registrar assinatura. Tente novamente.", 500)

        if is_ajax:
            return jsonify({"redirect": url_for("index")}), 200

        flash("Assinatura realizada com sucesso!", "success")
        return redirect(url_for("index"))
    
    return render_template('produto.html', info_produto=dict_info, id=id)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True , port=8000)


