from flask import Flask, render_template, request, session, redirect, url_for
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__, template_folder='templates', static_folder='static')

app.secret_key = "truck_parts_chave"

# SIMPLE PRODUCT CATALOG (in-memory)
PRODUCTS = [
    {"id": 1, "nome": "Gay", "preco": 150.0, "imagem": "imagens/pneu.png"},
    {"id": 2, "nome": "Chassi", "preco": 200.0, "imagem": "imagens/chassi.jpg"},
    {"id": 3, "nome": "Distribuidora", "preco": 250.0, "imagem": "imagens/distribuidora.webp"},
    {"id": 4, "nome": "Peça Promo", "preco": 99.0, "imagem": "imagens/carrosel_produtos1.png"},
]


def _get_cart():
    return session.get("cart", {})


def _save_cart(cart):
    session["cart"] = cart


def _cart_items():
    cart = _get_cart()
    items = []
    total = 0.0
    for pid_str, qty in cart.items():
        try:
            pid = int(pid_str)
        except ValueError:
            continue
        prod = next((p for p in PRODUCTS if p["id"] == pid), None)
        if not prod:
            continue
        subtotal = prod["preco"] * qty
        total += subtotal
        items.append({"produto": prod, "quantidade": qty, "subtotal": subtotal})
    return items, total


# CONECTAR AO MYSQL
def conectar_banco():

    conexao = mysql.connector.connect(
        host="localhost",
        user="root",
        password="senai105",
        database="truck_parts"
    )

    return conexao


# PÁGINA INICIAL
@app.route("/")
def land():

    return render_template("land.html")


# PÁGINA DE CADASTRO
@app.route("/cadastro")
def cadastro():

    return render_template("cadastro.html")


# PÁGINA DE LOGIN
@app.route("/login")
def login():

    return render_template("login.html")


# PÁGINA DO CARRINHO
@app.route("/carrinho")
def carrinho():

    items, total = _cart_items()
    return render_template("carrinho.html", items=items, total=total)


@app.route("/catalogo")
def catalogo():
    return render_template("catalogo.html", products=PRODUCTS)


@app.route("/add_to_cart/<int:product_id>", methods=["POST", "GET"])
def add_to_cart(product_id):
    cart = _get_cart()
    key = str(product_id)
    cart[key] = cart.get(key, 0) + 1
    _save_cart(cart)
    # Respect an optional 'next' parameter (from forms) or fall back to Referer
    next_target = request.values.get("next") or request.headers.get("Referer")
    # Basic safety: only allow relative redirects within app
    if next_target:
        # If referer is full URL, try to extract path
        try:
            from urllib.parse import urlparse

            parsed = urlparse(next_target)
            path = parsed.path or "/"
        except Exception:
            path = next_target

        # If path looks safe (starts with /), redirect there
        if isinstance(path, str) and path.startswith("/"):
            return redirect(path)

    return redirect(url_for("carrinho"))


@app.route("/remove_from_cart/<int:product_id>", methods=["POST", "GET"])
def remove_from_cart(product_id):
    cart = _get_cart()
    key = str(product_id)
    if key in cart:
        del cart[key]
        _save_cart(cart)
    return redirect(url_for("carrinho"))


# RECEBER CADASTRO
@app.route("/enviar", methods=["POST"])
def enviar():

    nome = request.form["nome"]
    email = request.form["email"]
    endereco = request.form["endereco"]
    senha = request.form["senha"]
    confirmar_senha = request.form["confirmar_senha"]
    tipo_cadastro = request.form["tipo_cadastro"]
    interesses = request.form.getlist("interesses")


    # VERIFICAR SENHA
    if senha != confirmar_senha:

        return "As senhas não são iguais!"


    # CRIAR HASH DA SENHA
    senha_hash = generate_password_hash(senha)


    # TRANSFORMAR LISTA EM TEXTO
    interesses = ", ".join(interesses)


    # CONECTAR AO BANCO
    conexao = conectar_banco()
    cursor = conexao.cursor()


    # VERIFICAR E-MAIL
    cursor.execute(
        "SELECT id FROM cadastros WHERE email = %s",
        (email,)
    )

    cadastro_existente = cursor.fetchone()


    if cadastro_existente:

        cursor.close()
        conexao.close()

        return "Este e-mail já está cadastrado!"


    # INSERIR CADASTRO
    comando = """
        INSERT INTO cadastros
        (nome, email, endereco, senha, tipo_cadastro, interesses)
        VALUES (%s, %s, %s, %s, %s, %s)
    """


    valores = (
        nome,
        email,
        endereco,
        senha_hash,
        tipo_cadastro,
        interesses
    )


    cursor.execute(comando, valores)

    conexao.commit()

    cursor.close()
    conexao.close()


    # DEPOIS DO CADASTRO, VAI PARA O LOGIN
    return redirect(url_for("login"))


# VERIFICAR LOGIN
@app.route("/login", methods=["POST"])
def fazer_login():

    email = request.form["email"]
    senha = request.form["senha"]


    # CONECTAR AO BANCO
    conexao = conectar_banco()
    cursor = conexao.cursor()


    # PROCURAR USUÁRIO
    cursor.execute(
        "SELECT id, nome, senha FROM cadastros WHERE email = %s",
        (email,)
    )


    usuario = cursor.fetchone()


    cursor.close()
    conexao.close()


    # E-MAIL NÃO ENCONTRADO
    if usuario is None:

        return "E-mail ou senha incorretos!"


    # HASH DA SENHA SALVA NO BANCO
    senha_hash = usuario[2]


    # COMPARAR SENHA DIGITADA COM O HASH
    if not check_password_hash(senha_hash, senha):

        return "E-mail ou senha incorretos!"


    # SALVAR USUÁRIO NA SESSÃO
    session["usuario_id"] = usuario[0]
    session["usuario_nome"] = usuario[1]


    # VOLTAR PARA A PÁGINA INICIAL
    return redirect(url_for("land"))


if __name__ == "__main__":

    app.run(debug=True)
