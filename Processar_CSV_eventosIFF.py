import csv

# --- Configure os nomes dos arquivos aqui ---
arquivo_de_entrada = 'EventosIFF.csv'  # Nome do arquivo original com 4 colunas
arquivo_de_saida = 'arquivo_modificado.csv'  # Nome do novo arquivo que terá 3 colunas
# ---------------------------------------------

try:
    # Abre o arquivo de entrada para leitura ('r') e o de saída para escrita ('w')
    with open(arquivo_de_entrada, 'r', newline='', encoding='utf-8') as f_entrada, \
         open(arquivo_de_saida, 'w', newline='', encoding='utf-8') as f_saida:

        # Cria um objeto para ler o CSV
        leitor_csv = csv.reader(f_entrada)
        
        # Cria um objeto para escrever o novo CSV
        escritor_csv = csv.writer(f_saida)

        # Itera sobre cada linha do arquivo de entrada
        for linha in leitor_csv:
            # Pega todos os elementos da linha a partir do segundo (índice 1)
            # e escreve no novo arquivo. Isso efetivamente remove a primeira coluna.
            escritor_csv.writerow(linha[1:])

    print(f"Processamento concluído com sucesso!")
    print(f"A primeira coluna de '{arquivo_de_entrada}' foi removida.")
    print(f"O resultado foi salvo em '{arquivo_de_saida}'.")

except FileNotFoundError:
    print(f"Erro: O arquivo de entrada '{arquivo_de_entrada}' não foi encontrado.")
    print("Por favor, verifique se o nome e o caminho do arquivo estão corretos.")

except Exception as e:
    print(f"Ocorreu um erro inesperado: {e}")