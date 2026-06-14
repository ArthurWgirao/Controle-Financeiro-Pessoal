def ler_float(mensagem):

    while True:

        entrada = input(mensagem).strip()

        try:
            valor = float(entrada)
            
            if valor <= 0:
                print("Digite um valor maior que zero!")

                continue
            return valor

        except:
            print("Digite um número válido!")

def ler_int(mensagem, permite_zero=False):
    while True:
        try:
            valor = int(input(mensagem))

            if valor < 0:
                print("Digite um valor positivo!")
                continue

            if not permite_zero and valor == 0:
                print("Digite um valor maior que zero!")
                continue

            return valor

        except ValueError:
            print("Digite um número inteiro válido.")