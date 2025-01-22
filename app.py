import os
import csv
import io
from flask import Flask, render_template, request, redirect, url_for, Response, flash
import sqlite3
import pandas as pd
from datetime import datetime
import plotly.express as px
from werkzeug.security import generate_password_hash, check_password_hash
import humanize
from flask_login import LoginManager, login_user, login_required, logout_user, UserMixin
import time
from sqlalchemy.orm import joinedload
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from flask import session
from sqlalchemy import text

##################################################### CONFIgURAÇÃO APP ####################################################################################

# Configurações do app
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///C:/Users/mathe_0cmys8j/Documents/MEGA/Luxury WheelsTest/database/database.db'
app.secret_key = 'minha_chave_super_segura_e_unica_12345'
db = SQLAlchemy(app)
secret_key = os.urandom(24)

# Inicializa o LoginManager para autenticação de usuário
login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    # Aqui, você deve buscar o usuário no banco de dados pelo ID
    return User.query.get(int(user_id))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.password == password:  # Verifique a senha adequadamente
            login_user(user)
            return redirect(url_for('dashboard'))
    return render_template('login.html')


############################## BANCO DE DADOS ##############################################################################################

# Caminho dinâmico baseado no diretório do script atual
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # Diretório onde o script está localizado
DATABASE_PATH = os.path.join(BASE_DIR, 'database', 'database.db')  # Caminho relativo ao banco de dados

# Função para obter conexão com o banco de dados
def obter_conexao():
    return sqlite3.connect(DATABASE_PATH)

# Função utilitária para executar queries
def executar_query(query, params=(), fetch=False):
    try:
        with obter_conexao() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            if fetch:
                return cursor.fetchall()
            conn.commit()
    except sqlite3.Error as e:
        print(f"Erro ao executar query: {e}")
        return None


# Conectar ao banco de dados e criar tabelas, se necessário
def criar_tabelas():
    queries = [
        '''CREATE TABLE IF NOT EXISTS Veiculos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            marca TEXT, modelo TEXT, categoria TEXT,
            valor_diaria REAL, data_ultima_revisao TEXT,
            data_proxima_revisao TEXT, data_ultima_inspecao TEXT)''',

        '''CREATE TABLE IF NOT EXISTS Clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT, cpf TEXT, email TEXT,
            telefone TEXT, endereco TEXT)''',

        '''CREATE TABLE IF NOT EXISTS Reservas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER, veiculo_id INTEGER,
            data_reserva TEXT, data_retirada TEXT,
            data_devolucao TEXT, status TEXT,
            FOREIGN KEY(cliente_id) REFERENCES Clientes(id),
            FOREIGN KEY(veiculo_id) REFERENCES Veiculos(id))''',

        '''CREATE TABLE IF NOT EXISTS Formas_de_Pagamento (
            ID INTEGER PRIMARY KEY AUTOINCREMENT,
            Nome TEXT NOT NULL,
            Descricao TEXT NOT NULL,
            TipoPagamento TEXT NOT NULL,
            Ativo INTEGER NOT NULL)''',

        '''CREATE TABLE IF NOT EXISTS Utilizadores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT, email TEXT, senha TEXT)'''
    ]
    for query in queries:
        executar_query(query)

# Criar as tabelas no banco de dados
criar_tabelas()

# Página inicial
@app.route('/')
def hello():
    return redirect(url_for('welcome'))


############################## DASHBOARD ###################################################################################################

@app.route('/dashboard')
def dashboard():
    # Dados do gráfico
    df = executar_query("SELECT categoria, COUNT(*) as count FROM Veiculos GROUP BY categoria", fetch=True)
    if not df:
        return "Erro ao carregar dados do Dashboard."

    df = pd.DataFrame(df, columns=['categoria', 'count'])
    fig = px.bar(
    df,
    x='categoria',
    y='count',
    title="Quantidade de Veículos por Categoria",
    color_discrete_sequence=['#3498db']) # Cor estilosa

    # Personalização do layout do gráfico
    fig.update_layout(
        title_font=dict(size=24, color='#333', family='Arial'),
        xaxis_title="Categoria",
        yaxis_title="Quantidade",
        plot_bgcolor='#f4f4f4',
        paper_bgcolor='#fff',
        font=dict(size=14, color='#333')
    )

    graph_html = fig.to_html(full_html=False)

    # Dados da tabela
    veiculos = executar_query("SELECT * FROM Veiculos", fetch=True)
    return render_template('dashboard.html', graph_html=graph_html, veiculos=veiculos)


#########################  VEICULOS  ####################################################################################################################

# Registrar veículo
@app.route('/registrar-veiculo', methods=['GET', 'POST'])
def registrar_veiculo():
    if request.method == 'POST':
        # Capturando os dados do formulário na ordem correta
        marca = request.form['marca']
        modelo = request.form['modelo']
        categoria = request.form['categoria']
        transmissao = request.form['transmissao']
        tipo = request.form['tipo']
        capacidade = request.form['capacidade']
        diaria = request.form['valor_diaria']
        ultima_revisao = request.form['ultima_revisao']
        ultima_inspecao = request.form['proxima_revisao']
        manutencao = 0  # Se você não tiver esse campo no formulário, pode deixar o valor fixo

        # Salvando os dados no banco de dados
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO Veiculos (marca, modelo, categoria, transmissao, tipo, capacidade, diaria, ultima_revisao, ultima_inspecao, manutencao)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (marca, modelo, categoria, transmissao, tipo, capacidade, diaria, ultima_revisao, ultima_inspecao, manutencao))
        conn.commit()
        conn.close()

        # Redirecionando para a página de listagem
        return redirect(url_for('listar_veiculos', success=True))

    return render_template('registrar_veiculo.html')


# Listar veículos
@app.route('/listar-veiculos')
def listar_veiculos():
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, marca, modelo, categoria, transmissao, tipo, capacidade, diaria, ultima_revisao, ultima_inspecao, manutencao FROM Veiculos")
    veiculos = cursor.fetchall()
    conn.close()

    return render_template('listar_veiculos.html', veiculos=veiculos)


# Remover veículo
@app.route('/remover-veiculo/<int:id>')
def remover_veiculo(id):
    if executar_query("DELETE FROM Veiculos WHERE id = ?", (id,)):
        flash("Veículo removido com sucesso!", "success")
    else:
        flash('Veículo removido com sucesso!', 'success')
    return redirect(url_for('listar_veiculos'))


# Exportar veículos
@app.route('/exportar-veiculos')
def exportar_veiculos():
    try:
        veiculos = db.session.execute(text('SELECT * FROM Veiculos')).fetchall()
        print(f"Veículos encontrados: {veiculos}")  # Log para verificar os dados

        output = io.StringIO()
        writer = csv.writer(output, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        writer.writerow(['ID', 'Marca', 'Modelo', 'Categoria', 'Transmissão', 'Tipo', 'Capacidade', 'Diária', 'Última Revisão', 'Última Inspeção', 'Manutenção'])

        for veiculo in veiculos:
            writer.writerow(veiculo)

        output.seek(0)
        return Response(output.getvalue(), mimetype='text/csv', headers={"Content-Disposition": "attachment;filename=veiculos.csv"})

    except Exception as e:
        print(f"Erro ao exportar veículos: {e}")
        return "Erro ao exportar veículos.", 500


# Alertas de revisão e inspeção
@app.route('/alertas')
def alertas():
    veiculos = executar_query("SELECT * FROM Veiculos", fetch=True)
    if not veiculos:
        return "Erro ao carregar veículos."

    hoje = datetime.now()
    alertas = []
    for veiculo in veiculos:
        if datetime.fromisoformat(veiculo[5]) < hoje:
            data_revisao = datetime.fromisoformat(veiculo[5])
            alertas.append(f'Veículo {veiculo[1]} {veiculo[2]} precisa de revisão! ({humanize.naturaldelta(hoje - data_revisao)})')
        if datetime.fromisoformat(veiculo[6]) < hoje:
            data_inspecao = datetime.fromisoformat(veiculo[6])
            alertas.append(f'Veículo {veiculo[1]} {veiculo[2]} precisa de inspeção! ({humanize.naturaldelta(hoje - data_inspecao)})')
    return render_template('alertas.html', alertas=alertas)

def gerar_csv():
    # Criar um objeto StringIO para armazenar os dados CSV na memória
    output = io.StringIO()
    
    # Criar o writer para escrever no objeto StringIO
    writer = csv.writer(output, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
    
    # Escrever os cabeçalhos do CSV (ajuste conforme necessário)
    writer.writerow(['Coluna1', 'Coluna2', 'Coluna3'])
    
    # Aqui, você pode adicionar as linhas do CSV, por exemplo:
    writer.writerow(['Dado1', 'Dado2', 'Dado3'])
    
    # Posicionar o ponteiro no início do objeto StringIO
    output.seek(0)
    
    # Criar a resposta com os dados CSV
    return Response(output.getvalue(), mimetype='text/csv', headers={"Content-Disposition": "attachment;filename=veiculos.csv"})

# Definindo a classe User
class User(UserMixin):
    def __init__(self, id, nome, email):
        self.id = id
        self.nome = nome
        self.email = email

    def get_id(self):
        return self.id

    
######################### UTILIZADORES ####################################################################################################

# Listar utilizadores
@app.route('/listar-utilizadores')
def listar_utilizadores():
    utilizadores = executar_query("SELECT * FROM Utilizadores", fetch=True)
    return render_template('utilizadores.html', utilizadores=utilizadores)

@app.route('/adicionar-utilizador')
def adicionar_utilizador():
    return render_template('adicionar_utilizador.html')

@app.route('/buscar-utilizador', methods=['GET'])
def buscar_utilizador():
    busca = request.args.get('busca', '')  # Captura o termo de busca
    # Adicione a lógica para buscar os dados no banco
    utilizadores = []  # Filtrar utilizadores do banco baseado no termo
    return render_template('lista_utilizadores.html', utilizadores=utilizadores)

    
######################### CLIENTES ########################################################################################################
# Rota para listar os clientes
@app.route('/clientes')
def listar_clientes():
    # Aqui você iria buscar os dados no banco de dados
    clientes = []  # Exemplo de lista de clientes
    return render_template('clientes.html', clientes=clientes)

# Rota para listar os clientes (usando consulta SQL)
@app.route('/listar-clientes')
def listar_clientes_completo():  # Renomeado para evitar conflito
    clientes = executar_query("SELECT * FROM Clientes", fetch=True)
    return render_template('clientes.html', clientes=clientes)

@app.route('/adicionar-cliente', methods=['GET', 'POST'])
def adicionar_cliente():
    if request.method == 'POST':
        dados = (
            request.form['nome'], request.form['telefone'], request.form['email'],
            request.form['endereco']
        )
        query = '''INSERT INTO Clientes (nome, telefone, email, endereco) VALUES (?, ?, ?, ?)'''
        if executar_query(query, dados):
            flash("Cliente registrado com sucesso!", "success")
            return redirect(url_for('listar_clientes_completo'))  # Redireciona para a lista de clientes
        else:
            flash("Erro ao adicionar cliente.", "danger")
    return render_template('adicionar_cliente.html')  # Retorna o formulário para adicionar cliente

@app.route('/remover-cliente/<int:id>')
def remover_cliente(id):
    if executar_query("DELETE FROM Clientes WHERE id = ?", (id,)):
        flash("Cliente removido com sucesso!", "success")
    else:
        flash("Erro ao remover cliente.", "danger")
    return redirect(url_for('listar_clientes_completo'))  # Correção: chamando a função correta

######################### FORMAS DE PAgAMENTO ############################################################################################

@app.route('/adicionar-forma-pagamento', methods=['POST'])
def adicionar_forma_pagamento():
    if request.method == 'POST':
        # Capturar os dados do formulário
        id = request.form.get('id')
        nome = request.form.get('nome')
        descricao = request.form.get('descricao')
        ativo = request.form.get('ativo')
        tipo_pagamento = request.form.get('tipo_pagamento')

        # Inserir no banco de dados
        query = '''
            INSERT INTO Formas_de_Pagamento (ID, Nome, Descricao, Ativo, TipoPagamento)
            VALUES (?, ?, ?, ?, ?)
        '''
        params = (id, nome, descricao, ativo, tipo_pagamento)
        executar_query(query, params)

        # Redirecionar para a listagem
        return redirect(url_for('listar_formas_pagamento'))

@app.route('/listar-formas-pagamento')
def listar_formas_pagamento():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row  # Retorna os resultados como dicionários
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Formas_de_Pagamento")
    formas_pagamento = cursor.fetchall()
    conn.close()
    return render_template('formas_pagamento.html', formas_pagamento=formas_pagamento)

# Rota para remover uma forma de pagamento pelo ID
@app.route('/remover-forma-pagamento/<int:id>', methods=['POST'])
def remover_forma_pagamento(id):
    try:
        executar_query("DELETE FROM Formas_de_Pagamento WHERE ID = ?", (id,))
        flash('Forma de pagamento removida com sucesso!', 'success')
    except Exception as e:
        flash(f'Erro ao remover forma de pagamento: {e}', 'danger')
    return redirect(url_for('listar_formas_pagamento'))

######################### RESERVAS ####################################################################################################### 

@app.route('/reservas', methods=['GET', 'POST'])
def reservas_view():
    if request.method == 'POST':
        cliente_nome = request.form['cliente_nome']
        veiculo_modelo = request.form['veiculo_modelo']
        veiculo_marca = request.form['veiculo_marca']
        veiculo_id = request.form['veiculo_id']
        data_reserva = request.form['data_reserva']
        data_retirada = request.form['data_retirada']  # Adicionado
        data_devolucao = request.form['data_devolucao']
        status = request.form['status']
        
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO Reservas (cliente_nome, veiculo_modelo, veiculo_marca, veiculo_id, data_reserva, data_retirada, data_devolucao, status) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (cliente_nome, veiculo_modelo, veiculo_marca, veiculo_id, data_reserva, data_retirada, data_devolucao, status))
        conn.commit()
        conn.close()
        return redirect(url_for('reservas_view'))

    reservas = executar_query("SELECT * FROM Reservas", fetch=True)
    return render_template('reservas.html', reservas=reservas)

@app.route('/remover_reserva/<int:id>', methods=['GET'])
def remover_reserva(id):
    conn = sqlite3.connect('caminho_do_seu_banco_de_dados')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM reservas WHERE id = ?', (id,))
    conn.commit()
    conn.close()

    return redirect(url_for('reservas'))

###############################################  Signup (CADASTRO) ###########################################################################################

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        nome = request.form.get('nome')
        email = request.form.get('email')
        confirmar_email = request.form.get('confirmar_email')
        senha = request.form.get('senha')

        # Validação básica
        if email != confirmar_email:
            flash("Os e-mails não coincidem. Tente novamente.", "danger")
            return redirect(url_for('signup'))

        if len(senha) > 12:
            flash("A senha deve ter no máximo 12 caracteres.", "danger")
            return redirect(url_for('signup'))

        # Verificar se o e-mail já está cadastrado
        usuario_existente = executar_query(
            "SELECT * FROM Utilizadores WHERE email = ?", (email,), fetch=True
        )
        if usuario_existente:
            flash("Este e-mail já está registrado. Tente outro.", "danger")
            return redirect(url_for('signup'))

        # Criptografar a senha e salvar no banco
        senha_hash = generate_password_hash(senha)
        query = '''INSERT INTO Utilizadores (nome, email, senha) VALUES (?, ?, ?)'''
        if executar_query(query, (nome, email, senha_hash)):
            flash("Cadastro realizado com sucesso!", "success")
            return redirect(url_for('login'))
        else:
            flash("Erro ao realizar o cadastro. Tente novamente.", "danger")

    return render_template('signup.html')

############################################## CENTRAL DE BOTOES DE DIRECIONAMENTO #################################################################

@app.route('/central')
def central():
    return render_template('central.html')

@app.route('/logout')
@login_required
def logout():
    # Faz o logout do usuário
    logout_user()
    # Redireciona para a página /welcome
    return redirect(url_for('welcome'))

############################################## Bem Vindo (Boas Vindas) ######################################################################### 

@app.route('/welcome')
def welcome():
    return render_template('Welcome.html')

##################################################### Esqueceu a Senha Login ##########################################################
# Configuração do Flask-Mail
app.config['MAIL_SERVER'] = 'smtp.gmail.com'  # Usando o Gmail, por exemplo
app.config['MAIL_PORT'] = 587  # Porta para enviar via TLS
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = 'seuemail@gmail.com'  # Seu e-mail
app.config['MAIL_PASSWORD'] = 'suasenha'  # Sua senha ou senha de aplicativo do Gmail
app.config['MAIL_DEFAULT_SENDER'] = 'seuemail@gmail.com'

mail = Mail(app)

@app.route('/recuperar-senha', methods=['GET', 'POST'])
def recuperar_senha():
    if request.method == 'POST':
        email = request.form['email']
        
        # Criação do link de recuperação de senha (simulação)
        recovery_link = url_for('nova_senha', _external=True, email=email)  # Criar link externo

        # Enviar o e-mail
        msg = Message('Recuperação de Senha', recipients=[email])
        msg.body = f'Clique no link abaixo para redefinir sua senha:\n{recovery_link}'
        try:
            mail.send(msg)
            flash('Se o e-mail existir, você receberá um link para redefinir sua senha.', 'success')
        except Exception as e:
            flash('Ocorreu um erro ao enviar o e-mail. Tente novamente.', 'danger')
            print(str(e))  # Exibir o erro no terminal, se houver

        return redirect(url_for('recuperar_senha'))

    return render_template('forgot_password.html')

@app.route('/nova-senha')
def nova_senha():
    # Aqui você pode exibir um formulário para o usuário alterar a senha
    return "Página para redefinir a senha"

#################################################################################################################################

# Execução da aplicação
if __name__ == '__main__':
    app.run(debug=True)
