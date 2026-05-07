import json

def load_data():
    try:
        with open("transacoes.json", "r") as arquivo:
            return json.load(arquivo)
    except:
        return []


def save_data(transacoes):
    with open("transacoes.json", "w") as arquivo:
        json.dump(transacoes, arquivo, indent=4)