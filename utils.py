def ler_float(mensagem):

    while True:

        entrada = input(mensagem).strip()

        try:
            valor = float(entrada)
            return valor

        except:
            print("Digite um número válido!")

def ler_int(mensagem):

    while True:

        entrada = input(mensagem).strip()

        try:
            valor = int(entrada)
            return valor
        
        except:
            print("Digite um número válido!")