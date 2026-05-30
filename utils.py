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

def ler_int(mensagem):

    while True:

        entrada = input(mensagem).strip()

        try:
            valor = int(entrada)
            
            if valor <= 0:
                print("Digite um valor maior que zero!")

                continue

            return valor
        
        except:
            print("Digite um número válido!")