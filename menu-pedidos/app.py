from flask import Flask, render_template, request, jsonify, redirect, url_for
import sqlite3
from datetime import datetime

app = Flask(__name__)

def get_connection():
    return sqlite3.connect("pedidos.db")

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pedidos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente TEXT,
            productos TEXT,
            total REAL,
            fecha TEXT,
            estado TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS configuracion (
            clave TEXT PRIMARY KEY,
            valor TEXT
        )
    """)

    cursor.execute("SELECT valor FROM configuracion WHERE clave = 'dia_abierto'")
    existe = cursor.fetchone()

    if not existe:
        cursor.execute("""
            INSERT INTO configuracion (clave, valor)
            VALUES ('dia_abierto', '1')
        """)

    conn.commit()
    conn.close()

def dia_abierto():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT valor FROM configuracion WHERE clave = 'dia_abierto'")
    resultado = cursor.fetchone()
    conn.close()
    return resultado and resultado[0] == "1"

@app.route("/")
def inicio():
    return redirect(url_for("menu"))

@app.route("/ordenar")
def menu():
    return render_template("menu.html")

@app.route("/caja")
def panel():
    return render_template("panel.html")

@app.route("/ticket/<int:pedido_id>")
def ticket(pedido_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM pedidos WHERE id = ?", (pedido_id,))
    pedido = cursor.fetchone()
    conn.close()

    if not pedido:
        return "Pedido no encontrado", 404

    pedido_data = {
        "id": pedido[0],
        "cliente": pedido[1],
        "productos": pedido[2],
        "total": pedido[3],
        "fecha": pedido[4],
        "estado": pedido[5]
    }

    return render_template("ticket.html", pedido=pedido_data)

@app.route("/estado_dia")
def estado_dia():
    return jsonify({"abierto": dia_abierto()})

@app.route("/abrir_dia", methods=["POST"])
def abrir_dia():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE configuracion
        SET valor = '1'
        WHERE clave = 'dia_abierto'
    """)
    conn.commit()
    conn.close()
    return jsonify({"mensaje": "Día abierto correctamente"})

@app.route("/cerrar_dia", methods=["POST"])
def cerrar_dia():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM pedidos")
    cursor.execute("""
        UPDATE configuracion
        SET valor = '0'
        WHERE clave = 'dia_abierto'
    """)

    conn.commit()
    conn.close()

    return jsonify({"mensaje": "Día cerrado. Se borraron los pedidos y ya no se aceptan nuevos."})

@app.route("/enviar_pedido", methods=["POST"])
def enviar_pedido():
    if not dia_abierto():
        return jsonify({"error": "Lo sentimos, ya no estamos aceptando pedidos por hoy."}), 400

    data = request.get_json()

    cliente = data.get("cliente", "").strip()
    productos = data.get("productos", [])
    total = data.get("total", 0)

    if not cliente:
        return jsonify({"error": "El nombre es obligatorio"}), 400

    if not productos:
        return jsonify({"error": "No hay productos en el pedido"}), 400

    productos_texto = ", ".join([f"{p['nombre']} x{p['cantidad']}" for p in productos])
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO pedidos (cliente, productos, total, fecha, estado)
        VALUES (?, ?, ?, ?, ?)
    """, (cliente, productos_texto, total, fecha, "Pendiente"))
    conn.commit()
    conn.close()

    return jsonify({"mensaje": "Pedido enviado correctamente"})

@app.route("/obtener_pedidos")
def obtener_pedidos():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM pedidos ORDER BY id DESC")
    pedidos = cursor.fetchall()
    conn.close()

    lista = []
    for p in pedidos:
        lista.append({
            "id": p[0],
            "cliente": p[1],
            "productos": p[2],
            "total": p[3],
            "fecha": p[4],
            "estado": p[5]
        })

    return jsonify(lista)

@app.route("/cambiar_estado/<int:pedido_id>", methods=["POST"])
def cambiar_estado(pedido_id):
    data = request.get_json()
    nuevo_estado = data.get("estado", "Pendiente")

    conn = get_connection()
    cursor = conn.cursor()

    if nuevo_estado == "Entregado":
        cursor.execute("DELETE FROM pedidos WHERE id = ?", (pedido_id,))
        conn.commit()
        conn.close()
        return jsonify({"mensaje": "Pedido entregado y eliminado"})
    else:
        cursor.execute("UPDATE pedidos SET estado = ? WHERE id = ?", (nuevo_estado, pedido_id))
        conn.commit()
        conn.close()
        return jsonify({"mensaje": "Estado actualizado"})

if __name__ == "__main__":
    init_db()
    app.run(debug=True, host="0.0.0.0", port=5000)