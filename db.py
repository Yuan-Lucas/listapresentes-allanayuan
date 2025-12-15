import sqlite3 as sq
from flask_sqlalchemy import SQLAlchemy

from lista import load_json
# from produto import Produto
import os

# os.chdir(r'C:\\Users\\Ivan\\OneDrive\\Área de Trabalho\\Servidor\\Casamento\\Site Lista de presentes\\instance')

db = SQLAlchemy()

def coneccao():
    conn = sq.connect('listaPresente.db')
    return conn

def func_cursor(conn):
    cursor = conn.cursor()
    return cursor

def func_fecharBanco(conn):
    conn.close()

# def func_criarTabela(cursor):
#     cursor.execute('''               
#         CREATE TABLE produtos (
#             id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
#             Nome TEXT NOT NULL UNIQUE,
#             Nome_abreviado TEXT NOT NULL,
#             Funcao TEXT,
#             Caracteristicas TEXT,
#             Cores_disponiveis TEXT NOT NULL,
#             Marca TEXT,
#             Tamanho TEXT,
#             Quantidade INTEGER NOT NULL,
#             Assinado_por TEXT,
#             Status TEXT          
#         );
                   
#     ''')

def func_registrarProdutos(conn, cursor):
    file_data = load_json('produtos')

    for i in range (len(file_data)):
        data_produto = file_data[f'produto-{i+1}']

        # produto = Produto(Nome = data_produto["Nome"], Nome_abreviado = data_produto["Nome_abreviado"], Funcao = data_produto["Funcao"], Caracteristicas = data_produto["Caracteristicas"], Cores_disponiveis = data_produto["Cores_disponiveis"], Marca = data_produto["Marca"], Tamanho = data_produto["Tamanho"], Quantidade = data_produto["Quantidade"], Assinado_por = data_produto["Assinado_por"], Status = data_produto["Status"])
        # db.session.add(produto)
        # db.session.commit()
        # db.create_all

        query = f"""INSERT INTO produtos (
            id, Nome, Nome_abreviado, Img_link,
            Funcao, Caracteristicas, Cores_disponiveis, coresDiferentes,
            Marca, Tamanho, Quantidade, Status)

            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        cursor.execute(query,(
            data_produto["id"],
            data_produto["Nome"],
            data_produto["Nome_abreviado"],
            data_produto["Img_link"],
            data_produto["Funcao"],
            data_produto["Caracteristicas"],
            data_produto["Cores_disponiveis"],
            data_produto["coresDiferentes"],
            data_produto["Marca"] or None,
            (data_produto["Tamanho"][0].strip() if data_produto["Tamanho"] else None),
            data_produto["Quantidade"],
            data_produto["Status"]))
        conn.commit()
    return "Registrado!"

# conn = coneccao()
# cursor = func_cursor(conn=conn)
# # func_criarTabela(cursor=cursor)
# func_registrarProdutos(conn, cursor)
# func_fecharBanco(conn)
















# def func_inserirCadastro(conn, cursor, nome, sobreNome, Telefone, email, senha, nomeSobrenome):
#     try:
#         cursor.execute('''
#             INSERT INTO cadastro (nome, sobreNome, Telefone, email, senha, nomeSobrenome)
#             VALUES (?, ?, ?, ?, ?, ?)
#                     ''', (nome, sobreNome, Telefone, email, senha, nomeSobrenome))
#         conn.commit()
        
#         return 'Cadastro inserido'
#     except:
#         return 'Erro no cadastro'

# def func_ativarLogin(cursor, nomeSobrenome): 
#     query = "SELECT senha FROM cadastro WHERE nomeSobrenome = ?"
#     try:
#         for row in cursor.execute(query,(nomeSobrenome,)):
#             senha = row[0]
#     except:
#         senha = 'ErroLoginSenha'
#     return senha

# def func_alterarSenha(conn, cursor, email, senha):
#     query = "UPDATE cadastro SET senha = ? WHERE email = ?"
#     cursor.execute(query,(senha, email))
    
#     conn.commit()
#     return 'Atualizado!'

# # 

# def func_updateAssinar(conn, cursor, assinar=[]):
#     print()

# def func_disponibilidadeProduto(conn, cursor,nome):
#     query = "SELECT quantidade FROM produtos WHERE nome = ?"
#     qtd = cursor.execute(query,(nome,))
#     if qtd == 0:
#         query = "UPDATE produtos SET Status = indisponivel WHERE nome = ?"
#         cursor.execute(query,(nome,))