from database import conectar
from transacoes import escolher_categoria

from utils import (
    ler_float,
    ler_int
)


def listar_metas_mensais(mes_referencia):

    conexao = conectar()

    try:
        cursor = conexao.cursor()
        cursor.execute(
            """
            SELECT
                m.id,
                m.categoria,
                m.limite,
                COALESCE(SUM(t.valor), 0) AS gasto
            FROM metas AS m
            LEFT JOIN transacoes AS t
                ON t.categoria = m.categoria
                AND t.tipo = 'despesa'
                AND substr(t.data, 4, 7) = ?
            GROUP BY m.id, m.categoria, m.limite
            ORDER BY m.categoria
            """,
            (mes_referencia,)
        )

        registros = cursor.fetchall()
    finally:
        conexao.close()

    return [
        calcular_dados_meta(registro, registro["gasto"])
        for registro in registros
    ]


def buscar_meta_por_id(id_meta):

    conexao = conectar()

    try:
        cursor = conexao.cursor()
        cursor.execute(
            "SELECT id, categoria, limite FROM metas WHERE id = ?",
            (id_meta,)
        )

        return cursor.fetchone()
    finally:
        conexao.close()


def categoria_possui_meta(categoria):

    conexao = conectar()

    try:
        cursor = conexao.cursor()
        cursor.execute(
            "SELECT id FROM metas WHERE categoria = ?",
            (categoria,)
        )

        return cursor.fetchone() is not None
    finally:
        conexao.close()


def cadastrar_meta(categoria, limite):

    conexao = conectar()

    try:
        cursor = conexao.cursor()
        cursor.execute(
            """
            INSERT INTO metas (categoria, limite)
            VALUES (?, ?)
            """,
            (categoria, limite)
        )
        conexao.commit()

        return cursor.lastrowid
    finally:
        conexao.close()


def atualizar_limite_meta(id_meta, limite):

    conexao = conectar()

    try:
        cursor = conexao.cursor()
        cursor.execute(
            """
            UPDATE metas
            SET limite = ?
            WHERE id = ?
            """,
            (limite, id_meta)
        )
        conexao.commit()

        return cursor.rowcount > 0
    finally:
        conexao.close()


def excluir_meta_por_id(id_meta):

    conexao = conectar()

    try:
        cursor = conexao.cursor()
        cursor.execute(
            "DELETE FROM metas WHERE id = ?",
            (id_meta,)
        )
        conexao.commit()

        return cursor.rowcount > 0
    finally:
        conexao.close()


def calcular_gasto_mensal_por_categoria(categoria, mes_referencia):

    conexao = conectar()

    try:
        cursor = conexao.cursor()
        cursor.execute(
            """
            SELECT COALESCE(SUM(valor), 0)
            FROM transacoes
            WHERE categoria = ?
                AND tipo = 'despesa'
                AND substr(data, 4, 7) = ?
            """,
            (categoria, mes_referencia)
        )

        return cursor.fetchone()[0]
    finally:
        conexao.close()


def calcular_dados_meta(meta, gasto):

    limite = meta["limite"]
    restante = limite - gasto
    percentual = (gasto / limite) * 100 if limite > 0 else 0

    if percentual >= 100:
        situacao = "Meta ultrapassada"
        classe_situacao = "ultrapassada"
    elif percentual >= 80:
        situacao = "Atenção"
        classe_situacao = "atencao"
    else:
        situacao = "Dentro da meta"
        classe_situacao = "dentro"

    return {
        "id": meta["id"],
        "categoria": meta["categoria"],
        "limite": limite,
        "gasto": gasto,
        "restante": restante,
        "percentual": percentual,
        "largura_barra": min(percentual, 100),
        "situacao": situacao,
        "classe_situacao": classe_situacao
    }


# =========================
# ADICIONAR / ATUALIZAR META
# =========================

def adicionar_meta():

    categoria = escolher_categoria()

    limite = ler_float(
        "Digite o limite de gastos: "
    )

    conexao = conectar()
    cursor = conexao.cursor()

    # Verifica se já existe meta
    cursor.execute(
        """
        SELECT id
        FROM metas
        WHERE categoria = ?
        """,
        (categoria,)
    )

    meta_existente = cursor.fetchone()

    # Atualiza meta existente
    if meta_existente:

        cursor.execute(
            """
            UPDATE metas

            SET limite = ?

            WHERE categoria = ?
            """,
            (limite, categoria)
        )

        print("Meta atualizada!")

    # Cria nova meta
    else:

        cursor.execute(
            """
            INSERT INTO metas (
                categoria,
                limite
            )

            VALUES (?, ?)
            """,
            (categoria, limite)
        )

        print("Meta criada!")

    conexao.commit()
    conexao.close()


# =========================
# LISTAR METAS
# =========================

def listar_metas():

    conexao = conectar()
    cursor = conexao.cursor()

    cursor.execute("""
    SELECT * FROM metas
    """)

    metas = cursor.fetchall()

    conexao.close()

    if len(metas) == 0:

        print("Nenhuma meta cadastrada.")
        return

    print("\n===== METAS =====")

    for indice, meta in enumerate(metas):

        print(
            f"{indice} - "
            f"{meta[1]} | "
            f"Limite: R$ {meta[2]:.2f}"
        )


# =========================
# REMOVER META
# =========================

def remover_meta():

    conexao = conectar()
    cursor = conexao.cursor()

    cursor.execute("""
    SELECT * FROM metas
    """)

    metas = cursor.fetchall()

    if len(metas) == 0:

        print("Nenhuma meta cadastrada.")
        conexao.close()
        return

    listar_metas()

    indice_visual = ler_int(
        "\nDigite o índice da meta: "
    )

    if 0 <= indice_visual < len(metas):

        meta = metas[indice_visual]

        id_real = meta[0]

        cursor.execute(
            """
            DELETE FROM metas
            WHERE id = ?
            """,
            (id_real,)
        )

        conexao.commit()

        print("Meta removida!")

    else:

        print("Índice inválido!")

    conexao.close()


# =========================
# EDITAR META
# =========================

def editar_meta():

    conexao = conectar()
    cursor = conexao.cursor()

    cursor.execute("""
    SELECT * FROM metas
    """)

    metas = cursor.fetchall()

    if len(metas) == 0:

        print("Nenhuma meta cadastrada.")
        conexao.close()
        return

    listar_metas()

    indice_visual = ler_int(
        "\nDigite o índice da meta: "
    )

    if 0 <= indice_visual < len(metas):

        meta = metas[indice_visual]

        id_real = meta[0]

        print(
            "\nPressione ENTER "
            "para não alterar.\n"
        )

        novo_limite = input(
            f"Novo limite ({meta[2]}): "
        ).strip()

        limite = meta[2]

        if novo_limite != "":

            limite = float(novo_limite)

        alterar_categoria = input(
            "Deseja alterar categoria? (s/n): "
        ).lower()

        categoria = meta[1]

        if alterar_categoria == "s":

            categoria = escolher_categoria()

        cursor.execute(
            """
            UPDATE metas

            SET categoria = ?,
                limite = ?

            WHERE id = ?
            """,
            (
                categoria,
                limite,
                id_real
            )
        )

        conexao.commit()

        print("Meta atualizada!")

    else:

        print("Índice inválido!")

    conexao.close()


# =========================
# VERIFICAR METAS
# =========================

def verificar_metas():

    conexao = conectar()
    cursor = conexao.cursor()

    cursor.execute("""
    SELECT categoria, limite
    FROM metas
    """)

    metas = cursor.fetchall()

    if len(metas) == 0:

        print("Nenhuma meta cadastrada.")
        conexao.close()
        return

    for meta in metas:

        categoria = meta[0]
        limite = meta[1]

        cursor.execute(
            """
            SELECT SUM(valor)

            FROM transacoes

            WHERE categoria = ?
            AND tipo = 'despesa'
            """,
            (categoria,)
        )

        total = cursor.fetchone()[0]

        if total is None:

            total = 0

        print(f"\nCategoria: {categoria}")

        print(
            f"Limite: "
            f"R$ {limite:.2f}"
        )

        print(
            f"Gasto atual: "
            f"R$ {total:.2f}"
        )

        if total > limite:

            print(
                "⚠️ LIMITE ULTRAPASSADO!"
            )

        else:

            print(
                "✅ Dentro do limite"
            )

    conexao.close()
